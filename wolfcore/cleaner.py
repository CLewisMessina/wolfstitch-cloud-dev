"""
Wolfstitch Cloud - Text Cleaning Module
Enhanced context-aware text cleaning for cloud processing

Extracted from desktop app's processing/clean.py with cloud optimizations:
- Context-aware cleaning based on file type
- Aggressive optimization for AI training datasets
- No UI dependencies (pure backend)
- Async-ready for cloud processing
"""

import re
from typing import Optional, Literal
import logging

logger = logging.getLogger(__name__)

ContentType = Literal['code', 'document', 'data']


def clean_text(raw_text: str, file_extension: Optional[str] = None, 
               content_type: Optional[ContentType] = None, 
               remove_headers: bool = True, normalize_whitespace: bool = True, 
               strip_bullets: bool = True) -> str:
    """
    Context-aware text cleaning based on content type with full backward compatibility
    
    This is the main entry point for text cleaning in Wolfstitch Cloud.
    It automatically determines the appropriate cleaning strategy based on file type.
    
    Args:
        raw_text (str): Raw text content to clean
        file_extension (Optional[str]): File extension (e.g., '.py', '.pdf') for context detection
        content_type (Optional[ContentType]): Override automatic content type detection
        remove_headers (bool): Remove headers/footers (document cleaning only)
        normalize_whitespace (bool): Normalize whitespace (document cleaning only)  
        strip_bullets (bool): Remove bullets (document cleaning only)
        
    Returns:
        str: Cleaned text appropriate for the content type
        
    Examples:
        >>> # Auto-detect from extension
        >>> clean_text(code_text, file_extension='.py')
        >>> 
        >>> # Manual content type
        >>> clean_text(doc_text, content_type='document')
        >>>
        >>> # Backward compatibility
        >>> clean_text(text, remove_headers=True, normalize_whitespace=True)
    """
    if not raw_text:
        return raw_text
    
    # Determine content type if file extension provided
    if file_extension and content_type is None:
        content_type = detect_content_type(file_extension)
    elif content_type is None:
        # Default to document for backward compatibility with existing calls
        content_type = 'document'
    
    logger.debug(f"Cleaning text with content_type={content_type}, length={len(raw_text)}")
    
    # Route to appropriate cleaning strategy
    if content_type == 'code':
        return clean_code_content(raw_text)
    elif content_type == 'document':
        return clean_document_content(raw_text, remove_headers, normalize_whitespace, strip_bullets)
    elif content_type == 'data':
        return clean_data_content(raw_text)
    else:
        # Fallback to document cleaning
        logger.warning(f"Unknown content_type: {content_type}, falling back to document cleaning")
        return clean_document_content(raw_text, remove_headers, normalize_whitespace, strip_bullets)


def detect_content_type(file_extension: str) -> ContentType:
    """
    Detect content type based on file extension
    
    Args:
        file_extension (str): File extension (e.g., '.py', '.pdf', '.csv')
        
    Returns:
        ContentType: One of 'code', 'document', or 'data'
    """
    # Normalize extension to lowercase
    ext = file_extension.lower()
    
    # Code file extensions
    CODE_EXTENSIONS = {
        # Programming languages
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp',
        '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.clj',
        '.hs', '.elm', '.ex', '.exs', '.erl', '.ml', '.fs', '.vb', '.pas',
        '.asm', '.s', '.sql', '.pl', '.pm', '.t', '.cgi', '.tcl', '.vim',
        '.lua', '.dart', '.sol', '.move', '.zig', '.nim', '.cr', '.jl',
        '.r', '.m', '.sh', '.bash', '.zsh', '.fish', '.ps1', '.cmd', '.bat',
        # Configuration and markup (code-like)
        '.toml', '.yaml', '.yml', '.ini', '.cfg', '.conf', '.xml',
        '.html', '.htm', '.css', '.scss', '.sass', '.less', '.svg',
        # Build and project files
        '.dockerfile', '.makefile', '.cmake', '.gradle', '.maven'
    }
    
    # Document file extensions
    DOCUMENT_EXTENSIONS = {
        '.pdf', '.docx', '.doc', '.epub', '.rtf', '.odt',
        '.md', '.markdown', '.rst', '.txt', '.text',
        '.pptx', '.ppt', '.odp', '.key'
    }
    
    # Data file extensions
    DATA_EXTENSIONS = {
        '.csv', '.tsv', '.xlsx', '.xls', '.ods',
        '.json', '.jsonl', '.ndjson', '.parquet', '.avro',
        '.sqlite', '.db', '.sql'
    }
    
    if ext in CODE_EXTENSIONS:
        return 'code'
    elif ext in DOCUMENT_EXTENSIONS:
        return 'document'
    elif ext in DATA_EXTENSIONS:
        return 'data'
    else:
        # Unknown extensions default to document
        return 'document'


