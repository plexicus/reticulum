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

# Legacy aliases for compatibility
quick-check: dev-check ## Alias for dev-check (legacy compatibility)

pre-release: dev-check release-sync ## Legacy pre-release workflow

version-sync: release-sync ## Alias for release-sync (legacy compatibility)

version-bump-patch: release-patch ## Alias for release-patch (legacy compatibility)

version-bump-minor: release-minor ## Alias for release-minor (legacy compatibility)

version-bump-major: release-major ## Alias for release-major (legacy compatibility)

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
