# Makefile for Reticulum project
# Provides convenient targets for development and release

.PHONY: help install test lint format check quick-check pre-release version-sync clean

# Default target
help:
	@echo "Reticulum - Makefile Help"
	@echo "========================="
	@echo ""
	@echo "Development targets:"
	@echo "  install      - Install dependencies with Poetry"
	@echo "  test         - Run tests with pytest"
	@echo "  lint         - Run ruff linting with auto-fix"
	@echo "  format       - Format code with black"
	@echo "  check        - Run all quality checks (lint + format + test)"
	@echo ""
	@echo "Release targets:"
	@echo "  quick-check  - Quick quality check (non-interactive)"
	@echo "  pre-release  - Full pre-release verification (interactive)"
	@echo "  version-sync - Check version consistency"
	@echo ""
	@echo "Utility targets:"
	@echo "  clean        - Clean up temporary files"
	@echo "  help         - Show this help message"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	poetry install --no-interaction

# Run tests
test:
	@echo "🧪 Running tests..."
	poetry run pytest -v

# Run linting with auto-fix
lint:
	@echo "🔍 Running ruff linting with auto-fix..."
	poetry run ruff check src/ --fix

# Format code
format:
	@echo "🎨 Formatting code with black..."
	poetry run black src/

# Run all quality checks
check: lint format test
	@echo "✅ All quality checks completed!"

# Quick quality check (non-interactive)
quick-check:
	@echo "🚀 Running quick quality check..."
	./scripts/quick-check.sh

# Full pre-release verification (interactive)
pre-release:
	@echo "🚀 Running full pre-release check..."
	./scripts/pre-release-check.sh

# Check version consistency
version-sync:
	@echo "🔄 Checking version consistency..."
	./scripts/version-sync.sh

# Clean up temporary files
clean:
	@echo "🧹 Cleaning up temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -delete 2>/dev/null || true
	@echo "✅ Cleanup completed!"

# Development workflow: install + check
dev: install check
	@echo "🚀 Development environment ready!"

# Release workflow: quick-check + pre-release
release: quick-check pre-release
	@echo "🎉 Ready for release!"
