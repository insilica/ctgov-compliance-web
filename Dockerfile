# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Copy application code (needed for editable install)
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

# Run the application with gunicorn
CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:6525", "--workers", "4", "--timeout", "120", "web.app:app"]
