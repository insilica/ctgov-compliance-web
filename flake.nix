{
  description = "Dev shell with Flyway, Python, PostgreSQL (TCP/IP focus)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        pgSettings = {
          user = "postgres";
          password = "devpassword";
          port = "5464";
          dbName = "ctgov-web";
          host = "localhost";
          # Define a local socket directory
          socketDirSubPath = "socket"; # Relative to $PWD/.postgres
        };
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pkgs.flyway
            pkgs.postgresql_15
            pkgs.uv
            pkgs.postgresql_jdbc
            pkgs.redis
            pkgs.awscli2
            pkgs.jdk8
            pkgs.locale
            pkgs.glibcLocales
            pkgs.zlib
            pkgs.stdenv.cc.cc.lib
          ];

          shellHook = ''
            # Set locale
            export LANG="en_US.UTF-8"
            export LC_ALL="en_US.UTF-8"
            
            # Set library path for system libraries
            export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [
              pkgs.stdenv.cc.cc.lib
              pkgs.zlib
            ]}:$LD_LIBRARY_PATH"

            # Set environment variables to skip interactive components
            export SKIP_AWS_SECRET_LOADING=true
            export SKIP_REDIS_SETUP=true  # Skip Redis since it's not used
            export SKIP_BLAZEGRAPH_SETUP=true  # Skip Blazegraph since it's not used
            export CI=false  # Keep services running but skip some setup

            # Setup virtual environment
            if [ ! -d .venv ]; then
              uv venv
            fi
            
            # Always activate the virtual environment
            source .venv/bin/activate
            
            # Sync dependencies (handle potential TOML errors gracefully)
            echo "Syncing Python dependencies..."
            if ! uv sync --no-dev 2>/dev/null; then
              echo "Warning: uv sync failed, trying to install from pyproject.toml..."
              uv pip install -e . || echo "Warning: Failed to install project in editable mode"
            fi

            # Source the shellhook script with error handling
            if [ -f scripts/flake/shellhook.sh ]; then
              source scripts/flake/shellhook.sh || echo "Warning: shellhook.sh completed with errors (this is expected in non-interactive mode)"
            fi

            export FLASK_APP=web.app
            export FLASK_ENV=development
            export FLASK_DEBUG=1

            WEB_DIR="$(pwd)/web"
            
            echo ""
            echo "=== Development Environment Ready ==="
            echo "Flask app: $FLASK_APP"
            echo "Python virtual environment: $(which python)"
            echo "To start the Flask server: flask run --host 0.0.0.0 --port 6525"
            echo "======================================="
          '';
        };

        # apps.flask = flake-utils.lib.mkApp {
        #   drv = pkgs.writeShellScriptBin "flask-dev" ''
        #     #!${pkgs.bash}/bin/bash
        #     set -euo pipefail 

        #     export FLASK_APP=web.app
        #     export FLASK_ENV=development
        #     export DEBUG=1 
        #     export PREFERRED_URL_SCHEME=http
        #     export SERVER_NAME="${pgSettings.host}:6513" 

        #     export DB_HOST="${pgSettings.host}" # Connect via TCP
        #     export DB_PORT="${pgSettings.port}"
        #     export DB_NAME="${pgSettings.dbName}"
        #     export DB_USER="${pgSettings.user}"
        #     export DB_PASSWORD="${pgSettings.password}"

        #     echo "Starting Flask development server on http://${pgSettings.host}:6513..."
        #     exec flask run --host=0.0.0.0 --port=6513
        #   '';
        # };
      });
}
