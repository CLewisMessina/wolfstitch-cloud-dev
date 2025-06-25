# backend/models/schemas.py
"""
Wolfstitch Cloud - Pydantic Schemas
Request and response models for API endpoints
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExportFormat(str, Enum):
    JSONL = "jsonl"
    CSV = "csv"
    TXT = "txt"
    JSON = "json"


class TokenizerType(str, Enum):
    WORD_ESTIMATE = "word-estimate"
    GPT2 = "gpt2"
    TIKTOKEN_CL100K = "tiktoken-cl100k"
    TIKTOKEN_P50K = "tiktoken-p50k"
    BERT = "bert"
    SENTENCE_TRANSFORMER = "sentence-transformer"


class UserTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


# =============================================================================
# BASE MODELS
# =============================================================================

class APIResponse(BaseModel):
    """Standard API response format"""
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# FILE UPLOAD MODELS
# =============================================================================

class FileUploadResponse(BaseModel):
    """Response for file upload"""
    file_id: str
    filename: str
    size_bytes: int
    format: str
    upload_url: Optional[str] = None  # For direct upload to S3
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FileInfo(BaseModel):
    """File information"""
    file_id: str
    filename: str
    size_bytes: int
    format: str
    upload_time: datetime
    processed: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# PROCESSING MODELS
# =============================================================================

class ProcessingConfig(BaseModel):
    """Configuration for text processing"""
    tokenizer: str = Field(default="gpt-4", description="Tokenizer to use")
    max_tokens: int = Field(default=1024, ge=100, le=8192)
    overlap_tokens: int = Field(default=50, ge=0, le=500)
    chunk_method: str = Field(default="paragraph", description="Chunking method")
    chunking_method: Optional[str] = Field(default=None, pattern="^(paragraph|sentence|custom)$")
    custom_delimiter: Optional[str] = None
    preserve_structure: bool = Field(default=True, description="Preserve document structure")
    preserve_formatting: bool = True
    remove_headers_footers: bool = True
    remove_headers: bool = Field(default=True, description="Remove headers/footers")
    normalize_whitespace: bool = Field(default=True, description="Normalize whitespace")
    min_chunk_size: int = Field(default=50, ge=10, le=1000)
    
    @validator('custom_delimiter')
    def validate_custom_delimiter(cls, v, values):
        if values.get('chunking_method') == 'custom' and not v:
            raise ValueError('custom_delimiter required when chunking_method is custom')
        return v


class ProcessingRequest(BaseModel):
    """Request to start processing a file"""
    file_id: str
    config: ProcessingConfig = Field(default_factory=ProcessingConfig)
    export_format: ExportFormat = ExportFormat.JSONL
    webhook_url: Optional[str] = None
    priority: int = Field(default=0, ge=0, le=10)  # Higher = more priority


class ChunkData(BaseModel):
    """Individual chunk data"""
    id: int
    text: str
    token_count: int
    start_position: int
    end_position: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProcessingResult(BaseModel):
    """Complete processing result"""
    filename: str
    total_chunks: int
    total_tokens: int
    total_characters: int
    processing_time: float
    chunks: List[Dict[str, Any]]
    file_info: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProcessingStatusDetail(BaseModel):
    """Processing job status detail"""
    job_id: str
    status: ProcessingStatus
    progress: float = Field(ge=0.0, le=100.0)
    current_step: str
    estimated_completion: Optional[datetime] = None
    chunks_processed: int = 0
    total_chunks_estimated: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class JobStatusResponse(BaseModel):
    """Response for job status queries"""
    job_id: str
    status: ProcessingStatus
    progress: float = Field(ge=0, le=100, description="Progress percentage")
    filename: str
    created_at: str
    export_format: str
    
    # Optional fields based on status
    error: Optional[str] = None
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    download_url: Optional[str] = None
    total_chunks: Optional[int] = None
    total_tokens: Optional[int] = None


# =============================================================================
# USER MANAGEMENT MODELS
# =============================================================================

class UserCreate(BaseModel):
    """User creation request"""
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    company: Optional[str] = None


class UserResponse(BaseModel):
    """User response data"""
    user_id: str
    email: str
    full_name: Optional[str]
    company: Optional[str]
    tier: UserTier
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool


class UserUpdate(BaseModel):
    """User update request"""
    full_name: Optional[str] = None
    company: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)


# =============================================================================
# AUTHENTICATION MODELS
# =============================================================================

class TokenResponse(BaseModel):
    """Authentication token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request"""
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


# =============================================================================
# USAGE AND BILLING MODELS
# =============================================================================

class UsageStats(BaseModel):
    """User usage statistics"""
    user_id: str
    current_period_start: datetime
    current_period_end: datetime
    files_processed: int
    total_tokens_processed: int
    api_calls_made: int
    storage_used_bytes: int
    limits: Dict[str, int]  # tier-based limits


class BillingInfo(BaseModel):
    """Billing information"""
    user_id: str
    tier: UserTier
    subscription_id: Optional[str] = None
    current_period_start: datetime
    current_period_end: datetime
    amount_due: float
    currency: str = "USD"
    status: str  # active, past_due, cancelled, etc.


# =============================================================================
# ANALYTICS MODELS
# =============================================================================

class DocumentAnalytics(BaseModel):
    """Analytics for processed document"""
    file_id: str
    filename: str
    format: str
    size_bytes: int
    total_chunks: int
    total_tokens: int
    avg_tokens_per_chunk: float
    min_tokens_per_chunk: int
    max_tokens_per_chunk: int
    processing_time: float
    tokenizer_used: str
    quality_score: Optional[float] = None  # Premium feature
    language_detected: Optional[str] = None
    
    # Token distribution
    token_distribution: Dict[str, int] = Field(default_factory=dict)  # ranges: 0-100, 100-500, etc.
    
    # Chunk quality metrics (premium)
    chunk_quality_metrics: Optional[Dict[str, float]] = None


class BatchAnalytics(BaseModel):
    """Analytics for batch processing"""
    batch_id: str
    total_files: int
    successful_files: int
    failed_files: int
    total_tokens: int
    total_chunks: int
    avg_processing_time: float
    total_processing_time: float
    formats_processed: Dict[str, int]
    tokenizers_used: Dict[str, int]


# =============================================================================
# EXPORT MODELS
# =============================================================================

class ExportRequest(BaseModel):
    """Request to export processed data"""
    job_id: str
    format: ExportFormat
    include_metadata: bool = True
    chunk_range: Optional[Dict[str, int]] = None  # {"start": 0, "end": 100}
    custom_fields: Optional[List[str]] = None


class ExportResponse(BaseModel):
    """Export response"""
    export_id: str
    job_id: str
    format: ExportFormat
    download_url: str
    expires_at: datetime
    size_bytes: int
    created_at: datetime


class ExportInfo(BaseModel):
    """Information about generated export file"""
    filename: str
    file_path: str
    format: str
    size_bytes: int
    size_readable: str
    created_at: str
    chunks_count: int
    tokens_count: int


class StorageInfo(BaseModel):
    """Information about stored file"""
    storage_id: str
    download_url: str
    filename: str
    size_bytes: int
    expires_at: str


# =============================================================================
# WEBHOOK MODELS
# =============================================================================

class WebhookEvent(BaseModel):
    """Webhook event data"""
    event_type: str  # processing.completed, processing.failed, etc.
    job_id: str
    user_id: str
    timestamp: datetime
    data: Dict[str, Any]


class WebhookConfig(BaseModel):
    """Webhook configuration"""
    url: str
    events: List[str]
    secret: Optional[str] = None
    active: bool = True


# =============================================================================
# ERROR MODELS
# =============================================================================

class ErrorDetail(BaseModel):
    """Detailed error information"""
    code: str
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    message: str = "Validation failed"
    errors: List[ErrorDetail]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# PROGRESSIVE LOADING MODELS
# =============================================================================

class ProgressiveLoadingStatus(BaseModel):
    """Status of progressive feature loading"""
    enabled: bool
    features_loaded: Dict[str, bool]
    loading_progress: Dict[str, float]
    estimated_completion: Optional[datetime] = None
    available_tokenizers: List[str]
    premium_features_available: bool


class FeatureAvailability(BaseModel):
    """Feature availability for user"""
    user_tier: UserTier
    available_features: List[str]
    tokenizers: List[str]
    rate_limits: Dict[str, int]
    storage_limit_gb: int
    max_file_size_mb: int