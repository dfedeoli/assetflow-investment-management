"""
Google Drive backup and restore utilities for AssetFlow

Provides functions to backup and restore the SQLite database to/from Google Drive
using OAuth 2.0 authentication.
"""

import os
import pickle
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io


# If modifying these scopes, delete the file token.pickle
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'
BACKUP_FOLDER_NAME = 'AssetFlow Backups'


class GoogleDriveBackupError(Exception):
    """Custom exception for Google Drive backup operations"""
    pass


def authenticate_google_drive(auth_code: Optional[str] = None) -> tuple[Optional[Credentials], Optional[str]]:
    """
    Authenticate with Google Drive using OAuth 2.0.

    Returns cached credentials if available and valid, otherwise initiates
    OAuth flow using manual URL/code exchange (works in WSL2/headless environments).

    Args:
        auth_code: Optional authorization code from user (for manual flow)

    Returns:
        Tuple of (credentials, auth_url):
        - If credentials are valid: (Credentials object, None)
        - If auth needed and no code provided: (None, auth_url)
        - If auth code provided: (Credentials object, None)

    Raises:
        GoogleDriveBackupError: If authentication fails
    """
    creds = None

    # Check if credentials.json exists
    if not os.path.exists(CREDENTIALS_FILE):
        raise GoogleDriveBackupError(
            f"Missing {CREDENTIALS_FILE}. Please follow GOOGLE_DRIVE_SETUP.md to set up Google Drive API."
        )

    # Load cached credentials from token.pickle if it exists
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        except Exception as e:
            # If token is corrupted, remove it and re-authenticate
            os.remove(TOKEN_FILE)
            creds = None

    # If no valid credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                raise GoogleDriveBackupError(f"Failed to refresh credentials: {str(e)}")
        else:
            # Manual OAuth flow for WSL2/headless environments
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)

                # If no auth code provided, return the authorization URL
                if auth_code is None:
                    # Use a fixed localhost URL for redirect
                    flow.redirect_uri = 'http://localhost:8080/'
                    auth_url, _ = flow.authorization_url(
                        access_type='offline',
                        include_granted_scopes='true'
                    )
                    return None, auth_url

                # If auth code provided, exchange it for credentials
                flow.redirect_uri = 'http://localhost:8080/'
                flow.fetch_token(code=auth_code)
                creds = flow.credentials

            except Exception as e:
                raise GoogleDriveBackupError(f"OAuth flow failed: {str(e)}")

        # Save the credentials for the next run
        if creds:
            try:
                with open(TOKEN_FILE, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                # Non-critical error, just warn
                print(f"Warning: Could not save token: {str(e)}")

    return creds, None


def _get_or_create_backup_folder(service) -> str:
    """
    Get the ID of the backup folder, creating it if it doesn't exist.

    Args:
        service: Google Drive API service instance

    Returns:
        Folder ID string
    """
    # Search for existing folder
    query = f"name='{BACKUP_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"

    try:
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()

        folders = results.get('files', [])

        if folders:
            return folders[0]['id']

        # Create folder if it doesn't exist
        folder_metadata = {
            'name': BACKUP_FOLDER_NAME,
            'mimeType': 'application/vnd.google-apps.folder'
        }

        folder = service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()

        return folder.get('id')

    except Exception as e:
        raise GoogleDriveBackupError(f"Failed to get/create backup folder: {str(e)}")


def upload_backup_to_drive(db_path: str, credentials: Credentials) -> Tuple[str, str]:
    """
    Upload database backup to Google Drive with timestamp.

    Args:
        db_path: Path to the SQLite database file
        credentials: Google OAuth credentials

    Returns:
        Tuple of (file_id, backup_filename)

    Raises:
        GoogleDriveBackupError: If upload fails
    """
    if not os.path.exists(db_path):
        raise GoogleDriveBackupError(f"Database file not found: {db_path}")

    try:
        service = build('drive', 'v3', credentials=credentials)

        # Get or create backup folder
        folder_id = _get_or_create_backup_folder(service)

        # Generate timestamped filename
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        db_name = Path(db_path).stem  # Get filename without extension
        backup_filename = f"{db_name}_{timestamp}.db"

        # Prepare file metadata
        file_metadata = {
            'name': backup_filename,
            'parents': [folder_id]
        }

        # Upload file
        media = MediaFileUpload(db_path, mimetype='application/x-sqlite3', resumable=True)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, createdTime'
        ).execute()

        return file.get('id'), backup_filename

    except Exception as e:
        raise GoogleDriveBackupError(f"Failed to upload backup: {str(e)}")


