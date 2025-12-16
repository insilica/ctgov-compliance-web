{
  description = "Dev shell with Flyway, Python, PostgreSQL (TCP/IP focus)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      with import nixpkgs { inherit system; }; {
        devShells.default = mkShell {

          # pgSettings = {
          #   user = "postgres";
          #   password = "devpassword";
          #   port = "5464";
          #   dbName = "ctgov-web";
          #   host = "localhost";
          #   # Define a local socket directory
          #   socketDirSubPath = "socket"; # Relative to $PWD/.postgres
          # };

          buildInputs = [
            flyway
            postgresql_15
            postgresql_jdbc
            uv
            nodejs_20
          ];

          shellHook = ''
            # Set environment variables to skip interactive components
            # export SKIP_FLYWAY_SETUP=true

            source scripts/flake/shellhook.sh

            echo "uv run flask run -p 3030 --debug"
          '';
        };
      });
}
