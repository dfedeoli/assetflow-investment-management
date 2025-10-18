# Google Drive Backup Setup Guide

This guide explains how to set up Google Drive integration for backing up and restoring your AssetFlow investment database.

## Overview

The Google Drive backup feature allows you to:
- **Backup** your `investment_data.db` to Google Drive with timestamped filenames
- **Restore** previous backups from Google Drive
- **Manage** backups (view, delete) directly from the app sidebar
- **Secure** your data with OAuth 2.0 authentication

All backups are stored in a dedicated "AssetFlow Backups" folder in your Google Drive.

## Prerequisites

- A Google account
- Access to [Google Cloud Console](https://console.cloud.google.com/)
- AssetFlow app installed with required dependencies

## Step-by-Step Setup

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click **"New Project"**
4. Enter a project name (e.g., "AssetFlow Backup")
5. Click **"Create"**

### 2. Enable Google Drive API

1. Make sure your new project is selected
2. Go to **APIs & Services → Library**
3. Search for **"Google Drive API"**
4. Click on it and press **"Enable"**

### 3. Configure OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**
2. Choose **"External"** user type (unless you have a Google Workspace)
3. Click **"Create"**
4. Fill in the required fields:
   - **App name**: AssetFlow Backup (or your preferred name)
   - **User support email**: Your email
   - **Developer contact information**: Your email
5. Click **"Save and Continue"**
6. Enable Google Drive API on your project at **Enable APIs and Services**
6. On the **Data Access** page, click **"Add or Remove Scopes"**
7. Search for "Google Drive API" and add:
   - `.../auth/drive.file` (allows app to manage files it creates)
8. Click **"Update"** then **"Save and Continue"**
9. On **Test users** in **Audience**, click **"Add Users"** and add your Google account email
10. Click **"Save and Continue"** and then **"Back to Dashboard"**

### 4. Create OAuth 2.0 Credentials

1. Go to **APIs & Services → Credentials**
2. Click **"Create Credentials"** → **"OAuth client ID"**
3. Select **"Desktop app"** as the application type
4. Enter a name (e.g., "AssetFlow Desktop Client")
5. Click **"Create"**
6. A popup will show your credentials - click **"Download JSON"**
7. Save the downloaded file

### 5. Install the Credentials File

1. Rename the downloaded JSON file to **`credentials.json`**
2. Move it to your AssetFlow project root directory (same folder as `main.py`)

Your directory structure should look like:
```
assetflow-investment-planner/
├── main.py
├── credentials.json          ← Place it here
├── investment_data.db
├── components/
├── database/
└── utils/
```

### 6. First-Time Authentication

1. Start your AssetFlow app:
   ```bash
   streamlit run main.py
   ```

2. In the sidebar, you'll see the **"☁️ Google Drive"** section

3. Click **"🔐 Conectar ao Google Drive"**

4. **For WSL2/Linux users**: A clickable link will appear in the sidebar:
   - Click **"🔗 Autorizar AssetFlow no Google Drive"**
   - Your Windows browser will open with the Google authorization page
   - Choose your Google account
   - Click **"Continue"** on the warning screen (since app is in testing mode)
   - Review permissions and click **"Allow"**
   - The browser will redirect to `http://localhost:8080/?code=4/0AbC...XyZ`
   - Copy everything **after** `code=` from the URL bar
   - Paste the code into the text input in the sidebar
   - Click **"✅ Confirmar"**

5. You should see **"✅ Conectado ao Google Drive!"**

6. The app creates a `token.pickle` file to remember your authentication for this session

## Using the Backup Feature

### Creating a Backup

1. Make sure you're connected to Google Drive (see sidebar)
2. Click **"💾 Backup para Drive"**
3. Wait for the upload to complete
4. You'll see a success message with the backup filename

Backup files are named like: `investment_data_2025-10-18_14-30-25.db`

### Restoring a Backup

1. In the sidebar under **"📥 Restaurar Backup"**, select a backup from the dropdown
2. Click **"📥 Restaurar"**
3. The app automatically creates a safety backup of your current database before restoring
4. Your data will be restored and the app will refresh

### Deleting a Backup

1. Select the backup you want to delete from the dropdown
2. Click **"🗑️ Deletar"**
3. Confirm the deletion

### Disconnecting

Click **"🔓 Desconectar"** to log out. You'll need to re-authenticate next time.

## Security Notes

- **credentials.json**: Contains your app's OAuth client credentials. Keep it private but it's not sensitive user data.
- **token.pickle**: Contains your personal access token. **Never commit this to git** - it's in `.gitignore`.
- The app only has access to files it creates in Google Drive (limited scope)
- Authentication is required every time you restart the app (Streamlit limitation)

## Troubleshooting

### "Missing credentials.json" Error

**Solution**: Make sure `credentials.json` is in the project root directory (same folder as `main.py`)

### OAuth Flow Fails

**Solutions**:
- Make sure your email is added to "Test Users" in OAuth consent screen
- Try deleting `token.pickle` and re-authenticating
- Check that Google Drive API is enabled in your Cloud project

### "Failed to refresh credentials" Error

**Solution**: Delete `token.pickle` file and click "Conectar ao Google Drive" again to re-authenticate

### Browser Doesn't Open for Authentication

**Solution**:
- Check your firewall settings
- Try running from a different terminal
- Ensure you have a default browser configured

### "Insufficient permissions" Error

**Solution**: Make sure you added the correct scope (`.../auth/drive.file`) in the OAuth consent screen configuration

## File Locations

- **Backups in Google Drive**: "AssetFlow Backups" folder
- **Local database**: `investment_data.db` (project root)
- **OAuth credentials**: `credentials.json` (project root, git-ignored)
- **Auth token**: `token.pickle` (project root, git-ignored)
- **Safety backups**: `investment_data.db.before_restore_TIMESTAMP` (created before each restore)

## Additional Resources

- [Google Drive API Documentation](https://developers.google.com/drive/api/guides/about-sdk)
- [OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [AssetFlow GitHub Issues](https://github.com/yourusername/assetflow-investment-planner/issues)

## Support

If you encounter issues not covered in this guide, please check the error messages carefully and ensure all setup steps were completed correctly.
