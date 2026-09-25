{
  description = "Valheim Mod Version Check - Discord bot + REST API";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python311;

        runtimeDeps = [ python pkgs.uv pkgs.ilspycmd ];

        runApp = pkgs.writeShellApplication {
          name = "valheim-mod-version-check";
          runtimeInputs = runtimeDeps;
          text = ''
            export UV_PYTHON="${python}/bin/python3.11"
            export UV_PYTHON_DOWNLOADS=never
            uv sync --frozen
            exec uv run --no-sync python app.py
          '';
        };
      in
      {
        packages.default = runApp;

        apps.default = {
          type = "app";
          program = "${runApp}/bin/valheim-mod-version-check";
        };

        devShells.default = pkgs.mkShell {
          packages = runtimeDeps;

          UV_PYTHON = "${python}/bin/python3.11";
          UV_PYTHON_DOWNLOADS = "never";

          shellHook = ''
            echo "Run 'uv sync' then 'uv run python app.py' (or 'nix run') to start the bot."
          '';
        };
      });
}
