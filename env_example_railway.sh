# Environment Configuration for Railway
ENVIRONMENT=production
DEBUG=false

# Security
SECRET_KEY=your-super-secure-secret-key-generate-this-with-secrets-token-urlsafe-32

# Database (Railway auto-provides this)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (Railway auto-provides this)
REDIS_URL=${{Redis.REDIS_URL}}

# Server Configuration
LOG_LEVEL=INFO
ALLOWED_HOSTS=*

# API Configuration
API_V1_STR=/api/v1
PROJECT_NAME=Wolfstitch Cloud

# File Upload Configuration
MAX_FILE_SIZE=100000000
UPLOAD_DIR=/tmp/uploads

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=3600