{
  description = "Dev shell with Flyway, Python, PostgreSQL (TCP/IP focus)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        pgSettings = {
          user = "postgres";
          password = "devpassword";
          port = "5433";
          dbName = "toxindex";
          host = "localhost";
          # Define a local socket directory
          socketDirSubPath = "socket"; # Relative to $PWD/.postgres
        };

        python-with-deps = pkgs.python3.withPackages (ps: with ps; [
          flask
          python-dotenv
          stripe
          requests
          urllib3
          flask-login
          flask-wtf
          sendgrid
          gunicorn
          psycopg2
          email-validator
          boto3
          openai
          celery
          redis
          flask-socketio
          gevent
          gevent-websocket
          pandas
          annotated-types
          (ps.buildPythonPackage {
            pname   = "pydantic-core";
            version = "2.16.3";
            format  = "wheel";
            src = pkgs.fetchurl {
              url = "https://files.pythonhosted.org/packages/18/0e/1e39cfbffa57e92ab9f1f0869b32ead8a48ab11e4a373421d625f25fcb26/pydantic_core-2.16.3-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl";
              sha256 = "prG7CCf1ZlS0Q3lVVV3Dru6+3cR8LX7VdUd/CCYixJ4=";
            };
          })
          (ps.buildPythonPackage rec {
            pname   = "pydantic";
            version = "2.6.4";
            format  = "wheel";
            src = pkgs.fetchurl {
              url    = "https://files.pythonhosted.org/packages/e5/f3/8296f550276194a58c5500d55b19a27ae0a5a3a51ffef66710c58544b32d/pydantic-2.6.4-py3-none-any.whl";
              sha256 = "zEb86GYHWAhnvcM2GtRiurnCIu8ELT2oby+zM+HZFsU=";
            };
          })
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pkgs.flyway
            python-with-deps
            pkgs.postgresql_15
            pkgs.postgresql_jdbc
            pkgs.redis
            pkgs.awscli2
            pkgs.python310Packages.pip
            pkgs.gcc
          ];

          shellHook = ''source scripts/flake/shellhook.sh'';
        };

        apps.flask = flake-utils.lib.mkApp {
          drv = pkgs.writeShellScriptBin "flask-dev" ''
            #!${pkgs.bash}/bin/bash
            set -euo pipefail 

            export FLASK_APP=webserver.app
            export FLASK_ENV=development
            export DEBUG=1 
            export PREFERRED_URL_SCHEME=http
            export SERVER_NAME="${pgSettings.host}:6513" 

            export DB_HOST="${pgSettings.host}" # Connect via TCP
            export DB_PORT="${pgSettings.port}"
            export DB_NAME="${pgSettings.dbName}"
            export DB_USER="${pgSettings.user}"
            export DB_PASSWORD="${pgSettings.password}"

            echo "Starting Flask development server on http://${pgSettings.host}:6513..."
            exec flask run --host=0.0.0.0 --port=6513
          '';
        };
      });
}