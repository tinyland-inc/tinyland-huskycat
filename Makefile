# HuskyCat - Universal Code Validation Platform
# Clean, professional Makefile following factory pattern

.DEFAULT_GOAL := help
SHELL := /bin/bash
PYTHON := python3
UV := uv
PROJECT_NAME := huskycat
VERSION := 2.0.0

# Directories
SRC_DIR := src
TESTS_DIR := tests
DOCS_DIR := docs
BUILD_DIR := build
DIST_DIR := dist
CACHE_DIR := ~/.cache/huskycats

# Colors
RESET := \\033[0m
BOLD := \\033[1m
GREEN := \\033[32m
YELLOW := \\033[33m
BLUE := \\033[34m

##@ General

.PHONY: help
help: ## Display this help message
	@echo -e "$(BOLD)$(BLUE)HuskyCat Build System v$(VERSION)$(RESET)"
	@echo -e "$(BOLD)==============================$(RESET)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf ""} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-18s$(RESET) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BOLD)%s$(RESET)\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Development

.PHONY: install
install: ## Install HuskyCat and dependencies using uv
	@echo -e "$(BOLD)Installing HuskyCat...$(RESET)"
	@command -v uv >/dev/null 2>&1 || (echo "Installing uv..." && curl -LsSf https://astral.sh/uv/install.sh | sh)
	@uv pip install -e .
	@uv pip install -e .[dev]
	@./huskycat install --dev
	@echo -e "$(GREEN)✓ Installation complete$(RESET)"

.PHONY: dev
dev: ## Setup development environment
	@echo -e "$(BOLD)Setting up development environment...$(RESET)"
	@uv venv
	@uv pip install -e .[dev]
	@./huskycat setup-hooks
	@./huskycat update-schemas
	@echo -e "$(GREEN)✓ Development environment ready$(RESET)"

.PHONY: run
run: ## Run HuskyCat CLI
	@./huskycat $(ARGS)

##@ Validation

.PHONY: validate
validate: ## Validate all files in repository
	@echo -e "$(BOLD)Running validation...$(RESET)"
	@./huskycat validate --all

.PHONY: validate-staged
validate-staged: ## Validate only staged files
	@./huskycat validate --staged

.PHONY: ci-validate
ci-validate: ## Validate CI/CD configuration
	@./huskycat ci-validate

.PHONY: auto-devops
auto-devops: ## Validate Auto-DevOps Helm charts and K8s manifests
	@./huskycat auto-devops --simulate

##@ Testing

.PHONY: test
test: ## Run all tests with pytest
	@echo -e "$(BOLD)Running tests...$(RESET)"
	@$(PYTHON) -m pytest $(TESTS_DIR) -v

.PHONY: test-pbt
test-pbt: ## Run property-based tests with hypothesis
	@$(PYTHON) -m pytest $(TESTS_DIR) -v -k pbt

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	@$(PYTHON) -m pytest $(TESTS_DIR) --cov=$(SRC_DIR) --cov-report=html --cov-report=term

.PHONY: test-watch
test-watch: ## Run tests in watch mode
	@$(PYTHON) -m pytest $(TESTS_DIR) -v --watch

##@ Quality

.PHONY: lint
lint: ## Run linters (black, flake8, mypy, ruff)
	@echo -e "$(BOLD)Running linters...$(RESET)"
	@black --check $(SRC_DIR) $(TESTS_DIR)
	@flake8 $(SRC_DIR) $(TESTS_DIR)
	@mypy $(SRC_DIR)
	@ruff check $(SRC_DIR) $(TESTS_DIR)

.PHONY: format
format: ## Format code with black and ruff
	@echo -e "$(BOLD)Formatting code...$(RESET)"
	@black $(SRC_DIR) $(TESTS_DIR)
	@ruff check --fix $(SRC_DIR) $(TESTS_DIR)

.PHONY: typecheck
typecheck: ## Run type checking with mypy
	@mypy $(SRC_DIR) --strict

##@ Documentation

.PHONY: docs
docs: ## Build documentation with mkdocs
	@echo -e "$(BOLD)Building documentation...$(RESET)"
	@mkdocs build

.PHONY: docs-serve
docs-serve: ## Serve documentation locally
	@mkdocs serve

.PHONY: docs-deploy
docs-deploy: ## Deploy docs to GitLab Pages
	@mkdocs gh-deploy --force

##@ Building

.PHONY: build
build: ## Build binary with PyInstaller
	@echo -e "$(BOLD)Building binary...$(RESET)"
	@mkdir -p $(DIST_DIR)
	@pyinstaller --onefile --name=$(PROJECT_NAME) \
		--add-data="$(SRC_DIR):$(SRC_DIR)" \
		--hidden-import=pydantic \
		--hidden-import=jsonschema \
		--hidden-import=requests \
		$(SRC_DIR)/__main__.py
	@echo -e "$(GREEN)✓ Binary built: $(DIST_DIR)/$(PROJECT_NAME)$(RESET)"

.PHONY: container
container: ## Build container with podman
	@echo -e "$(BOLD)Building container...$(RESET)"
	@podman build -f ContainerFile -t $(PROJECT_NAME):$(VERSION) .
	@podman build -f ContainerFile.dev -t $(PROJECT_NAME):dev .

##@ Cleanup

.PHONY: clean
clean: ## Remove all build artifacts and cache
	@echo -e "$(BOLD)Cleaning up...$(RESET)"
	@rm -rf $(BUILD_DIR) $(DIST_DIR) *.egg-info
	@rm -rf .pytest_cache .mypy_cache .ruff_cache .hypothesis
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo -e "$(GREEN)✓ Cleanup complete$(RESET)"

.PHONY: clean-all
clean-all: clean ## Remove everything including schemas cache
	@rm -rf $(CACHE_DIR)
	@rm -rf ~/.huskycat
	@echo -e "$(GREEN)✓ Deep cleanup complete$(RESET)"

##@ GitLab CI/CD

.PHONY: ci-lint
ci-lint: ## Lint GitLab CI configuration
	@./huskycat ci-validate .gitlab-ci.yml

.PHONY: ci-local
ci-local: ## Run GitLab CI locally with gitlab-runner
	@gitlab-runner exec docker validate

##@ MCP Server

.PHONY: mcp-server
mcp-server: ## Start MCP server for Claude integration
	@./huskycat mcp-server --port=0

.PHONY: mcp-test
mcp-test: ## Test MCP server connection
	@$(PYTHON) $(SRC_DIR)/mcp_server.py --test

##@ Status

.PHONY: status
status: ## Show HuskyCat status
	@./huskycat status

.PHONY: version
version: ## Display version information
	@echo -e "$(BOLD)HuskyCat v$(VERSION)$(RESET)"
	@$(PYTHON) --version
	@uv --version 2>/dev/null || echo "uv: not installed"