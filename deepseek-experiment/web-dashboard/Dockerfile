# Production Dockerfile for API Server
# Railway root should be set to: deepseek-experiment (parent directory)
# This allows access to both web-dashboard and config directories
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

# Copy requirements from web-dashboard
COPY web-dashboard/requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Copy API server files from web-dashboard
COPY web-dashboard/api_server_supabase.py .
COPY web-dashboard/supabase_client.py .

# Copy config directory (needed for imports)
COPY config ./config

# Create necessary directories
RUN mkdir -p data/logs

# Expose port (Railway sets PORT env var automatically)
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8001}/health || exit 1

# Run the API server
# The server reads PORT from environment variable automatically
CMD ["python", "api_server_supabase.py"]
