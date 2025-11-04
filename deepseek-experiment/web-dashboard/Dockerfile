# Production Dockerfile for API Server
# Railway root is set to: web-dashboard
# This version works standalone from web-dashboard directory
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Copy API server files
COPY api_server_supabase.py .
COPY supabase_client.py .

# Create minimal config structure (since we can't access parent)
# Create config directory
RUN mkdir -p config

# Copy config.py file (created separately to avoid heredoc issues)
COPY config_config.py config/config.py

# Create __init__.py that exports config from config.config
RUN echo '"""Configuration module for the trading bot."""' > config/__init__.py && \
    echo 'from .config import config' >> config/__init__.py

# Create necessary directories
RUN mkdir -p data/logs config

# Expose port (Railway sets PORT env var automatically)
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8001}/health || exit 1

# Run the API server
# The server reads PORT from environment variable automatically
CMD ["python", "api_server_supabase.py"]
