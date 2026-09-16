# Multi-stage or optimized production build for Pre-Release Risk Monitor
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    FLASK_ENV=production

# Install essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-privileged user for security compliance (SOX / PCI-DSS compliance)
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Install Python dependencies first for efficient layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code into container
COPY . .

# Ensure data and instance directories exist with proper permissions for appuser
RUN mkdir -p /app/data /app/instance && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 5000

# Health check to monitor container availability
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Launch application with Gunicorn production WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--timeout", "120", "app:create_app()"]
