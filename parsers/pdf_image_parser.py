"""
PDF and Image Parser for Investment Position Documents

Uses OpenAI Vision API to extract investment positions from:
- PDF statements
- Images of statements (PNG, JPG, JPEG)
"""

import os
import base64
from typing import List, Dict, Optional, Tuple, Generator
from datetime import datetime
from io import BytesIO
from PIL import Image
import PyPDF2

from parsers.xlsx_parser import InvestmentPosition
from utils.openai_client import OpenAIExtractor


class PDFImageParser:
    """Parser for PDF and image investment statements using OpenAI Vision API"""

    SUPPORTED_IMAGE_FORMATS = ['.png', '.jpg', '.jpeg']
    SUPPORTED_PDF_FORMATS = ['.pdf']

    def __init__(self, file_path: str, model: str = "gpt-4o"):
        """
        Initialize parser

        Args:
            file_path: Path to PDF or image file
            model: OpenAI model to use (gpt-4o or gpt-4o-mini)
        """
        self.file_path = file_path
        self.model = model
        self.extractor = OpenAIExtractor()

        # Validate file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine file type
        self.file_ext = os.path.splitext(file_path)[1].lower()
        if self.file_ext not in self.SUPPORTED_IMAGE_FORMATS + self.SUPPORTED_PDF_FORMATS:
            raise ValueError(
                f"Unsupported file format: {self.file_ext}. "
                f"Supported: {', '.join(self.SUPPORTED_IMAGE_FORMATS + self.SUPPORTED_PDF_FORMATS)}"
            )

    def parse(self) -> Tuple[List[InvestmentPosition], Dict]:
        """
        Parse the document and extract investment positions

        Returns:
            Tuple of (positions list, metadata dict)
        """
        if self.file_ext in self.SUPPORTED_PDF_FORMATS:
            return self._parse_pdf()
        else:
            return self._parse_image()

    def _parse_image(self) -> Tuple[List[InvestmentPosition], Dict]:
        """Parse an image file"""
        try:
            # Load and potentially resize image
            with Image.open(self.file_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Resize if too large (max 20MB for OpenAI)
                max_size = (4096, 4096)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)

                # Convert to bytes
                img_byte_arr = BytesIO()
                img.save(img_byte_arr, format='JPEG', quality=95)
                img_bytes = img_byte_arr.getvalue()

                # Get file size for cost estimation
                file_size_kb = len(img_bytes) / 1024

            # Extract positions using OpenAI
            positions_data, extraction_metadata = self.extractor.extract_positions_from_image(
                image_data=img_bytes,
                model=self.model,
                mime_type="image/jpeg"
            )

            # Convert to InvestmentPosition objects
            positions = self._convert_to_positions(positions_data, extraction_metadata)

            # Get document metadata
            doc_metadata = self.extractor.get_extraction_metadata(
                type('Response', (), {'choices': [type('Choice', (), {
                    'message': type('Message', (), {'content': str(positions_data)})()
                })()]})()
            )

            # Combine metadata
            metadata = {
                'file_name': os.path.basename(self.file_path),
                'file_type': 'image',
                'file_size_kb': file_size_kb,
                'model_used': self.model,
                'estimated_cost': self.extractor.estimate_cost(self.model, file_size_kb),
                **extraction_metadata,
                **doc_metadata
            }

            return positions, metadata

        except Exception as e:
            raise Exception(f"Failed to parse image: {str(e)}")

    def _parse_pdf(self) -> Tuple[List[InvestmentPosition], Dict]:
        """
        Parse a PDF file by converting first page to image

        Note: This requires poppler-utils to be installed on the system
        For simpler setup, users can convert PDFs to images themselves
        """
        try:
            import tempfile
            import subprocess

            # Check if poppler is available
            try:
                subprocess.run(['pdftoppm', '-v'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                raise NotImplementedError(
                    "PDF support requires 'poppler-utils' to be installed.\n"
                    "Install it with: sudo apt-get install poppler-utils (Ubuntu/Debian)\n"
                    "Or convert your PDF to an image (PNG/JPG) and upload that instead."
                )

            # Read PDF to get page count
            with open(self.file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)

                if num_pages == 0:
                    raise ValueError("PDF has no pages")

            # Convert first page to image using pdftoppm
            with tempfile.TemporaryDirectory() as tmp_dir:
                output_prefix = os.path.join(tmp_dir, 'page')

                # Convert first page to JPEG at 300 DPI
                subprocess.run(
                    ['pdftoppm', '-jpeg', '-f', '1', '-l', '1', '-r', '300', self.file_path, output_prefix],
                    check=True,
                    capture_output=True
                )

                # pdftoppm creates files with -1.jpg suffix
                img_path = f"{output_prefix}-1.jpg"

                # Read the generated image
                with open(img_path, 'rb') as img_file:
                    img_bytes = img_file.read()

            file_size_kb = len(img_bytes) / 1024

            # Extract positions using OpenAI
            positions_data, extraction_metadata = self.extractor.extract_positions_from_image(
                image_data=img_bytes,
                model=self.model,
                mime_type="image/jpeg"
            )

            # Convert to InvestmentPosition objects
            positions = self._convert_to_positions(positions_data, extraction_metadata)

            # Get document metadata from extraction
            doc_metadata = extraction_metadata.copy()
            if 'position_date' not in doc_metadata:
                doc_metadata['position_date'] = datetime.now()

            # Combine metadata
            metadata = {
                'file_name': os.path.basename(self.file_path),
                'file_type': 'pdf',
                'num_pages': num_pages,
                'file_size_kb': file_size_kb,
                'model_used': self.model,
                'estimated_cost': self.extractor.estimate_cost(self.model, file_size_kb),
                **doc_metadata
            }

            return positions, metadata

        except NotImplementedError:
            raise
        except Exception as e:
            raise Exception(f"Failed to parse PDF: {str(e)}")

    def _convert_to_positions(
        self,
        positions_data: List[Dict],
        extraction_metadata: Dict
    ) -> List[InvestmentPosition]:
        """
        Convert extracted position data to InvestmentPosition objects

        Args:
            positions_data: List of position dictionaries from OpenAI
            extraction_metadata: Metadata from extraction

        Returns:
            List of InvestmentPosition objects
        """
        positions = []

        # Get position date from metadata or use current date
        position_date = extraction_metadata.get('position_date', datetime.now())

        for pos_data in positions_data:
            try:
                position = InvestmentPosition(
                    name=pos_data['name'],
                    value=float(pos_data['value']),
                    main_category=pos_data.get('main_category', 'Outro'),
                    sub_category=pos_data.get('sub_category', ''),
                    date=position_date,
                    invested_value=float(pos_data['invested_value']) if pos_data.get('invested_value') else None,
                    percentage=None,  # Not extracted from documents
                    quantity=None,  # Not extracted from documents
                    additional_info={'extracted_via': 'openai_vision'}
                )
                positions.append(position)

            except Exception as e:
                # Log warning but continue with other positions
                print(f"Warning: Failed to convert position {pos_data.get('name', 'unknown')}: {str(e)}")
                continue

        return positions

    def get_summary(self, positions: List[InvestmentPosition]) -> Dict:
        """
        Generate summary statistics for extracted positions

        Args:
            positions: List of InvestmentPosition objects

        Returns:
            Summary dictionary
        """
        if not positions:
            return {
                'total_positions': 0,
                'total_value': 0,
                'categories': {}
            }

        total_value = sum(p.value for p in positions)

        # Group by main category
        categories = {}
        for pos in positions:
            cat = pos.main_category
            if cat not in categories:
                categories[cat] = {
                    'count': 0,
                    'value': 0
                }
            categories[cat]['count'] += 1
            categories[cat]['value'] += pos.value

        return {
            'total_positions': len(positions),
            'total_value': total_value,
            'categories': categories
        }

    def get_page_count(self) -> int:
        """
        Get the number of pages in a PDF file

        Returns:
            Number of pages (returns 1 for image files)
        """
        if self.file_ext not in self.SUPPORTED_PDF_FORMATS:
            return 1  # Images are single "page"

        try:
            with open(self.file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return len(pdf_reader.pages)
        except Exception as e:
            raise Exception(f"Failed to get page count: {str(e)}")

    def generate_page_thumbnail(self, page_num: int, width: int = 200) -> str:
        """
        Generate a thumbnail preview of a specific PDF page

        Args:
            page_num: Page number (1-indexed)
            width: Width of thumbnail in pixels (height auto-calculated)

        Returns:
            Base64-encoded JPEG thumbnail
        """
        if self.file_ext not in self.SUPPORTED_PDF_FORMATS:
            raise ValueError("Thumbnails only supported for PDF files")

        try:
            import tempfile
            import subprocess

            # Check if poppler is available
            try:
                subprocess.run(['pdftoppm', '-v'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                raise NotImplementedError(
                    "Thumbnail generation requires 'poppler-utils' to be installed."
                )

            # Convert specific page to image at lower DPI for thumbnail
            with tempfile.TemporaryDirectory() as tmp_dir:
                output_prefix = os.path.join(tmp_dir, 'thumb')

                # Use lower DPI (72) for thumbnails to save processing time
                subprocess.run(
                    ['pdftoppm', '-jpeg', '-f', str(page_num), '-l', str(page_num),
                     '-r', '72', '-scale-to', str(width), self.file_path, output_prefix],
                    check=True,
                    capture_output=True
                )

                # pdftoppm creates files with -N.jpg suffix
                thumb_path = f"{output_prefix}-{page_num}.jpg"

                # Read and encode to base64
                with open(thumb_path, 'rb') as thumb_file:
                    thumb_bytes = thumb_file.read()
                    thumb_base64 = base64.b64encode(thumb_bytes).decode('utf-8')

            return thumb_base64

        except Exception as e:
            raise Exception(f"Failed to generate thumbnail for page {page_num}: {str(e)}")

    def parse_multiple_pages(
        self,
        pages_to_process: List[int]
    ) -> Generator[Dict, None, Tuple[List[InvestmentPosition], Dict, Dict]]:
        """
        Parse multiple PDF pages sequentially with progress updates

        Args:
            pages_to_process: List of page numbers to process (1-indexed)

        Yields:
            Progress dictionaries with keys: 'current_page', 'total_pages', 'status'

        Returns:
            Tuple of (all_positions, combined_metadata, duplicate_warnings)
        """
        if self.file_ext not in self.SUPPORTED_PDF_FORMATS:
            raise ValueError("Multi-page parsing only supported for PDF files")

        import tempfile
        import subprocess

        # Check if poppler is available
        try:
            subprocess.run(['pdftoppm', '-v'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise NotImplementedError(
                "PDF support requires 'poppler-utils' to be installed.\n"
                "Install it with: sudo apt-get install poppler-utils (Ubuntu/Debian)"
            )

        all_positions = []
        all_costs = []
        all_tokens = []
        page_sources = {}  # Track which page each position came from

        total_pages = len(pages_to_process)

        for idx, page_num in enumerate(pages_to_process, 1):
            # Yield progress update
            yield {
                'current_page': idx,
                'total_pages': total_pages,
                'page_number': page_num,
                'status': 'processing'
            }

            try:
                # Convert specific page to image
                with tempfile.TemporaryDirectory() as tmp_dir:
                    output_prefix = os.path.join(tmp_dir, 'page')

                    # Convert page to JPEG at 300 DPI
                    subprocess.run(
                        ['pdftoppm', '-jpeg', '-f', str(page_num), '-l', str(page_num),
                         '-r', '300', self.file_path, output_prefix],
                        check=True,
                        capture_output=True
                    )

                    # pdftoppm creates files with -N.jpg suffix
                    img_path = f"{output_prefix}-{page_num}.jpg"

                    # Read the generated image
                    with open(img_path, 'rb') as img_file:
                        img_bytes = img_file.read()

                file_size_kb = len(img_bytes) / 1024

                # Extract positions using OpenAI
                positions_data, extraction_metadata = self.extractor.extract_positions_from_image(
                    image_data=img_bytes,
                    model=self.model,
                    mime_type="image/jpeg"
                )

                # Convert to InvestmentPosition objects
                page_positions = self._convert_to_positions(positions_data, extraction_metadata)

                # Track source page for each position
                for pos in page_positions:
                    if pos.name not in page_sources:
                        page_sources[pos.name] = []
                    page_sources[pos.name].append(page_num)

                all_positions.extend(page_positions)

                # Track costs and tokens
                all_costs.append(self.extractor.estimate_cost(self.model, file_size_kb))
                if 'tokens_used' in extraction_metadata:
                    all_tokens.append(extraction_metadata['tokens_used'])

                # Yield progress update with results
                yield {
                    'current_page': idx,
                    'total_pages': total_pages,
                    'page_number': page_num,
                    'status': 'completed',
                    'positions_found': len(page_positions),
                    'page_cost': all_costs[-1]
                }

            except Exception as e:
                # Yield error but continue with other pages
                yield {
                    'current_page': idx,
                    'total_pages': total_pages,
                    'page_number': page_num,
                    'status': 'error',
                    'error': str(e)
                }

        # Detect duplicates
        duplicate_warnings = {
            name: pages for name, pages in page_sources.items() if len(pages) > 1
        }

        # Combine metadata
        combined_metadata = {
            'file_name': os.path.basename(self.file_path),
            'file_type': 'pdf',
            'pages_processed': pages_to_process,
            'model_used': self.model,
            'total_cost': sum(all_costs),
            'total_tokens': sum(all_tokens) if all_tokens else 0,
            'position_date': datetime.now()
        }

        return all_positions, combined_metadata, duplicate_warnings

    @staticmethod
    def detect_duplicates(positions: List[InvestmentPosition]) -> Dict[str, List[int]]:
        """
        Detect duplicate asset names and return their indices

        Args:
            positions: List of InvestmentPosition objects

        Returns:
            Dictionary mapping asset name to list of indices where it appears
        """
        duplicates = {}
        for idx, pos in enumerate(positions):
            if pos.name not in duplicates:
                duplicates[pos.name] = []
            duplicates[pos.name].append(idx)

        # Filter to only return actual duplicates (appears more than once)
        return {name: indices for name, indices in duplicates.items() if len(indices) > 1}
