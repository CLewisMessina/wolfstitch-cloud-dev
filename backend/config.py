#backend\config.py
"""
Wolfstitch Cloud - Application Configuration
Centralized configuration management using environment variables
"""

from pydantic_settings import BaseSettings
from pydantic import validator, field_validator
from typing import List, Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # =============================================================================
    # APPLICATION SETTINGS
    # =============================================================================
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    API_VERSION: str = "v1"
    LOG_LEVEL: str = "INFO"
    
    # =============================================================================
    # DATABASE CONFIGURATION  
    # =============================================================================
    DATABASE_URL: str = "sqlite:///./wolfstitch.db"
    
    # =============================================================================
    # REDIS CONFIGURATION
    # =============================================================================
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # =============================================================================
    # AUTHENTICATION & SECURITY
    # =============================================================================
    JWT_SECRET_KEY: str = "jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    BCRYPT_ROUNDS: int = 12
    
    # =============================================================================
    # FILE STORAGE
    # =============================================================================
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_FILE_EXTENSIONS: List[str] = [
        # Documents
        "pdf", "docx", "txt", "epub", "html", "md", "rtf",
        # Spreadsheets  
        "xlsx", "csv",
        # Presentations
        "pptx",
        # Code files
        "py", "js", "jsx", "ts", "tsx", "java", "cpp", "c", "h", 
        "go", "rs", "rb", "php", "swift", "kt", "cs", "r", "scala",
        # Config files
        "json", "yaml", "yml", "toml", "ini", "xml"
    ]
    
    # AWS S3 Configuration (for production)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_BUCKET_NAME: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    
    # =============================================================================
    # EXTERNAL SERVICES
    # =============================================================================
    # Stripe
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # Clerk
    CLERK_SECRET_KEY: Optional[str] = None
    CLERK_PUBLISHABLE_KEY: Optional[str] = None
    
    # Email
    EMAIL_SERVICE_API_KEY: Optional[str] = None
    FROM_EMAIL: str = "noreply@wolfstitch.com"
    
    # HuggingFace (for premium tokenizers)
    HUGGINGFACE_API_KEY: Optional[str] = None
    
    # OpenAI (for tiktoken validation)
    OPENAI_API_KEY: Optional[str] = None
    
    # Sentry (error tracking)
    SENTRY_DSN: Optional[str] = None
    
    # =============================================================================
    # BACKGROUND JOB SETTINGS
    # =============================================================================
    RQ_DEFAULT_TIMEOUT: int = 300  # 5 minutes
    RQ_RESULT_TTL: int = 3600      # 1 hour
    MAX_CONCURRENT_JOBS: int = 5
    
    # =============================================================================
    # API RATE LIMITING
    # =============================================================================
    FREE_TIER_REQUESTS_PER_HOUR: int = 100
    PRO_TIER_REQUESTS_PER_HOUR: int = 1000
    ENTERPRISE_TIER_REQUESTS_PER_HOUR: int = 10000
    
    # =============================================================================
    # FEATURE FLAGS
    # =============================================================================
    ENABLE_PREMIUM_FEATURES: bool = True
    ENABLE_COST_ANALYSIS: bool = True
    ENABLE_ANALYTICS: bool = True
    DESKTOP_SESSION_COMPATIBILITY: bool = True
    LEGACY_EXPORT_FORMATS: bool = True
    
    # =============================================================================
    # CORS AND SECURITY
    # =============================================================================
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: Optional[List[str]] = None
    ALLOWED_HOSTS: Optional[List[str]] = None

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def set_allowed_origins(cls, v, info):
        frontend_url = info.data.get("FRONTEND_URL", "http://localhost:3000")
        return [
            frontend_url,
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://wolfstitch.dev",
            "https://app.wolfstitch.dev"
        ]

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def set_allowed_hosts(cls, v, info):
        if info.data.get("ENVIRONMENT") == "production":
            return [
                "api.wolfstitch.dev",
                "wolfstitch.dev",
                "app.wolfstitch.dev"
            ]
        return ["*"]
    
    # =============================================================================
    # DEPLOYMENT SETTINGS
    # =============================================================================
    DOMAIN: Optional[str] = None
    HEALTH_CHECK_PATH: str = "/health"
    
    # =============================================================================
    # DEVELOPMENT SETTINGS
    # =============================================================================
    TEST_FILES_DIR: str = "./test-files"
    
    @validator("UPLOAD_DIR", pre=True, always=True)
    def create_upload_dir(cls, v):
        """Ensure upload directory exists"""
        Path(v).mkdir(exist_ok=True)
        return v
    
    @validator("MAX_FILE_SIZE_MB")
    def validate_file_size(cls, v):
        """Validate file size limit"""
        if v <= 0 or v > 1000:  # Max 1GB
            raise ValueError("File size must be between 1MB and 1000MB")
        return v
    
    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    @property
    def database_url_async(self) -> str:
        """Get async database URL for SQLAlchemy"""
        if self.DATABASE_URL.startswith("sqlite"):
            return self.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
        elif self.DATABASE_URL.startswith("postgresql"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        return self.DATABASE_URL
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() == "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "formatter": "detailed",
            "class": "logging.FileHandler",
            "filename": "wolfstitch.log",
        },
    },
    "root": {
        "level": settings.LOG_LEVEL,
        "handlers": ["default"] + (["file"] if settings.is_production else []),
    },
}