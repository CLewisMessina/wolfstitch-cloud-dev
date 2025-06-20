# Wolfstitch Cloud - Environment Variables Template
# Copy this file to .env and fill in your actual values

# =============================================================================
# APPLICATION SETTINGS
# =============================================================================
DEBUG=true
ENVIRONMENT=development
SECRET_KEY=your-secret-key-here
API_VERSION=v1

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
# Development (SQLite)
DATABASE_URL=sqlite:///./wolfstitch.db

# Production (PostgreSQL)  
# DATABASE_URL=postgresql://user:password@localhost/wolfstitch_cloud

# =============================================================================
# REDIS CONFIGURATION (for background jobs)
# =============================================================================
REDIS_URL=redis://localhost:6379/0

# =============================================================================
# AUTHENTICATION & SECURITY
# =============================================================================
# JWT token settings
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Password hashing
BCRYPT_ROUNDS=12

# =============================================================================
# FILE STORAGE
# =============================================================================
# Local development
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=100

# Production S3 (uncomment when ready)
# AWS_ACCESS_KEY_ID=your-access-key
# AWS_SECRET_ACCESS_KEY=your-secret-key  
# AWS_BUCKET_NAME=wolfstitch-files
# AWS_REGION=us-east-1

# =============================================================================
# EXTERNAL SERVICES
# =============================================================================
# Stripe (for billing)
# STRIPE_PUBLISHABLE_KEY=pk_test_...
# STRIPE_SECRET_KEY=sk_test_...
# STRIPE_WEBHOOK_SECRET=whsec_...

# Clerk (for authentication) 
# CLERK_SECRET_KEY=sk_test_...
# CLERK_PUBLISHABLE_KEY=pk_test_...

# Email service (SendGrid, Mailgun, etc.)
# EMAIL_SERVICE_API_KEY=your-email-api-key
# FROM_EMAIL=noreply@wolfstitch.com

# =============================================================================
# PREMIUM TOKENIZER SETTINGS
# =============================================================================
# HuggingFace API (for premium tokenizers)
# HUGGINGFACE_API_KEY=hf_...

# OpenAI API (for tiktoken validation)
# OPENAI_API_KEY=sk-...

# =============================================================================
# MONITORING & LOGGING
# =============================================================================
# Sentry (error tracking)
# SENTRY_DSN=https://...@sentry.io/...

# Log level
LOG_LEVEL=INFO

# =============================================================================
# BACKGROUND JOB SETTINGS  
# =============================================================================
# RQ worker settings
RQ_DEFAULT_TIMEOUT=300
RQ_RESULT_TTL=3600
MAX_CONCURRENT_JOBS=5

# =============================================================================
# API RATE LIMITING
# =============================================================================
# Rate limits per user tier
FREE_TIER_REQUESTS_PER_HOUR=100
PRO_TIER_REQUESTS_PER_HOUR=1000
ENTERPRISE_TIER_REQUESTS_PER_HOUR=10000

# =============================================================================
# DEVELOPMENT SETTINGS
# =============================================================================
# Enable/disable features during development
ENABLE_PREMIUM_FEATURES=true
ENABLE_COST_ANALYSIS=true
ENABLE_ANALYTICS=true

# Test file paths (for development)
TEST_FILES_DIR=./test-files

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000

# =============================================================================
# DEPLOYMENT SETTINGS
# =============================================================================
# Domain and SSL
# DOMAIN=api.wolfstitch.com
# SSL_CERT_PATH=/path/to/cert.pem
# SSL_KEY_PATH=/path/to/key.pem

# Load balancer health check
HEALTH_CHECK_PATH=/health

# =============================================================================
# LEGACY DESKTOP APP COMPATIBILITY
# =============================================================================
# Settings for maintaining compatibility with desktop app
DESKTOP_SESSION_COMPATIBILITY=true
LEGACY_EXPORT_FORMATS=true