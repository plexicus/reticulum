# Quality Check & Version Management Scripts

This directory contains scripts to help maintain code quality, manage versions, and prepare for releases.

## Scripts Overview

### 1. `quick-check.sh` - Quick Quality Check
**Purpose**: Daily development quality checks without interactive prompts.

**What it does**:
- ✅ Installs dependencies
- 🔍 Runs ruff linting with auto-fix
- 🎨 Checks and applies black formatting
- 🧪 Runs all tests
- 🔄 Quick version synchronization check
- 📊 Shows current git status

**Usage**:
```bash
# Run directly
./scripts/quick-check.sh

# Or via Makefile
make quick-check
```

**When to use**: Before committing code, during development, daily checks.

---

### 2. `pre-release-check.sh` - Full Pre-Release Verification
**Purpose**: Comprehensive verification before creating a release tag.

**What it does**:
- ✅ All quick-check features
- 🔄 Enhanced version synchronization across all files
- 📝 Auto-commit of formatting/linting fixes
- 🚫 Checks for TODO/FIXME comments
- 🌐 Verifies remote sync status
- 📋 Comprehensive release readiness assessment

**Usage**:
```bash
# Run directly
./scripts/pre-release-check.sh

# Or via Makefile
make pre-release
```

**When to use**: Before creating a git tag, before releases.

---

### 3. `version-sync.sh` - Version Synchronization
**Purpose**: Ensures version consistency across project files.

**What it does**:
- 🔍 Validates versions in pyproject.toml, __init__.py, cli.py, README.md
- 🔄 Auto-synchronizes mismatched versions
- 📝 Intelligent commit of version fixes
- 🏷️ Git tag validation
- 🧪 Quality check integration
- 📊 Release readiness assessment

**Supported Files**:
- `pyproject.toml` (source of truth)
- `src/reticulum/__init__.py` (Python package)
- `src/reticulum/cli.py` (CLI version display)
- `README.md` (documentation)

**Usage**:
```bash
# Run directly
./scripts/version-sync.sh

# Or via Makefile
make version-sync
```

**When to use**: Before releases, after version changes, daily integration.

---

### 4. `version-bump.sh` - Version Bumping
**Purpose**: Semantic version bumping with synchronization.

**What it does**:
- 📈 Increments version (patch/minor/major)
- 🔄 Auto-syncs ALL version files
- 📝 Creates intelligent commit message
- 🏷️ Creates git tag automatically
- 📋 Provides push instructions

**Usage**:
```bash
# Bump patch version (4.1.2 → 4.1.3)
./scripts/version-bump.sh patch

# Bump minor version (4.1.2 → 4.2.0)
./scripts/version-bump.sh minor

# Bump major version (4.1.2 → 5.0.0)  
./scripts/version-bump.sh major

# Or via Makefile
make version-bump-patch
make version-bump-minor
make version-bump-major
```

**When to use**: For creating new releases with automatic version management.

---

## Makefile Targets

The project includes a `Makefile` with convenient targets:

### Development Targets
```bash
make install      # Install dependencies
make test         # Run tests only
make lint         # Run linting only
make format       # Format code only
make check        # Run all quality checks
make dev          # Install + check (development setup)
```

### Release Targets
```bash
make quick-check     # Quick quality check
make pre-release     # Full pre-release verification  
make version-sync    # Version synchronization
make release-strict  # Comprehensive release preparation
```

### Version Management Targets
```bash
make version-sync        # Sync all version files
make version-bump-patch  # Bump patch version (x.y.Z)
make version-bump-minor  # Bump minor version (x.Y.z)
make version-bump-major  # Bump major version (X.y.z)
```

### Utility Targets
```bash
make clean        # Clean temporary files
make help         # Show help message
```

---

## Workflow Examples

### Daily Development
```bash
# Quick check before committing
make quick-check

# If all passes, commit your changes
git add .
git commit -m "feat: add new feature"
```

### Before Release
```bash
# Method 1: Manual version management
make pre-release              # Full verification + version sync
git tag v0.x.x               # Create tag manually
git push origin main v0.x.x  # Push changes and tag

# Method 2: Automated version bumping (RECOMMENDED)
make version-bump-patch       # Automatic patch bump + sync + tag
git push origin main v0.x.x  # Push everything

# Method 3: Full control
make version-sync            # Sync versions first
make pre-release             # Then full verification
```

### Fix Issues Found
```bash
# If linting issues found, they're auto-fixed
# If formatting issues found, they're auto-fixed
# If tests fail, fix the code and run again

# After fixes, run quick check
make quick-check
```

---

## Requirements

- **Poetry**: For dependency management
- **Git**: For version control
- **Bash**: For script execution
- **Python 3.9+**: For running the project

---

## Troubleshooting

### Script Permission Issues
```bash
chmod +x scripts/*.sh
```

### Poetry Not Found
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Or via pip
pip install poetry
```

### Tests Failing
1. Check the test output for specific failures
2. Fix the code issues
3. Run `make test` again
4. Ensure all tests pass before proceeding

### Linting Issues
1. Run `make lint` to auto-fix issues
2. Review any remaining issues manually
3. Fix remaining issues
4. Run `make lint` again to verify

---

## Best Practices

1. **Run quick-check daily** before committing (includes version sync check)
2. **Use automated version bumping** for releases (`make version-bump-patch`)
3. **Let version-sync handle consistency** across all files automatically
4. **Use pre-release for final verification** before important releases  
5. **Fix issues immediately** when found
6. **Keep dependencies updated** with `poetry update`
7. **Review auto-fixes** before committing
8. **Trust the automation** - the enhanced scripts handle cross-platform consistency

### Version Management
- Use semantic versioning: patch for bug fixes, minor for features, major for breaking changes
- pyproject.toml is the source of truth - other files sync automatically
- Run version-sync if you manually edit any version
- Use version-bump scripts for releases

---

## Integration with CI/CD

These scripts provide local testing that mirrors GitHub Actions:
- **Quality Checks**: Linting with ruff, formatting with black, testing with pytest
- **Version Management**: Cross-platform version consistency validation  
- **Release Automation**: Automated tagging and release preparation
- **Platform Consistency**: Ensures Python, CLI, and documentation versions align

**Benefits**:
- ✅ **Zero CI failures** - catch issues before pushing
- 🚀 **Faster releases** - automated version management  
- 🔄 **Perfect consistency** - all platforms stay synchronized
- 📦 **Release confidence** - comprehensive pre-flight checks

Running locally ensures CI passes and consistent releases.
