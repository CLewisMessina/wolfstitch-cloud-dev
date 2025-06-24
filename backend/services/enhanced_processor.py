# backend/services/enhanced_processor.py
"""
Enhanced Document Processing Service
Handles DOCX, PDF, and other document formats with robust text extraction
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Standard library imports
import re
import unicodedata
from datetime import datetime

# Document processing libraries
try:
    import docx
    from docx.document import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import PyPDF2
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import openpyxl
    import pandas as pd
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    from pptx import Presentation
    POWERPOINT_AVAILABLE = True
except ImportError:
    POWERPOINT_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    HTML_AVAILABLE = True
except ImportError:
    HTML_AVAILABLE = False

try:
    import ebooklib
    from ebooklib import epub
    EPUB_AVAILABLE = True
except ImportError:
    EPUB_AVAILABLE = False

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Enhanced document processor with robust text extraction"""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup detailed logging for debugging"""
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    
    async def process_file(
        self, 
        file_path: str, 
        max_tokens: int = 1024,
        tokenizer: str = "word-estimate"
    ) -> Dict[str, Any]:
        """
        Process any supported document format
        """
        try:
            file_ext = Path(file_path).suffix.lower()
            file_size = os.path.getsize(file_path)
            
            logger.info(f"Processing {file_ext} file: {file_path} ({file_size} bytes)")
            
            # Extract text based on file type
            if file_ext == '.docx':
                text = await self._extract_docx_text(file_path)
            elif file_ext == '.pdf':
                text = await self._extract_pdf_text(file_path)
            elif file_ext in ['.xlsx', '.xls']:
                text = await self._extract_excel_text(file_path)
            elif file_ext in ['.pptx', '.ppt']:
                text = await self._extract_powerpoint_text(file_path)
            elif file_ext in ['.html', '.htm']:
                text = await self._extract_html_text(file_path)
            elif file_ext == '.epub':
                text = await self._extract_epub_text(file_path)
            elif file_ext == '.csv':
                text = await self._extract_csv_text(file_path)
            elif file_ext == '.txt':
                text = await self._extract_txt_text(file_path)
            elif file_ext in ['.md', '.markdown']:
                text = await self._extract_markdown_text(file_path)
            elif file_ext in ['.py', '.js', '.ts', '.json', '.xml', '.yaml', '.yml']:
                text = await self._extract_code_text(file_path)
            else:
                # Fallback to text extraction
                text = await self._extract_txt_text(file_path)
            
            if not text or len(text.strip()) < 10:
                raise ValueError(f"Failed to extract meaningful text from {file_ext} file")
            
            logger.info(f"Extracted {len(text)} characters from {file_ext} file")
            
            # Clean and chunk the text
            cleaned_text = self._clean_text(text)
            chunks = self._create_chunks(cleaned_text, max_tokens)
            
            # Calculate tokens
            total_tokens = self._estimate_tokens(cleaned_text, tokenizer)
            
            result = {
                "text": cleaned_text,
                "chunks": chunks,
                "total_tokens": total_tokens,
                "chunk_count": len(chunks),
                "file_info": {
                    "filename": Path(file_path).name,
                    "format": file_ext.lstrip('.'),
                    "size_bytes": file_size,
                    "processed_at": datetime.utcnow().isoformat() + "Z"
                },
                "processing_method": "enhanced"
            }
            
            logger.info(f"✅ Successfully processed: {len(chunks)} chunks, {total_tokens} tokens")
            return result
            
        except Exception as e:
            logger.error(f"❌ Processing failed: {e}")
            raise
    
    async def _extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX files with enhanced error handling"""
        
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx not available. Install with: pip install python-docx")
        
        def extract_sync():
            try:
                doc = docx.Document(file_path)
                text_parts = []
                
                # Extract main document text
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        text_parts.append(paragraph.text.strip())
                
                # Extract table text
                for table in doc.tables:
                    for row in table.rows:
                        row_text = []
                        for cell in row.cells:
                            if cell.text.strip():
                                row_text.append(cell.text.strip())
                        if row_text:
                            text_parts.append(" | ".join(row_text))
                
                # Extract headers and footers
                for section in doc.sections:
                    # Headers
                    if section.header.paragraphs:
                        for para in section.header.paragraphs:
                            if para.text.strip():
                                text_parts.append(para.text.strip())
                    
                    # Footers
                    if section.footer.paragraphs:
                        for para in section.footer.paragraphs:
                            if para.text.strip():
                                text_parts.append(para.text.strip())
                
                full_text = "\n\n".join(text_parts)
                
                if not full_text.strip():
                    logger.warning("No text extracted from DOCX file")
                    return ""
                
                logger.info(f"DOCX extraction successful: {len(full_text)} characters")
                return full_text
                
            except Exception as e:
                logger.error(f"DOCX extraction failed: {e}")
                raise
        
        # Run in thread pool to avoid blocking
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, extract_sync
        )
    
    async def _extract_powerpoint_text(self, file_path: str) -> str:
        """Extract text from PowerPoint files"""
        
        if not POWERPOINT_AVAILABLE:
            raise ImportError("python-pptx not available. Install with: pip install python-pptx")
        
        def extract_sync():
            try:
                prs = Presentation(file_path)
                text_parts = []
                
                for slide_num, slide in enumerate(prs.slides, 1):
                    slide_text = f"=== Slide {slide_num} ===\n"
                    slide_content = []
                    
                    # Extract text from shapes
                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text.strip():
                            slide_content.append(shape.text.strip())
                        
                        # Extract text from tables
                        if hasattr(shape, "table"):
                            table_text = []
                            for row in shape.table.rows:
                                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                                if row_text:
                                    table_text.append(row_text)
                            if table_text:
                                slide_content.extend(table_text)
                    
                    if slide_content:
                        slide_text += "\n".join(slide_content)
                        text_parts.append(slide_text)
                
                full_text = "\n\n".join(text_parts)
                logger.info(f"PowerPoint extraction: {len(full_text)} characters from {len(prs.slides)} slides")
                return full_text
                
            except Exception as e:
                logger.error(f"PowerPoint extraction failed: {e}")
                raise
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, extract_sync
        )
    
    async def _extract_html_text(self, file_path: str) -> str:
        """Extract text from HTML files"""
        
        if not HTML_AVAILABLE:
            raise ImportError("beautifulsoup4 not available. Install with: pip install beautifulsoup4")
        
        def extract_sync():
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    html_content = file.read()
                
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Extract text with some structure preservation
                text_parts = []
                
                # Extract title
                title = soup.find('title')
                if title and title.text.strip():
                    text_parts.append(f"Title: {title.text.strip()}")
                
                # Extract headings and content
                for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'article', 'section']):
                    text = element.get_text().strip()
                    if text and len(text) > 10:  # Skip very short text
                        text_parts.append(text)
                
                # Extract table content
                for table in soup.find_all('table'):
                    for row in table.find_all('tr'):
                        cells = [cell.get_text().strip() for cell in row.find_all(['td', 'th'])]
                        if any(cells):
                            text_parts.append(" | ".join(cells))
                
                full_text = "\n\n".join(text_parts)
                logger.info(f"HTML extraction: {len(full_text)} characters")
                return full_text
                
            except Exception as e:
                logger.error(f"HTML extraction failed: {e}")
                raise
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, extract_sync
        )
    
    async def _extract_epub_text(self, file_path: str) -> str:
        """Extract text from EPUB files"""
        
        if not EPUB_AVAILABLE:
            raise ImportError("ebooklib not available. Install with: pip install ebooklib")
        
        def extract_sync():
            try:
                book = epub.read_epub(file_path)
                text_parts = []
                
                # Extract metadata
                title = book.get_metadata('DC', 'title')
                if title:
                    text_parts.append(f"Title: {title[0][0]}")
                
                author = book.get_metadata('DC', 'creator')
                if author:
                    text_parts.append(f"Author: {author[0][0]}")
                
                # Extract text from chapters
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        content = item.get_content().decode('utf-8')
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Remove unwanted elements
                        for element in soup(["script", "style", "nav"]):
                            element.decompose()
                        
                        chapter_text = soup.get_text()
                        if chapter_text.strip():
                            text_parts.append(chapter_text.strip())
                
                full_text = "\n\n".join(text_parts)
                logger.info(f"EPUB extraction: {len(full_text)} characters")
                return full_text
                
            except Exception as e:
                logger.error(f"EPUB extraction failed: {e}")
                raise
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, extract_sync
        )
    
    async def _extract_csv_text(self, file_path: str) -> str:
        """Extract text from CSV files"""
        
        def extract_sync():
            try:
                # Try to read with pandas for better handling
                df = pd.read_csv(file_path, encoding='utf-8')
                
                # Convert to structured text
                text_parts = []
                
                # Add column headers
                headers = " | ".join(df.columns.astype(str))
                text_parts.append(f"Columns: {headers}")
                
                # Add data rows (limit to prevent huge files)
                max_rows = 1000
                for idx, row in df.head(max_rows).iterrows():
                    row_text = " | ".join(row.astype(str))
                    text_parts.append(row_text)
                
                if len(df) > max_rows:
                    text_parts.append(f"... ({len(df) - max_rows} more rows)")
                
                full_text = "\n".join(text_parts)
                logger.info(f"CSV extraction: {len(full_text)} characters from {len(df)} rows")
                return full_text
                
            except Exception as e:
                logger.error(f"CSV extraction failed: {e}")
                # Fallback to basic text reading
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, extract_sync
        )
    
    async def _extract_code_text(self, file_path: str) -> str:
        """Extract text from code files with syntax preservation"""
        
        def extract_sync():
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    code_content = file.read()
                
                # Add basic structure for code files
                file_ext = Path(file_path).suffix.lower()
                filename = Path(file_path).name
                
                structured_text = f"=== {filename} ({file_ext}) ===\n\n{code_content}"
                
                logger.info(f"Code extraction: {len(structured_text)} characters")
                return structured_text
                
            except Exception as e:
                logger.error(f"Code extraction failed: {e}")
                raise
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, extract_sync
        )
    
    async def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF files"""
        
        if not PDF_AVAILABLE:
            raise ImportError("PDF processing libraries not available")
        
        def extract_sync():
            text_parts = []
            
            try:
                # Try pdfplumber first (better for complex layouts)
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                
            except Exception as e1:
                logger.warning(f"pdfplumber failed: {e1}, trying PyPDF2")
                
                try:
                    # Fallback to PyPDF2
                    with open(file_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        for page in pdf_reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text)
                
                except Exception as e2:
                    logger.error(f"Both PDF extractors failed: pdfplumber({e1}), PyPDF2({e2})")
                    raise e2
            
            full_text = "\n\n".join(text_parts)
            logger.info(f"PDF extraction: {len(full_text)} characters")
            return full_text
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, extract_sync
        )
    
    async def _extract_excel_text(self, file_path: str) -> str:
        """Extract text from Excel files"""
        
        if not EXCEL_AVAILABLE:
            raise ImportError("Excel processing libraries not available")
        
        def extract_sync():
            try:
                # Read all sheets
                excel_file = pd.ExcelFile(file_path)
                text_parts = []
                
                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    # Convert to string representation
                    sheet_text = f"=== {sheet_name} ===\n"
                    sheet_text += df.to_string(index=False, na_rep='')
                    text_parts.append(sheet_text)
                
                full_text = "\n\n".join(text_parts)
                logger.info(f"Excel extraction: {len(full_text)} characters")
                return full_text
                
            except Exception as e:
                logger.error(f"Excel extraction failed: {e}")
                raise
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, extract_sync
        )
    
    async def _extract_txt_text(self, file_path: str) -> str:
        """Extract text from plain text files"""
        
        def extract_sync():
            try:
                # Try different encodings
                encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
                
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as file:
                            text = file.read()
                            logger.info(f"Text file read with {encoding}: {len(text)} characters")
                            return text
                    except UnicodeDecodeError:
                        continue
                
                raise ValueError("Could not decode text file with any supported encoding")
                
            except Exception as e:
                logger.error(f"Text extraction failed: {e}")
                raise
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, extract_sync
        )
    
    async def _extract_markdown_text(self, file_path: str) -> str:
        """Extract text from Markdown files"""
        
        def extract_sync():
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    markdown_text = file.read()
                
                # Basic markdown cleaning (remove some formatting)
                text = re.sub(r'#{1,6}\s+', '', markdown_text)  # Remove headers
                text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)    # Remove bold
                text = re.sub(r'\*(.*?)\*', r'\1', text)        # Remove italic
                text = re.sub(r'`(.*?)`', r'\1', text)          # Remove inline code
                text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)  # Remove code blocks
                
                logger.info(f"Markdown extraction: {len(text)} characters")
                return text
                
            except Exception as e:
                logger.error(f"Markdown extraction failed: {e}")
                raise
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, extract_sync
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        
        # Normalize unicode
        text = unicodedata.normalize('NFKD', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Max 2 consecutive newlines
        text = re.sub(r' +', ' ', text)  # Collapse multiple spaces
        text = re.sub(r'\t+', ' ', text)  # Convert tabs to spaces
        
        # Remove control characters except newlines and tabs
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _create_chunks(self, text: str, max_tokens: int) -> List[Dict[str, Any]]:
        """Create text chunks with intelligent splitting"""
        
        # Estimate words per chunk (rough token estimation)
        words_per_chunk = max_tokens // 1.3  # Conservative estimate
        
        # Split by paragraphs first
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = ""
        current_word_count = 0
        chunk_id = 1
        
        for paragraph in paragraphs:
            para_words = len(paragraph.split())
            
            # If paragraph alone exceeds max, split it
            if para_words > words_per_chunk:
                # Save current chunk if not empty
                if current_chunk:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "chunk_id": chunk_id,
                        "tokens": self._estimate_tokens(current_chunk, "word-estimate")
                    })
                    chunk_id += 1
                    current_chunk = ""
                    current_word_count = 0
                
                # Split large paragraph by sentences
                sentences = re.split(r'[.!?]+', paragraph)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    
                    sentence_words = len(sentence.split())
                    
                    if current_word_count + sentence_words > words_per_chunk:
                        if current_chunk:
                            chunks.append({
                                "text": current_chunk.strip(),
                                "chunk_id": chunk_id,
                                "tokens": self._estimate_tokens(current_chunk, "word-estimate")
                            })
                            chunk_id += 1
                        current_chunk = sentence
                        current_word_count = sentence_words
                    else:
                        current_chunk += (" " if current_chunk else "") + sentence
                        current_word_count += sentence_words
            
            # Normal paragraph processing
            elif current_word_count + para_words > words_per_chunk:
                if current_chunk:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "chunk_id": chunk_id,
                        "tokens": self._estimate_tokens(current_chunk, "word-estimate")
                    })
                    chunk_id += 1
                current_chunk = paragraph
                current_word_count = para_words
            else:
                current_chunk += ("\n\n" if current_chunk else "") + paragraph
                current_word_count += para_words
        
        # Add final chunk
        if current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "chunk_id": chunk_id,
                "tokens": self._estimate_tokens(current_chunk, "word-estimate")
            })
        
        # Ensure at least one chunk
        if not chunks and text:
            chunks.append({
                "text": text[:int(words_per_chunk * 5)],  # Rough character limit
                "chunk_id": 1,
                "tokens": self._estimate_tokens(text, "word-estimate")
            })
        
        return chunks
    
    def _estimate_tokens(self, text: str, tokenizer: str = "word-estimate") -> int:
        """Estimate token count for text"""
        
        if tokenizer == "word-estimate":
            # Conservative word-to-token ratio
            words = len(text.split())
            return int(words * 1.3)
        
        # Add other tokenizer methods here if needed
        return len(text.split())
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats"""
        
        formats = ['txt', 'md', 'markdown', 'csv', 'json', 'xml', 'yaml', 'yml']
        
        # Add code file formats
        formats.extend(['py', 'js', 'ts', 'jsx', 'tsx', 'java', 'cpp', 'c', 'h', 'go', 'rs', 'rb', 'php'])
        
        if DOCX_AVAILABLE:
            formats.extend(['docx', 'doc'])
        
        if PDF_AVAILABLE:
            formats.append('pdf')
        
        if EXCEL_AVAILABLE:
            formats.extend(['xlsx', 'xls'])
            
        if POWERPOINT_AVAILABLE:
            formats.extend(['pptx', 'ppt'])
            
        if HTML_AVAILABLE:
            formats.extend(['html', 'htm'])
            
        if EPUB_AVAILABLE:
            formats.append('epub')
        
        return formats
    
    def __del__(self):
        """Cleanup thread pool"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
