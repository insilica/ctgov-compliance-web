#!/bin/bash
set -euo pipefail

echo "Setting up development environment for Codex..."

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to handle errors
handle_error() {
    echo "Error: $1"
    exit 1
}

# Install Flyway if not present
echo "Checking Flyway installation..."
if ! command_exists flyway; then
    echo "Installing Flyway..."
    FLYWAY_VERSION="10.4.1"
    wget -qO- https://download.red-gate.com/maven/release/com/redgate/flyway/flyway-commandline/${FLYWAY_VERSION}/flyway-commandline-${FLYWAY_VERSION}-linux-x64.tar.gz | tar -xz || handle_error "Failed to download/extract Flyway"
    mv flyway-${FLYWAY_VERSION} /opt/flyway || handle_error "Failed to move Flyway to /opt"
    ln -sf /opt/flyway/flyway /usr/local/bin/flyway || handle_error "Failed to create Flyway symlink"
fi

# Verify Python3 is available
if ! command_exists python3; then
    handle_error "Python3 is not installed"
fi

# Upgrade pip with error handling
echo "Upgrading pip..."
python3 -m pip install --upgrade pip || handle_error "Failed to upgrade pip"

# Install Python dependencies with error handling
echo "Installing Python packages..."
python3 -m pip install --no-cache-dir \
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
    pydantic==2.6.4 || handle_error "Failed to install Python packages"

# Set up environment variables for development
echo "Setting up environment variables..."
cat > /tmp/dev_env.sh << 'EOF' || handle_error "Failed to create environment file"
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
source /tmp/dev_env.sh || handle_error "Failed to source environment variables"

# Make environment available for future sessions
echo "source /tmp/dev_env.sh" >> ~/.bashrc || handle_error "Failed to update .bashrc"

echo "Setup complete! Environment variables have been configured."
echo "You can start your Flask app with: flask run --host=0.0.0.0 --port=6513"
echo ""
echo "Note: You'll need to start PostgreSQL and Redis services separately."
echo "PostgreSQL should be configured to listen on port 5464 with the credentials above."
