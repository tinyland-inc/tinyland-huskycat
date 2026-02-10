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
    {
      # Home-manager module for declarative HuskyCat configuration
      homeManagerModules.default = import ./nix/modules/huskycat.nix;
      homeManagerModules.huskycat = self.homeManagerModules.default;

      # Nixpkgs overlay for easy integration
      overlays.default = final: prev: {
        huskycat = self.packages.${prev.system}.default;
      };
    } //
    flake-utils.lib.eachSystem [
      "x86_64-linux"
      "aarch64-linux"
      "x86_64-darwin"
      "aarch64-darwin"
    ] (system:
      let
        pkgs = import nixpkgs { inherit system; };

        # Version from git revision
        version =
          if (self ? rev)
          then "2.1.0-${self.shortRev}"
          else "2.1.0-dirty";

        # Source filtering to avoid rebuilds on doc/test/cache changes
        filteredSrc = pkgs.lib.cleanSourceWith {
          src = ./.;
          filter = path: type:
            let baseName = baseNameOf path; in
            (pkgs.lib.hasSuffix ".py" baseName) ||
            (baseName == "pyproject.toml") ||
            (baseName == "uv.lock") ||
            (baseName == "README.md") ||
            (baseName == "LICENSE") ||
            (type == "directory");
        };

        # Package derivation (extracted to nix/package.nix for monorepo composability)
        huskycatPkg = pkgs.callPackage ./nix/package.nix {
          inherit version;
          src = filteredSrc;
        };

        # Re-export the python environment for devShells and checks
        pythonEnv = huskycatPkg.passthru.pythonEnv;

        # nix2container helper (only available on Linux)
        n2c = nix2container.packages.${system}.nix2container or null;

      in {
        # Package: huskycat (derivation defined in nix/package.nix)
        packages.default = huskycatPkg;

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

            # Node.js (legacy npm scripts)
            nodejs_22

            # Task runner (replaces npm scripts)
            just

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
            echo "Just: $(just --version 2>/dev/null || echo 'not found')"
            echo ""
            echo "Quick Start:"
            echo "  uv sync --dev       Install Python dependencies"
            echo "  just validate       Validate codebase"
            echo "  just test           Run tests"
            echo "  just build-binary   Build binary"
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

          # Run tests (skip container/e2e tests that need Docker/network)
          tests = pkgs.runCommand "huskycat-tests" {
            buildInputs = [ pythonEnv pkgs.git ];
          } ''
            cd ${self}
            export HOME=$(mktemp -d)
            export PYTHONPATH=${self}/src
            # Initialize a minimal git config for tests that need it
            git config --global user.email "test@test.com"
            git config --global user.name "Test"
            python -m pytest tests/ -v --tb=short -x \
              --timeout=60 \
              --ignore=tests/test_container_comprehensive.py \
              --ignore=tests/e2e/ \
              -k "not test_container and not test_docker"
            touch $out
          '';
        };
      }
    );
}