def list_backups_from_drive(credentials: Credentials) -> List[Dict]:
    """
    List all backup files from Google Drive.

    Args:
        credentials: Google OAuth credentials

    Returns:
        List of dictionaries with backup file info (id, name, createdTime)
        Sorted by creation time (newest first)

    Raises:
        GoogleDriveBackupError: If listing fails
    """
    try:
        service = build('drive', 'v3', credentials=credentials)

        # Get backup folder ID
        folder_id = _get_or_create_backup_folder(service)

        # Query for all .db files in the backup folder
        query = f"'{folder_id}' in parents and name contains '.db' and trashed=false"

        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, createdTime, size)',
            orderBy='createdTime desc'
        ).execute()

        files = results.get('files', [])

        # Parse and format file info
        backups = []
        for file in files:
            backups.append({
                'id': file['id'],
                'name': file['name'],
                'created_time': file.get('createdTime'),
                'size': file.get('size', 0)
            })

        return backups

    except Exception as e:
        raise GoogleDriveBackupError(f"Failed to list backups: {str(e)}")


def download_backup_from_drive(file_id: str, destination_path: str, credentials: Credentials) -> str:
    """
    Download a backup file from Google Drive and restore it.

    Creates a safety backup of the current database before restoring.

    Args:
        file_id: Google Drive file ID to download
        destination_path: Local path where to save the restored database
        credentials: Google OAuth credentials

    Returns:
        Path to the safety backup of the previous database

    Raises:
        GoogleDriveBackupError: If download or restore fails
    """
    try:
        service = build('drive', 'v3', credentials=credentials)

        # Create safety backup of current database if it exists
        safety_backup_path = None
        if os.path.exists(destination_path):
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            safety_backup_path = f"{destination_path}.before_restore_{timestamp}"
            shutil.copy2(destination_path, safety_backup_path)

        # Download the backup file
        request = service.files().get_media(fileId=file_id)

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        # Write to destination
        with open(destination_path, 'wb') as f:
            fh.seek(0)
            f.write(fh.read())

        return safety_backup_path

    except Exception as e:
        # If restore failed and we made a safety backup, restore it
        if safety_backup_path and os.path.exists(safety_backup_path):
            shutil.copy2(safety_backup_path, destination_path)
        raise GoogleDriveBackupError(f"Failed to download/restore backup: {str(e)}")


def delete_backup_from_drive(file_id: str, credentials: Credentials) -> bool:
    """
    Delete a backup file from Google Drive.

    Args:
        file_id: Google Drive file ID to delete
        credentials: Google OAuth credentials

    Returns:
        True if successful

    Raises:
        GoogleDriveBackupError: If deletion fails
    """
    try:
        service = build('drive', 'v3', credentials=credentials)
        service.files().delete(fileId=file_id).execute()
        return True

    except Exception as e:
        raise GoogleDriveBackupError(f"Failed to delete backup: {str(e)}")


def format_backup_display_name(backup_info: Dict) -> str:
    """
    Format backup info for display in UI.

    Args:
        backup_info: Dictionary with backup file info

    Returns:
        Formatted string for display
    """
    name = backup_info.get('name', 'Unknown')
    created_time = backup_info.get('created_time', '')

    # Parse and format timestamp
    if created_time:
        try:
            dt = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
            formatted_date = dt.strftime('%d/%m/%Y %H:%M:%S')
            return f"{name} ({formatted_date})"
        except:
            pass

    return name
