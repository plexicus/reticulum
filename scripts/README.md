# Quality Check Scripts

This directory contains scripts to help maintain code quality and prepare for releases.

## Scripts Overview

### 1. `quick-check.sh` - Quick Quality Check
**Purpose**: Daily development quality checks without interactive prompts.

**What it does**:
- ✅ Installs dependencies
- 🔍 Runs ruff linting with auto-fix
- 🎨 Checks and applies black formatting
- 🧪 Runs all tests
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
- 🔄 Interactive prompts for fixes
- 📝 Auto-commit of formatting/linting fixes
- 🚫 Checks for TODO/FIXME comments
- 🌐 Verifies remote sync status
- 📋 Provides release guidance

**Usage**:
```bash
# Run directly
./scripts/pre-release-check.sh

# Or via Makefile
make pre-release
```

**When to use**: Before creating a git tag, before releases.

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
make quick-check  # Quick quality check
make pre-release  # Full pre-release verification
make release      # Quick-check + pre-release
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
# Full pre-release verification
make pre-release

# If all passes, create tag
git tag v0.x.x
git push origin v0.x.x
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

1. **Run quick-check daily** before committing
2. **Use pre-release before tags** to catch issues early
3. **Fix issues immediately** when found
4. **Keep dependencies updated** with `poetry update`
5. **Review auto-fixes** before committing

---

## Integration with CI/CD

These scripts mirror the checks run in GitHub Actions:
- Linting with ruff
- Formatting with black
- Testing with pytest
- Quality gates

Running locally ensures CI passes when you push.
