{
  description = "Dev shell with Flyway, Python, PostgreSQL (TCP/IP focus)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
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
            pkgs.postgresql_jdbc
            pkgs.redis
            pkgs.awscli2
            pkgs.jdk8
            pkgs.locale
            pkgs.glibcLocales
            pkgs.zlib
            pkgs.stdenv.cc.cc.lib
            pkgs.uv
          ];

          shellHook = ''
            # Set locale
            export LANG="en_US.UTF-8"

            # Set environment variables to skip interactive components
            export SKIP_AWS_SECRET_LOADING=true
            export SKIP_REDIS_SETUP=true  # Skip Redis since it's not used
            export SKIP_BLAZEGRAPH_SETUP=true  # Skip Blazegraph since it's not used
            export CI=false  # Keep services running but skip some setup

            source scripts/flake/shellhook.sh

            echo "uv run flask run --host 0.0.0.0 --port 6525"
          '';
        };
      });
}
