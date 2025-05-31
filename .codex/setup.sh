#!/bin/bash
set -euo pipefail

echo "Setting up development environment for Codex..."

# Update package lists
apt-get update

# Install system dependencies
echo "Installing system packages..."
apt-get install -y \
    postgresql-client-15 \
    redis-tools \
    gcc \
    python3-dev \
    libpq-dev \
    curl \
    wget \
    unzip

# Install AWS CLI v2
echo "Installing AWS CLI v2..."
if ! command -v aws &> /dev/null; then
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    ./aws/install
    rm -rf aws awscliv2.zip
fi

# Install Flyway
echo "Installing Flyway..."
if ! command -v flyway &> /dev/null; then
    FLYWAY_VERSION="10.4.1"
    wget -qO- https://download.red-gate.com/maven/release/com/redgate/flyway/flyway-commandline/${FLYWAY_VERSION}/flyway-commandline-${FLYWAY_VERSION}-linux-x64.tar.gz | tar -xz
    mv flyway-${FLYWAY_VERSION} /opt/flyway
    ln -sf /opt/flyway/flyway /usr/local/bin/flyway
fi

# Upgrade pip
echo "Upgrading pip..."
python3 -m pip install --upgrade pip

# Install Python dependencies
echo "Installing Python packages..."
python3 -m pip install \
    flask \
    python-dotenv \
    stripe \
    requests \
    urllib3 \
    flask-login \
    flask-wtf \
    sendgrid \
    gunicorn \
    psycopg2-binary \
    email-validator \
    boto3 \
    openai \
    celery \
    redis \
    flask-socketio \
    gevent \
    gevent-websocket \
    pandas \
    annotated-types \
    pydantic-core==2.16.3 \
    pydantic==2.6.4

# Set up environment variables for development
echo "Setting up environment variables..."
cat > /tmp/dev_env.sh << 'EOF'
# PostgreSQL settings
export DB_HOST="localhost"
export DB_PORT="5464"
export DB_NAME="ctgov-web"
export DB_USER="postgres"
export DB_PASSWORD="devpassword"

# Flask settings
export FLASK_APP=webserver.app
export FLASK_ENV=development
export DEBUG=1
export PREFERRED_URL_SCHEME=http
export SERVER_NAME="localhost:6513"

# Add to PATH
export PATH="/opt/flyway:$PATH"
EOF

# Source the environment in the current shell
source /tmp/dev_env.sh

# Make environment available for future sessions
echo "source /tmp/dev_env.sh" >> ~/.bashrc

echo "Setup complete! Environment variables have been configured."
echo "You can start your Flask app with: flask run --host=0.0.0.0 --port=6513"
echo ""
echo "Note: You'll need to start PostgreSQL and Redis services separately."
echo "PostgreSQL should be configured to listen on port 5464 with the credentials above."
