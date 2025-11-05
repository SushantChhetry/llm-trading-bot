# Risk Service Dockerfile
# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    RISK_SERVICE_PORT=8003

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the services directory (risk service code)
COPY services ./services

# Copy the directory structure for imports (if risk_service needs config, etc.)
COPY config ./config

# Create data and logs directories
RUN mkdir -p data/logs

# Expose port 8003 (risk service port)
EXPOSE 8003

# Health check - Use /health endpoint
# Note: Risk service uses RISK_SERVICE_PORT (8003) which takes precedence over Railway's PORT
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run the risk service
# RISK_SERVICE_PORT is set as ENV above (defaults to 8003)
# This takes precedence over Railway's automatically-set PORT environment variable
# Railway's PORT is ignored - risk service always uses RISK_SERVICE_PORT (8003)
CMD ["python", "services/risk_service.py"]

