# Multi-stage build for Architectural DNA MCP Server
FROM python:3.14-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for downloaded models
RUN mkdir -p /app/.cache/fastembed

# Make entrypoint executable
RUN chmod +x docker-entrypoint.sh

# Healthcheck - verify SSE server is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -sf http://localhost:8080/sse > /dev/null || exit 1

# Run as non-root user
RUN useradd -m -u 1000 dna && chown -R dna:dna /app
USER dna

# Expose MCP server port
EXPOSE 8080

# Environment for SSE server mode
ENV MCP_TRANSPORT=sse
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8080

# Set entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command - runs MCP server in SSE mode
CMD ["python", "dna_server.py", "--sse"]
