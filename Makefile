# Makefile for Reticulum project
# Provides convenient targets for development and release

.PHONY: help check test lint format clean quick-check pre-release version-sync release-strict advanced-tests test-all dev-setup ci-test ci-lint ci-format-check

help: ## Show this help message
	@echo "Reticulum - Development and Release Management"
	@echo "=============================================="
	@echo ""
	@echo "Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

check: lint format test ## Run all quality checks (lint, format, test)

test: ## Run the test suite
	@echo "🧪 Running tests..."
	poetry run pytest tests/ -v

lint: ## Run linting checks
	@echo "🔍 Running linting checks..."
	poetry run ruff check src/ --fix
	@echo "✅ Linting completed"

format: ## Format code with black
	@echo "🎨 Formatting code..."
	poetry run black src/
	@echo "✅ Code formatting completed"

clean: ## Clean up generated files
	@echo "🧹 Cleaning up..."
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf test-results/
	@echo "✅ Cleanup completed"

quick-check: ## Quick quality check for daily development
	@echo "⚡ Running quick quality check..."
	@scripts/quick-check.sh

pre-release: ## Comprehensive pre-release quality check
	@echo "🚀 Running pre-release quality check..."
	@scripts/pre-release-check.sh

version-sync: ## Verify and sync version numbers across all files
	@echo "🔄 Running version synchronization..."
	@scripts/version-sync.sh

version-bump-patch: ## Bump patch version (x.y.Z) and sync all files
	@echo "📈 Bumping patch version..."
	@scripts/version-bump.sh patch

version-bump-minor: ## Bump minor version (x.Y.z) and sync all files
	@echo "📈 Bumping minor version..."
	@scripts/version-bump.sh minor

version-bump-major: ## Bump major version (X.y.z) and sync all files
	@echo "📈 Bumping major version..."
	@scripts/version-bump.sh major

release-strict: ## Strict release preparation (check + version-sync)
	@echo "🎯 Running strict release preparation..."
	@make check
	@make version-sync

advanced-tests: ## Run advanced test scenarios against complex repository
	@echo "🔬 Running advanced test scenarios..."
	@scripts/run-advanced-tests.sh

test-all: test advanced-tests ## Run all tests including advanced scenarios
	@echo "🎉 All tests completed!"

# Development helpers
dev-setup: ## Set up development environment
	@echo "🔧 Setting up development environment..."
	poetry install
	@echo "✅ Development environment ready"

# CI/CD helpers
ci-test: ## Run tests for CI environment
	@echo "🔄 Running CI tests..."
	poetry run pytest tests/ --junitxml=test-results.xml

ci-lint: ## Run linting for CI environment
	@echo "🔄 Running CI linting..."
	poetry run ruff check src/

ci-format-check: ## Check code formatting for CI
	@echo "🔄 Checking code formatting..."
	poetry run black --check src/
