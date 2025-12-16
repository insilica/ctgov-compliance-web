# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (Node.js for frontend build + build tooling)
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    postgresql-client \
    ca-certificates \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./
COPY web/frontend/package.json web/frontend/package-lock.json ./web/frontend/

# Install frontend dependencies
RUN cd web/frontend && npm ci

# Copy application code
COPY web/frontend/ ./web/frontend/
RUN cd web/frontend && npm run build && rm -rf node_modules
COPY web/ ./web/
COPY scripts/ ./scripts/
COPY tests/ ./tests/

# Install Python dependencies using uv
RUN uv sync --frozen --no-dev

# Set environment variables
ENV FLASK_APP=web.app:app
ENV PYTHONUNBUFFERED=1

# Expose the application port
EXPOSE 6525

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:6525/health || exit 1

# Run the application with gunicorn
CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:6525", "--workers", "4", "--timeout", "120", "web.app:app"]
