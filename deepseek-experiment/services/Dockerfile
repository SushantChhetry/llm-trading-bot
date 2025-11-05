# Risk Service Dockerfile
# Use Python 3.13 slim image
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
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run the risk service
CMD ["python", "services/risk_service.py"]

