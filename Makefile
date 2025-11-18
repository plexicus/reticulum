# Makefile for Reticulum project
# Provides convenient targets for development and release
# Supports multiple environment managers: Poetry (preferred), pip+virtualenv, uv

.PHONY: help check test lint format clean release-strict advanced-tests test-all dev-setup ci-test ci-lint ci-format-check

# Environment detection
PYTHON_RUN := $(shell if command -v poetry >/dev/null 2>&1; then echo "poetry run"; elif [ -d ".venv" ]; then echo ".venv/bin/python -m"; else echo "python -m"; fi)
PYTHON_EXEC := $(shell if command -v poetry >/dev/null 2>&1; then echo "poetry run python"; elif [ -d ".venv" ]; then echo ".venv/bin/python"; else echo "python"; fi)

help: ## Show this help message
	@echo "Reticulum - Development and Release Management"
	@echo "=============================================="
	@echo ""
	@echo "Environment: $(PYTHON_RUN)"
	@echo ""
	@echo "Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

check: lint format test ## Run all quality checks (lint, format, test)

test: ## Run the test suite
	@echo "🧪 Running tests..."
	$(PYTHON_RUN) pytest tests/ -v

lint: ## Run linting checks
	@echo "🔍 Running linting checks..."
	$(PYTHON_RUN) ruff check src/ --fix
	@echo "✅ Linting completed"

format: ## Format code with black
	@echo "🎨 Formatting code..."
	$(PYTHON_RUN) black src/
	@echo "✅ Code formatting completed"

clean: ## Clean up generated files
	@echo "🧹 Cleaning up..."
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf test-results/
	@echo "✅ Cleanup completed"

dev-check: ## Development quality check (daily use)
	@echo "🔍 Running development quality check..."
	@scripts/dev-check.sh

dev-check-fix: ## Development quality check with auto-fix
	@echo "🔍 Running development quality check with auto-fix..."
	@scripts/dev-check.sh --fix

release-patch: ## Create patch release (x.y.Z)
	@echo "📈 Creating patch release..."
	@scripts/release.sh patch

release-minor: ## Create minor release (x.Y.z)
	@echo "📈 Creating minor release..."
	@scripts/release.sh minor

release-major: ## Create major release (X.y.z)
	@echo "📈 Creating major release..."
	@scripts/release.sh major

release-sync: ## Synchronize version files only
	@echo "🔄 Synchronizing version files..."
	@scripts/release.sh sync


advanced-tests: ## Run advanced test scenarios against complex repository
	@echo "🔬 Running advanced test scenarios..."
	@scripts/run-advanced-tests.sh

test-all: ## Run all tests including advanced scenarios
	@echo "🧪 Running all tests..."
	@$(PYTHON_RUN) pytest tests/ -v
	@echo "🔬 Running advanced test scenarios..."
	@scripts/run-advanced-tests.sh
	@echo "🎉 All tests completed!"

# Development helpers
dev-setup: ## Set up development environment
	@echo "🔧 Setting up development environment..."
	@if command -v poetry >/dev/null 2>&1; then \
		poetry install; \
		@echo "✅ Development environment ready (Poetry)"; \
	elif command -v uv >/dev/null 2>&1; then \
		uv pip install -e .; \
		@echo "✅ Development environment ready (uv)"; \
	else \
		python -m venv .venv && .venv/bin/python -m pip install -e .; \
		@echo "✅ Development environment ready (pip+virtualenv)"; \
	fi
	@echo "🔧 Generating advanced test repository..."
	@$(PYTHON_EXEC) scripts/create-test-repo.py
	@echo "✅ Advanced test repository generated"

# CI/CD helpers
ci-test: ## Run tests for CI environment
	@echo "🔄 Running CI tests..."
	$(PYTHON_RUN) pytest tests/ --junitxml=test-results.xml

ci-lint: ## Run linting for CI environment
	@echo "🔄 Running CI linting..."
	$(PYTHON_RUN) ruff check src/

ci-format-check: ## Check code formatting for CI
	@echo "🔄 Checking code formatting..."
	$(PYTHON_RUN) black --check src/
