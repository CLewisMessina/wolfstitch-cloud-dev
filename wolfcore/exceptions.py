"""
Wolfcore Exceptions - Custom Exception Classes
Provides specific exceptions for different types of errors in the wolfcore library
"""


class WolfcoreError(Exception):
    """Base exception for all wolfcore-related errors"""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message


class ParsingError(WolfcoreError):
    """Raised when file parsing fails"""
    
    def __init__(self, message: str, filename: str = None, format: str = None):
        details = {}
        if filename:
            details['filename'] = filename
        if format:
            details['format'] = format
        super().__init__(message, details)


class UnsupportedFormatError(WolfcoreError):
    """Raised when attempting to parse an unsupported file format"""
    
    def __init__(self, message: str, format: str = None, supported_formats: list = None):
        details = {}
        if format:
            details['format'] = format
        if supported_formats:
            details['supported_formats'] = ', '.join(supported_formats)
        super().__init__(message, details)


class ProcessingError(WolfcoreError):
    """Raised when processing operations fail"""
    
    def __init__(self, message: str, operation: str = None, stage: str = None):
        details = {}
        if operation:
            details['operation'] = operation
        if stage:
            details['stage'] = stage
        super().__init__(message, details)


class TokenizerError(WolfcoreError):
    """Raised when tokenizer operations fail"""
    
    def __init__(self, message: str, tokenizer: str = None, available_tokenizers: list = None):
        details = {}
        if tokenizer:
            details['tokenizer'] = tokenizer
        if available_tokenizers:
            details['available_tokenizers'] = ', '.join(available_tokenizers)
        super().__init__(message, details)


class CleaningError(WolfcoreError):
    """Raised when text cleaning fails"""
    
    def __init__(self, message: str, cleaning_operation: str = None):
        details = {}
        if cleaning_operation:
            details['cleaning_operation'] = cleaning_operation
        super().__init__(message, details)


class ChunkingError(WolfcoreError):
    """Raised when text chunking fails"""
    
    def __init__(self, message: str, chunking_method: str = None, chunk_size: int = None):
        details = {}
        if chunking_method:
            details['chunking_method'] = chunking_method
        if chunk_size:
            details['chunk_size'] = chunk_size
        super().__init__(message, details)


class ExportError(WolfcoreError):
    """Raised when export operations fail"""
    
    def __init__(self, message: str, export_format: str = None, filename: str = None):
        details = {}
        if export_format:
            details['export_format'] = export_format
        if filename:
            details['filename'] = filename
        super().__init__(message, details)


class ConfigurationError(WolfcoreError):
    """Raised when configuration is invalid"""
    
    def __init__(self, message: str, config_key: str = None, config_value: str = None):
        details = {}
        if config_key:
            details['config_key'] = config_key
        if config_value:
            details['config_value'] = str(config_value)
        super().__init__(message, details)


class ValidationError(WolfcoreError):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: str = None, value: str = None):
        details = {}
        if field:
            details['field'] = field
        if value:
            details['value'] = str(value)
        super().__init__(message, details)