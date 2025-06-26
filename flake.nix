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

            if [ ! -d .venv ]; then
              uv venv
              source .venv/bin/activate
            else 
              source .venv/bin/activate
            fi

            uv sync

            source scripts/flake/shellhook.sh

            export FLASK_APP=web.app
            export FLASK_ENV=development
            export FLASK_DEBUG=1

            WEB_DIR="$(pwd)/web"
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