def clean_code_content(text: str) -> str:
    """
    Clean code content while preserving structure and formatting
    
    Ultra-aggressive cleaning optimized for AI training datasets while
    preserving essential code structure.
    
    Cleaning operations:
    - Remove trailing whitespace from lines
    - Ultra-aggressive blank line management (max 2 sections)
    - Preserve all indentation and leading whitespace
    - Preserve all operators and syntax
    
    Args:
        text (str): Raw code content
        
    Returns:
        str: Cleaned code content
    """
    if not text:
        return text
    
    # Split into lines for line-by-line processing
    lines = text.split('\n')
    cleaned_lines = []
    
    # Remove trailing whitespace from each line (preserve leading whitespace)
    for line in lines:
        cleaned_lines.append(line.rstrip())
    
    # Ultra-aggressive blank line management for AI training
    # Allow maximum 1 consecutive blank line, but limit total blank sections
    result = []
    consecutive_blanks = 0
    total_blank_sections = 0
    max_blank_sections = 2  # Maximum logical separations allowed
    
    for line in cleaned_lines:
        if line == '':
            consecutive_blanks += 1
            # Only allow blank line if we haven't exceeded limits
            if consecutive_blanks <= 1 and total_blank_sections < max_blank_sections:
                result.append('')
        else:
            # If we just finished a blank section, count it
            if consecutive_blanks > 0:
                total_blank_sections += 1
            consecutive_blanks = 0
            result.append(line)
    
    # Join lines back together
    cleaned_text = '\n'.join(result)
    
    # Remove leading and trailing blank lines
    cleaned_text = cleaned_text.strip()
    
    logger.debug(f"Code cleaning reduced from {len(lines)} to {len(result)} lines")
    return cleaned_text


def clean_document_content(text: str, remove_headers: bool = True, 
                         normalize_whitespace: bool = True, 
                         strip_bullets: bool = True) -> str:
    """
    Clean document content with traditional text processing
    
    This preserves the original cleaning logic for documents like PDFs,
    Word files, etc. where whitespace normalization and bullet removal
    are appropriate.
    
    Args:
        text (str): Raw document text
        remove_headers (bool): Remove common headers/footers
        normalize_whitespace (bool): Normalize spacing and newlines
        strip_bullets (bool): Remove bullet points and numbering
        
    Returns:
        str: Cleaned document text
    """
    if not text:
        return text
    
    # Start with original text
    cleaned_text = text
    
    if remove_headers:
        # Strip Project Gutenberg headers/footers or similar markers
        cleaned_text = re.sub(r"\*\*\* START OF.*?\*\*\*", "", cleaned_text, flags=re.IGNORECASE | re.DOTALL)
        cleaned_text = re.sub(r"\*\*\* END OF.*?\*\*\*", "", cleaned_text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove common PDF/document headers and footers
        cleaned_text = re.sub(r"^Page \d+ of \d+.*$", "", cleaned_text, flags=re.MULTILINE)
        cleaned_text = re.sub(r"^\d+\s*$", "", cleaned_text, flags=re.MULTILINE)  # Page numbers alone

    if strip_bullets:
        # Remove bullets anywhere in the text (not just at line start)
        # First remove bullet characters themselves
        cleaned_text = re.sub(r'[•\-\*]', '', cleaned_text)
        # Then remove numbered lists at start of lines
        cleaned_text = re.sub(r"^\s*\d+\.\s+", "", cleaned_text, flags=re.MULTILINE)

    if normalize_whitespace:
        # Normalize all whitespace patterns
        # First, replace single newlines with spaces (to join wrapped lines)
        # but preserve paragraph breaks (double newlines)
        cleaned_text = re.sub(r'(?<!\n)\n(?!\n)', ' ', cleaned_text)
        # Now convert all consecutive spaces/tabs to single space
        cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)
        # Remove spaces at start and end of lines
        cleaned_text = re.sub(r'^ +', '', cleaned_text, flags=re.MULTILINE)
        cleaned_text = re.sub(r' +$', '', cleaned_text, flags=re.MULTILINE)
        # Normalize multiple newlines
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)

    # Final strip
    result = cleaned_text.strip()
    logger.debug(f"Document cleaning: {len(text)} -> {len(result)} characters")
    return result


def clean_data_content(text: str) -> str:
    """
    Clean structured data content (CSV, JSON, XML, etc.)
    
    This provides minimal cleaning appropriate for structured data files
    where formatting may be significant.
    
    Args:
        text (str): Raw data content
        
    Returns:
        str: Lightly cleaned data content
    """
    if not text:
        return text
    
    # For data files, do very minimal cleaning to preserve structure
    lines = text.split('\n')
    
    # Only remove trailing whitespace from lines (preserve everything else)
    cleaned_lines = [line.rstrip() for line in lines]
    
    # Remove excessive blank lines but be more permissive than code
    result = []
    blank_count = 0
    
    for line in cleaned_lines:
        if line == '':
            blank_count += 1
            if blank_count <= 3:  # More permissive for data files
                result.append(line)
        else:
            blank_count = 0
            result.append(line)
    
    cleaned_text = '\n'.join(result)
    result_text = cleaned_text.strip()
    
    logger.debug(f"Data cleaning: {len(lines)} -> {len(result)} lines")
    return result_text


# Async versions for cloud processing
async def clean_text_async(raw_text: str, file_extension: Optional[str] = None, 
                          content_type: Optional[ContentType] = None, 
                          remove_headers: bool = True, normalize_whitespace: bool = True, 
                          strip_bullets: bool = True) -> str:
    """
    Async wrapper for clean_text to support cloud processing
    
    Args: Same as clean_text()
    Returns: Same as clean_text()
    """
    # For now, cleaning is CPU-bound and fast enough to run synchronously
    # In future, could use asyncio.to_thread for very large texts
    return clean_text(raw_text, file_extension, content_type, 
                     remove_headers, normalize_whitespace, strip_bullets)


# Export the main interface
__all__ = [
    'clean_text',
    'clean_text_async',
    'detect_content_type', 
    'clean_code_content',
    'clean_document_content',
    'clean_data_content'
]