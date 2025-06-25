# backend/config.py
"""
Wolfstitch Cloud - Application Configuration
Environment-aware configuration management for dev/prod domains
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
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
    # DOMAIN CONFIGURATION - Environment-aware
    # =============================================================================
    API_BASE_URL: Optional[str] = None
    FRONTEND_URL: Optional[str] = None
    
    @field_validator("API_BASE_URL", mode="before")
    @classmethod
    def set_api_base_url(cls, v, info):
        """Set API base URL based on environment if not explicitly provided"""
        if v:
            return v
        
        environment = info.data.get("ENVIRONMENT", "development").lower()
        
        if environment == "production":
            return "https://api.wolfstitch.dev"
        elif environment in ["development", "staging", "dev"]:
            return "https://api-dev.wolfstitch.dev"
        else:
            # Fallback for local development
            return "http://localhost:8000"
    
    @field_validator("FRONTEND_URL", mode="before") 
    @classmethod
    def set_frontend_url(cls, v, info):
        """Set frontend URL based on environment if not explicitly provided"""
        if v:
            return v
            
        environment = info.data.get("ENVIRONMENT", "development").lower()
        
        if environment == "production":
            return "https://app.wolfstitch.dev"
        elif environment in ["development", "staging", "dev"]:
            return "https://dev.wolfstitch.dev"
        else:
            # Fallback for local development
            return "http://localhost:3000"
    
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
    STORAGE_DIR: str = "./storage"
    EXPORT_DIR: str = "./exports"
    MAX_FILE_SIZE_MB: int = 100
    FILE_RETENTION_HOURS: int = 24
    
    ALLOWED_FILE_EXTENSIONS: List[str] = [
        # Documents
        "pdf", "docx", "txt", "epub", "html", "md", "rtf",
        # Spreadsheets  
        "xlsx", "csv", "xls",
        # Presentations
        "pptx", "ppt",
        # Code files
        "py", "js", "ts", "java", "cpp", "c", "cs", "php", "rb", "go", "rs",
        # Data files
        "json", "jsonl", "xml", "yaml", "yml"
    ]
    
    # =============================================================================
    # CORS AND SECURITY - Environment-aware
    # =============================================================================
    ALLOWED_ORIGINS: Optional[List[str]] = None
    ALLOWED_HOSTS: Optional[List[str]] = None
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def set_allowed_origins(cls, v, info):
        """Set CORS origins based on environment"""
        if v:
            return v
            
        environment = info.data.get("ENVIRONMENT", "development").lower()
        frontend_url = info.data.get("FRONTEND_URL")
        
        base_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        ]
        
        if environment == "production":
            return base_origins + [
                "https://wolfstitch.dev",
                "https://www.wolfstitch.dev", 
                "https://app.wolfstitch.dev"
            ]
        else:
            return base_origins + [
                "https://wolfstitch.dev",
                "https://www.wolfstitch.dev",
                "https://dev.wolfstitch.dev",
                "https://api-dev.wolfstitch.dev"
            ]
    
    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def set_allowed_hosts(cls, v, info):
        """Set allowed hosts based on environment"""
        if v:
            return v
            
        environment = info.data.get("ENVIRONMENT", "development").lower()
        
        # Base hosts that are always allowed
        base_hosts = [
            "*.railway.app", 
            "*.up.railway.app",
            "localhost",
            "127.0.0.1"
        ]
        
        if environment == "production":
            return base_hosts + [
                "api.wolfstitch.dev",
                "wolfstitch.dev",
                "app.wolfstitch.dev",
                "www.wolfstitch.dev"
            ]
        else:
            return base_hosts + [
                "api-dev.wolfstitch.dev",
                "dev.wolfstitch.dev",
                "wolfstitch.dev",
                "www.wolfstitch.dev"
            ]
    
    # =============================================================================
    # PROCESSING CONFIGURATION
    # =============================================================================
    MAX_CONCURRENT_JOBS: int = 10
    JOB_TIMEOUT_SECONDS: int = 300  # 5 minutes
    CHUNK_SIZE_LIMIT: int = 8192  # 8KB per chunk
    MAX_CHUNKS_PER_FILE: int = 10000
    
    # =============================================================================
    # RATE LIMITING
    # =============================================================================
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 3600  # 1 hour
    ANONYMOUS_RATE_LIMIT: int = 10
    
    # =============================================================================
    # FEATURE FLAGS
    # =============================================================================
    ENABLE_ANALYTICS: bool = True
    ENABLE_COST_ANALYSIS: bool = True
    ENABLE_PREMIUM_FEATURES: bool = True
    ENABLE_USER_UPLOADS: bool = True
    ENABLE_BACKGROUND_JOBS: bool = True
    
    # =============================================================================
    # MONITORING AND LOGGING
    # =============================================================================
    HEALTH_CHECK_PATH: str = "/health"
    METRICS_ENABLED: bool = True
    
    # =============================================================================
    # VALIDATION AND COMPUTED PROPERTIES
    # =============================================================================
    @field_validator("UPLOAD_DIR", "STORAGE_DIR", "EXPORT_DIR", mode="before")
    @classmethod
    def create_directories(cls, v):
        """Ensure directories exist"""
        Path(v).mkdir(parents=True, exist_ok=True)
        return v
    
    @field_validator("MAX_FILE_SIZE_MB")
    @classmethod
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
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() in ["development", "dev"]
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging"""
        return self.ENVIRONMENT.lower() == "staging"
    
    @property
    def database_url_async(self) -> str:
        """Get async database URL for SQLAlchemy"""
        if self.DATABASE_URL.startswith("sqlite"):
            return self.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
        elif self.DATABASE_URL.startswith("postgresql"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        return self.DATABASE_URL
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Logging configuration based on environment
def get_logging_config():
    """Get logging configuration based on environment"""
    base_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
            },
            "json": {
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
            }
        },
        "handlers": {
            "console": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            }
        },
        "root": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console"],
        },
        "loggers": {
            "wolfstitch": {
                "level": settings.LOG_LEVEL,
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "fastapi": {
                "level": "INFO", 
                "handlers": ["console"],
                "propagate": False,
            }
        }
    }
    
    # Add file handler in production
    if settings.is_production:
        base_config["handlers"]["file"] = {
            "formatter": "detailed",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "wolfstitch.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
        base_config["root"]["handlers"].append("file")
        base_config["loggers"]["wolfstitch"]["handlers"].append("file")
    
    return base_config


# Environment-specific configurations
def get_environment_config():
    """Get environment-specific configuration summary"""
    return {
        "environment": settings.ENVIRONMENT,
        "is_production": settings.is_production,
        "is_development": settings.is_development,
        "is_staging": settings.is_staging,
        "api_base_url": settings.API_BASE_URL,
        "frontend_url": settings.FRONTEND_URL,
        "allowed_origins": settings.ALLOWED_ORIGINS,
        "allowed_hosts": settings.ALLOWED_HOSTS[:3] if settings.ALLOWED_HOSTS else [],  # First 3 for logs
        "debug": settings.DEBUG,
        "log_level": settings.LOG_LEVEL
    }