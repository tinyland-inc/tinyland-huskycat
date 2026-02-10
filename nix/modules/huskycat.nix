{ config, lib, pkgs, ... }:

let
  cfg = config.tinyland.huskycat;
  huskycatPkg = cfg.package;
  hooksDir = "${config.xdg.configHome}/git/hooks";
in
{
  options.tinyland.huskycat = {
    enable = lib.mkEnableOption "HuskyCat universal code validation platform";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.huskycat or (builtins.throw
        "huskycat not found in pkgs. Add the huskycat overlay or set tinyland.huskycat.package.");
      defaultText = lib.literalExpression "pkgs.huskycat";
      description = "HuskyCat package to use. Defaults to pkgs.huskycat from the overlay.";
    };

    # Global hooks integration
    hooks = {
      preCommit = {
        validation = lib.mkOption {
          type = lib.types.bool;
          default = true;
          description = "Enable pre-commit validation via HuskyCat";
        };
      };

      postCommit = {
        triage = lib.mkOption {
          type = lib.types.bool;
          default = false;
          description = "Enable post-commit auto-triage (non-blocking)";
        };
      };

      prepareCommitMsg = {
        branchPrefix = lib.mkOption {
          type = lib.types.bool;
          default = false;
          description = "Auto-populate commit message from branch name";
        };
      };
    };

    # Auto-discovery configuration
    autoDiscover = {
      enable = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = "Enable automatic discovery and hook installation for git repos";
      };

      directories = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [ "~/git" "~/src" "~/projects" ];
        description = "Directories to scan for git repositories";
      };

      excludeRepos = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [];
        description = "List of repository paths to exclude from auto-discovery";
        example = [ "~/git/vendor-repo" "~/src/third-party" ];
      };

      shellHook = {
        enable = lib.mkOption {
          type = lib.types.bool;
          default = true;
          description = "Enable shell hook that detects new repos on cd";
        };
      };
    };

    # Triage configuration
    triage = {
      enable = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = "Enable auto-triage engine";
      };

      platforms = lib.mkOption {
        type = lib.types.listOf (lib.types.enum [ "gitlab" "github" "codeberg" ]);
        default = [ "gitlab" "github" "codeberg" ];
        description = "Forge platforms to support for triage";
      };

      autoIteration = lib.mkOption {
        type = lib.types.bool;
        default = true;
        description = "Auto-set iteration to current week";
      };

      autoLabel = lib.mkOption {
        type = lib.types.bool;
        default = true;
        description = "Auto-label based on file paths and branch prefix";
      };
    };

    # MCP server registration
    mcp = {
      enable = lib.mkOption {
        type = lib.types.bool;
        default = true;
        description = "Register HuskyCat as MCP server for Claude Code";
      };

      scope = lib.mkOption {
        type = lib.types.enum [ "user" "project" ];
        default = "user";
        description = "MCP registration scope (user = global, project = per-repo)";
      };
    };

    # Linting mode
    lintingMode = lib.mkOption {
      type = lib.types.enum [ "fast" "comprehensive" ];
      default = "fast";
      description = "Linting mode: fast (Apache/MIT tools) or comprehensive (includes GPL)";
    };

    # Default linting mode for newly discovered repos
    defaultLintingMode = lib.mkOption {
      type = lib.types.enum [ "fast" "comprehensive" ];
      default = "fast";
      description = "Default linting mode for newly discovered repositories";
    };
  };

  config = lib.mkIf cfg.enable {
    # Install the HuskyCat package
    home.packages = [ huskycatPkg ];

    # Integration with globalGitHooks dispatcher
    # HuskyCat hooks slot into the existing crush-dots hook dispatcher
    # by registering as extraScript in the appropriate hook phases.
    tinyland.globalGitHooks = lib.mkIf (cfg.hooks.preCommit.validation || cfg.hooks.postCommit.triage) {
      hooks = {
        preCommit = lib.mkIf cfg.hooks.preCommit.validation {
          extraScript = ''
            # HuskyCat pre-commit validation (FAST mode)
            if [ -x "${huskycatPkg}/bin/huskycat" ]; then
              HUSKYCAT_LINTING_MODE="${cfg.lintingMode}" \
                "${huskycatPkg}/bin/huskycat" validate --staged --mode git_hooks || exit 1
            fi
          '';
        };
      };
    };

    # Post-commit triage hook (standalone, non-blocking)
    home.file."${hooksDir}/post-commit-huskycat" = lib.mkIf cfg.hooks.postCommit.triage {
      executable = true;
      text = ''
        #!/usr/bin/env bash
        # HuskyCat post-commit auto-triage (non-blocking)
        # Generated by nix home-manager module

        set -euo pipefail

        [ "''${SKIP_TRIAGE:-0}" = "1" ] && exit 0

        CACHE_DIR="''${XDG_CACHE_HOME:-$HOME/.cache}/huskycat/triage"
        mkdir -p "$CACHE_DIR"

        run_triage() {
          local log_file="$CACHE_DIR/$(date +%Y%m%d).log"
          HUSKYCAT_TRIAGE=1 "${huskycatPkg}/bin/huskycat" triage --post-commit \
            >> "$log_file" 2>&1 || true
        }

        if [ "''${TRIAGE_FOREGROUND:-0}" = "1" ]; then
          run_triage
        else
          run_triage &
          disown 2>/dev/null || true
        fi

        exit 0
      '';
    };

    # Prepare-commit-msg hook for branch prefix injection
    home.file."${hooksDir}/prepare-commit-msg-huskycat" = lib.mkIf cfg.hooks.prepareCommitMsg.branchPrefix {
      executable = true;
      text = ''
        #!/usr/bin/env bash
        # HuskyCat prepare-commit-msg: branch prefix injection
        # Generated by nix home-manager module

        set -euo pipefail

        COMMIT_MSG_FILE="$1"
        COMMIT_SOURCE="''${2:-}"

        # Only for new commits
        case "$COMMIT_SOURCE" in
          merge|squash|commit) exit 0 ;;
        esac

        branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
        [ -z "$branch" ] || [ "$branch" = "HEAD" ] && exit 0

        case "$branch" in
          main|master|dev|develop) exit 0 ;;
        esac

        # Extract type from branch prefix
        commit_type=""
        case "$branch" in
          feat/*|feature/*) commit_type="feat" ;;
          fix/*|bugfix/*|hotfix/*) commit_type="fix" ;;
          docs/*|doc/*) commit_type="docs" ;;
          refactor/*) commit_type="refactor" ;;
          test/*) commit_type="test" ;;
          chore/*) commit_type="chore" ;;
          ci/*) commit_type="ci" ;;
          perf/*) commit_type="perf" ;;
        esac

        # Extract issue number
        issue_num=""
        if [[ "$branch" =~ [/-]([0-9]+)[/-] ]]; then
          issue_num="''${BASH_REMATCH[1]}"
        elif [[ "$branch" =~ /([0-9]+)- ]]; then
          issue_num="''${BASH_REMATCH[1]}"
        fi

        first_line=$(head -1 "$COMMIT_MSG_FILE")
        if [ -n "$first_line" ] && ! echo "$first_line" | grep -q "^#"; then
          if [ -n "$issue_num" ] && ! grep -q "#''${issue_num}" "$COMMIT_MSG_FILE"; then
            echo "" >> "$COMMIT_MSG_FILE"
            echo "Refs #''${issue_num}" >> "$COMMIT_MSG_FILE"
          fi
          exit 0
        fi

        if [ -n "$commit_type" ]; then
          {
            echo "''${commit_type}: "
            echo ""
            [ -n "$issue_num" ] && echo "Refs #''${issue_num}" && echo ""
            cat "$COMMIT_MSG_FILE"
          } > "''${COMMIT_MSG_FILE}.tmp"
          mv "''${COMMIT_MSG_FILE}.tmp" "$COMMIT_MSG_FILE"
        fi

        exit 0
      '';
    };

    # Auto-discovery: activation script that scans directories for git repos
    home.activation.huskycatAutoDiscover = lib.mkIf cfg.autoDiscover.enable (
      lib.hm.dag.entryAfter [ "writeBoundary" ] ''
        # HuskyCat auto-discovery: scan directories for git repos and install hooks
        DISCOVERY_LOG="''${XDG_CACHE_HOME:-$HOME/.cache}/huskycat/discovery.log"
        mkdir -p "$(dirname "$DISCOVERY_LOG")"

        echo "$(date -Iseconds) HuskyCat auto-discovery starting" >> "$DISCOVERY_LOG"

        ${lib.concatMapStringsSep "\n" (dir: ''
          SCAN_DIR="${dir}"
          SCAN_DIR="''${SCAN_DIR/#\~/$HOME}"
          if [ -d "$SCAN_DIR" ]; then
            for repo_dir in $(find "$SCAN_DIR" -maxdepth 3 -name ".git" -type d 2>/dev/null); do
              repo="$(dirname "$repo_dir")"

              # Check opt-out sentinel file
              if [ -f "$repo/.huskycat-disable" ]; then
                echo "$(date -Iseconds) SKIP (opt-out): $repo" >> "$DISCOVERY_LOG"
                continue
              fi

              # Check exclude list
              EXCLUDED=0
              ${lib.concatMapStringsSep "\n" (excl: ''
                EXCL_PATH="${excl}"
                EXCL_PATH="''${EXCL_PATH/#\~/$HOME}"
                if [ "$repo" = "$EXCL_PATH" ]; then
                  EXCLUDED=1
                fi
              '') cfg.autoDiscover.excludeRepos}
              if [ "$EXCLUDED" = "1" ]; then
                echo "$(date -Iseconds) SKIP (excluded): $repo" >> "$DISCOVERY_LOG"
                continue
              fi

              # Install hooks if not already present
              if [ ! -f "$repo/.git/hooks/pre-commit" ] || ! grep -q "huskycat" "$repo/.git/hooks/pre-commit" 2>/dev/null; then
                echo "$(date -Iseconds) ENABLE: $repo" >> "$DISCOVERY_LOG"
                # Write a minimal pre-commit hook
                mkdir -p "$repo/.git/hooks"
                cat > "$repo/.git/hooks/pre-commit" << 'HOOKEOF'
        #!/usr/bin/env bash
        # HuskyCat pre-commit hook (auto-installed by home-manager)
        if command -v huskycat &>/dev/null; then
          HUSKYCAT_LINTING_MODE="${cfg.defaultLintingMode}" \
            huskycat validate --staged --mode git_hooks || exit 1
        fi
        HOOKEOF
                chmod +x "$repo/.git/hooks/pre-commit"
              fi
            done
          fi
        '') cfg.autoDiscover.directories}

        echo "$(date -Iseconds) HuskyCat auto-discovery complete" >> "$DISCOVERY_LOG"
        $VERBOSE_ECHO "HuskyCat auto-discovery complete (see $DISCOVERY_LOG)"
      ''
    );

    # Shell hook for cd-based repo detection
    # Generates a shell function that checks for .git/ when changing directories
    programs.bash.initExtra = lib.mkIf (cfg.autoDiscover.enable && cfg.autoDiscover.shellHook.enable) ''
      # HuskyCat: auto-detect git repos and install hooks on cd
      _huskycat_cd_hook() {
        builtin cd "$@" || return
        if [ -d ".git" ] && [ ! -f ".huskycat-disable" ]; then
          if [ ! -f ".git/hooks/pre-commit" ] || ! grep -q "huskycat" ".git/hooks/pre-commit" 2>/dev/null; then
            if command -v huskycat &>/dev/null; then
              mkdir -p .git/hooks
              cat > .git/hooks/pre-commit << 'HOOKEOF'
      #!/usr/bin/env bash
      # HuskyCat pre-commit hook (auto-installed by shell hook)
      if command -v huskycat &>/dev/null; then
        huskycat validate --staged --mode git_hooks || exit 1
      fi
      HOOKEOF
              chmod +x .git/hooks/pre-commit
              local DISCOVERY_LOG="''${XDG_CACHE_HOME:-$HOME/.cache}/huskycat/discovery.log"
              mkdir -p "$(dirname "$DISCOVERY_LOG")"
              echo "$(date -Iseconds) SHELL-HOOK: $(pwd)" >> "$DISCOVERY_LOG"
            fi
          fi
        fi
      }
      alias cd='_huskycat_cd_hook'
    '';

    programs.zsh.initExtra = lib.mkIf (cfg.autoDiscover.enable && cfg.autoDiscover.shellHook.enable) ''
      # HuskyCat: auto-detect git repos and install hooks on cd
      _huskycat_chpwd_hook() {
        if [ -d ".git" ] && [ ! -f ".huskycat-disable" ]; then
          if [ ! -f ".git/hooks/pre-commit" ] || ! grep -q "huskycat" ".git/hooks/pre-commit" 2>/dev/null; then
            if command -v huskycat &>/dev/null; then
              mkdir -p .git/hooks
              cat > .git/hooks/pre-commit << 'HOOKEOF'
      #!/usr/bin/env bash
      # HuskyCat pre-commit hook (auto-installed by shell hook)
      if command -v huskycat &>/dev/null; then
        huskycat validate --staged --mode git_hooks || exit 1
      fi
      HOOKEOF
              chmod +x .git/hooks/pre-commit
              local DISCOVERY_LOG="''${XDG_CACHE_HOME:-$HOME/.cache}/huskycat/discovery.log"
              mkdir -p "$(dirname "$DISCOVERY_LOG")"
              echo "$(date -Iseconds) SHELL-HOOK: $(pwd)" >> "$DISCOVERY_LOG"
            fi
          fi
        fi
      }
      chpwd_functions+=(_huskycat_chpwd_hook)
    '';

    # MCP server registration for Claude Code
    # Writes to ~/.claude.json mcpServers section
    home.activation.huskycatMcp = lib.mkIf cfg.mcp.enable (
      lib.hm.dag.entryAfter [ "writeBoundary" ] ''
        # Register HuskyCat MCP server with Claude Code
        CLAUDE_CONFIG="$HOME/.claude.json"

        if [ -f "$CLAUDE_CONFIG" ]; then
          ${pkgs.jq}/bin/jq --arg cmd "${huskycatPkg}/bin/huskycat" \
            '.mcpServers.huskycat = {
              "command": $cmd,
              "args": ["mcp-server"],
              "env": {}
            }' "$CLAUDE_CONFIG" > "''${CLAUDE_CONFIG}.tmp" && \
            mv "''${CLAUDE_CONFIG}.tmp" "$CLAUDE_CONFIG"
        else
          cat > "$CLAUDE_CONFIG" << MCPEOF
        {
          "mcpServers": {
            "huskycat": {
              "command": "${huskycatPkg}/bin/huskycat",
              "args": ["mcp-server"],
              "env": {}
            }
          }
        }
        MCPEOF
        fi

        $VERBOSE_ECHO "HuskyCat MCP server registered"
      ''
    );

    # Environment variables for HuskyCat
    home.sessionVariables = {
      HUSKYCAT_LINTING_MODE = cfg.lintingMode;
    } // lib.optionalAttrs cfg.triage.enable {
      HUSKYCAT_TRIAGE_ENABLED = "true";
    };
  };
}
