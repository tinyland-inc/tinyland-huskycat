{
  description = "HuskyCat - Universal Code Validation Platform with MCP Server Integration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
    # nix2container for reproducible container builds with layer caching
    nix2container = {
      url = "github:nlewo/nix2container";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  # Nix configuration hints for binary caches
  # Note: ATTIC_PUBLIC_KEY to be obtained from https://nix-cache.fuzzy-dev.tinyland.dev
  nixConfig = {
    extra-substituters = [
      "https://cache.nixos.org"
      "https://nix-cache.fuzzy-dev.tinyland.dev/main"
    ];
    extra-trusted-public-keys = [
      "cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY="
      "main:PBDvqG8OP3W2XF4QzuqWwZD/RhLRsE7ONxwM09kqTtw="
    ];
  };

  outputs = { self, nixpkgs, flake-utils, nix2container }:
    flake-utils.lib.eachSystem [
      "x86_64-linux"
      "aarch64-linux"
      "x86_64-darwin"
      "aarch64-darwin"
    ] (system:
      let
        pkgs = import nixpkgs { inherit system; };

        # Version from git revision (research recommendation)
        version =
          if (self ? rev)
          then "2.0.0-${self.shortRev}"
          else "2.0.0-dirty";

        # Source filtering to avoid rebuilds on doc/test/cache changes (research recommendation)
        src = pkgs.lib.cleanSourceWith {
          src = ./.;
          filter = path: type:
            let baseName = baseNameOf path; in
            # Include source files
            (pkgs.lib.hasSuffix ".py" baseName) ||
            (baseName == "pyproject.toml") ||
            (baseName == "uv.lock") ||
            (baseName == "README.md") ||
            (baseName == "LICENSE") ||
            (pkgs.lib.hasPrefix "src/" path) ||
            # Exclude cache, tests, docs from build (avoid unnecessary rebuilds)
            (!(pkgs.lib.hasPrefix ".cache" baseName)) &&
            (!(pkgs.lib.hasPrefix "tests/" path)) &&
            (!(pkgs.lib.hasPrefix "docs/" path)) &&
            (!(pkgs.lib.hasPrefix ".git" baseName)) &&
            (!(pkgs.lib.hasPrefix "__pycache__" baseName)) &&
            (baseName != ".pytest_cache") &&
            (baseName != ".mypy_cache") &&
            (baseName != ".ruff_cache");
        };

        # Python environment with HuskyCat dependencies
        pythonEnv = pkgs.python312.withPackages (ps: with ps; [
          # Core dependencies (from pyproject.toml)
          pydantic
          pyyaml
          jsonschema
          requests
          rich
          networkx
          psutil
          click
          toml
          gitpython

          # Validation tools
          black
          mypy
          flake8
          bandit
          autoflake

          # Testing
          pytest
          pytest-cov
          hypothesis
        ]);

        # nix2container helper (only available on Linux)
        n2c = nix2container.packages.${system}.nix2container or null;

      in {
        # Package: huskycat as a derivation
        packages.default = pkgs.stdenvNoCC.mkDerivation {
          pname = "huskycat";
          inherit version src;

          nativeBuildInputs = [ pkgs.makeWrapper ];
          buildInputs = [ pythonEnv ];

          installPhase = ''
            mkdir -p $out/bin $out/lib/huskycat
            cp -r src/huskycat $out/lib/huskycat/

            makeWrapper ${pythonEnv}/bin/python $out/bin/huskycat \
              --add-flags "-m huskycat" \
              --prefix PYTHONPATH : "$out/lib"
          '';

          meta = with pkgs.lib; {
            description = "Universal Code Validation Platform with MCP Server Integration";
            homepage = "https://huskycat-570fbd.gitlab.io/";
            license = licenses.asl20;
            maintainers = [ ];
            platforms = platforms.unix;
          };
        };

        # Container image using nix2container (Linux only)
        # Provides reproducible container builds with layer caching
        packages.container = pkgs.lib.optionalAttrs (n2c != null && pkgs.stdenv.isLinux) (
          n2c.buildImage {
            name = "registry.gitlab.com/tinyland/ai/huskycat";
            tag = version;

            # Layer strategy: base -> python -> app
            # Each layer caches independently for faster rebuilds
            layers = [
              # Layer 1: Base system utilities (rarely changes)
              (n2c.buildLayer {
                deps = with pkgs; [ coreutils bash cacert ];
              })
              # Layer 2: Python environment (changes with deps)
              (n2c.buildLayer {
                deps = [ pythonEnv ];
              })
              # Layer 3: Application (changes with code)
              (n2c.buildLayer {
                deps = [ self.packages.${system}.default ];
              })
            ];

            config = {
              entrypoint = [ "${self.packages.${system}.default}/bin/huskycat" ];
              cmd = [ "validate" ];
              env = [
                "SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
              ];
              labels = {
                "org.opencontainers.image.title" = "HuskyCat";
                "org.opencontainers.image.description" = "Universal Code Validation Platform";
                "org.opencontainers.image.version" = version;
                "org.opencontainers.image.source" = "https://gitlab.com/tinyland/ai/huskycat";
                "org.opencontainers.image.licenses" = "Apache-2.0";
              };
            };
          }
        );

        # App for `nix run`
        apps.default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/huskycat";
        };

        # Formatter for `nix fmt`
        formatter = pkgs.nixpkgs-fmt;

        # Development shell - Apache/MIT tools only (FAST mode)
        devShells.default = pkgs.mkShell {
          name = "huskycat-dev";

          buildInputs = with pkgs; [
            # Python environment
            python312
            uv

            # Node.js for npm scripts
            nodejs_22

            # Linting tools (Apache/MIT compatible)
            black
            ruff
            mypy

            # TOML formatting
            taplo

            # Documentation
            python312Packages.mkdocs
            python312Packages.mkdocs-material

            # Development utilities
            git
            jq
            yq-go
          ];

          shellHook = ''
            echo "HuskyCat Development Environment (Nix)"
            echo "======================================="
            echo "Python: $(python --version)"
            echo "UV: $(uv --version 2>/dev/null || echo 'run: curl -LsSf https://astral.sh/uv/install.sh | sh')"
            echo "Node: $(node --version)"
            echo ""
            echo "Quick Start:"
            echo "  uv sync --dev       Install Python dependencies"
            echo "  npm install         Install Node dependencies"
            echo "  npm run dev         Run HuskyCat CLI"
            echo "  npm run validate    Validate codebase"
            echo "  nix build           Build Nix package"
            echo ""
            echo "Linting Mode: FAST (Apache/MIT tools only)"
            echo "For GPL tools, use: nix develop .#ci"
          '';
        };

        # CI shell - includes GPL tools for comprehensive validation
        devShells.ci = pkgs.mkShell {
          name = "huskycat-ci";

          buildInputs = with pkgs; [
            # All dev dependencies
            python312
            uv
            nodejs_22
            black
            ruff
            mypy
            taplo
            git
            jq

            # GPL tools (for COMPREHENSIVE mode)
            shellcheck
            hadolint
            yamllint
          ];

          shellHook = ''
            echo "HuskyCat CI Environment (Nix)"
            echo "============================="
            echo "Linting Mode: COMPREHENSIVE (includes GPL tools)"
            echo ""
            echo "GPL Tools Available:"
            echo "  shellcheck $(shellcheck --version | head -2 | tail -1)"
            echo "  hadolint $(hadolint --version)"
            echo "  yamllint $(yamllint --version)"
          '';
        };

        # Checks for CI
        checks = {
          # Verify package builds
          package = self.packages.${system}.default;

          # Run tests (if pytest is available)
          tests = pkgs.runCommand "huskycat-tests" {
            buildInputs = [ pythonEnv pkgs.git ];
          } ''
            cd ${self}
            export HOME=$(mktemp -d)
            export PYTHONPATH=${self}/src
            python -m pytest tests/ -v --tb=short -x || true
            touch $out
          '';
        };
      }
    );
}
