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
            pkgs.python310Packages.pip
            pkgs.gcc
            pkgs.jdk8
          ];

          shellHook = ''
            if [ ! -d .venv ]; then
              uv venv
              source .venv/bin/activate
              uv sync >/dev/null 2>&1
            else 
              source .venv/bin/activate
            fi

            source scripts/flake/shellhook.sh

            # populate mock data
            uv run scripts/init_mock_data.py >/dev/null 2>&1
            uv run -- flask run --host 0.0.0.0 --port 6525 --debug --extra-files "web/templates/*.html"
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
