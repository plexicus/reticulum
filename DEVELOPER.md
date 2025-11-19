# Reticulum Developer Guide

This guide provides comprehensive instructions for developers working on the Reticulum project, including development workflows, version management, and release processes.

## Quick Start

### Initial Setup

**Install uv:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Set up development environment:**
```bash
# Clone repository
git clone https://github.com/plexicus/reticulum.git
cd reticulum

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

```

### Daily Development Workflow

**Always activate the virtual environment first:**
```bash
source .venv/bin/activate
```

**Then run development commands:**
```bash
# Run development quality checks (recommended before commits)
make dev-check

# Run tests only
make test

# Run all tests including advanced scenarios
make test-all

# Auto-fix linting and formatting issues
make dev-check-fix
```

## Development Commands

### Quality Assurance

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `make dev-check` | Development quality check | **Daily use**, before commits |
| `make dev-check-fix` | Auto-fix quality issues | When linting/formatting fails |
| `make check` | Full quality check (lint + format + test) | Before releases |
| `make test` | Run test suite | Feature development |
| `make advanced-tests` | Run complex test scenarios | Testing edge cases |
| `make test-all` | Run all tests | Comprehensive testing |

### Code Quality

```bash
# Lint code
make lint

# Format code
make format

# Clean generated files
make clean
```

## Version Management

### Understanding Version Numbers

Reticulum uses [Semantic Versioning](https://semver.org/):
- **MAJOR** (X.0.0): Breaking API changes
- **MINOR** (0.X.0): New features (backward compatible)
- **PATCH** (0.0.X): Bug fixes (backward compatible)

### Release Workflow

#### 1. Patch Release (Bug Fixes)

```bash
# For bug fixes, security patches, minor improvements
make release-patch
```

**When to use:**
- Fixing bugs in existing functionality
- Security vulnerability patches
- Documentation improvements
- Minor performance optimizations

#### 2. Minor Release (New Features)

```bash
# For new features, enhancements (backward compatible)
make release-minor
```

**When to use:**
- Adding new features
- Significant performance improvements
- Major documentation updates
- Dependency updates with new functionality

#### 3. Major Release (Breaking Changes)

```bash
# For breaking API changes
make release-major
```

**When to use:**
- Breaking API changes
- Major architectural changes
- Dropping support for deprecated features

### Version Synchronization

```bash
# Manually synchronize version files if needed
make release-sync
```

**Use when:**
- Version files get out of sync
- Manual version changes were made
- Release process reports synchronization issues

## Release Process

### Pre-Release Checklist

1. **Ensure clean working directory**
   ```bash
   git status  # Should show no uncommitted changes
   ```

2. **Run comprehensive quality checks**
   ```bash
   make check  # Must pass all checks
   ```

3. **Verify tests pass**
   ```bash
   make test-all  # All tests should pass
   ```

4. **Check version synchronization**
   ```bash
   make release-sync  # Fix any synchronization issues
   ```

### Automated Release Steps

The release script (`scripts/release.sh`) performs:

1. **Environment validation** - Checks for clean working directory
2. **Quality checks** - Runs linting, formatting, and tests
3. **Version bump** - Updates version in all files
4. **File synchronization** - Ensures all version files match
5. **Commit and tag** - Creates version commit and git tag
6. **Validation** - Final checks before completion

### Manual Release (When Automated Fails)

If the automated release fails, you can manually:

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Bump version with commitizen
python -m commitizen bump --increment PATCH

# 3. Create and push tag
git tag v0.5.1
git push origin v0.5.1
```


## Development Best Practices

### Commit Message Convention

Use conventional commit messages:

```
feat: add dynamic test repository generation
fix: resolve GitHub Actions pytest coverage failure
docs: update release notes with correct CLI usage
chore: bump version to v0.5.1
```

### Testing Strategy

- **Unit Tests**: `tests/test_exposure_scanner.py` - Core functionality
- **Advanced Tests**: `tests/test_advanced_scenarios.py` - Complex scenarios
- **Test Markers**: Use appropriate markers (`slow`, `integration`, `advanced`)

### Test Repository Setup

The advanced test scenarios use a static test repository that is committed to version control:

```bash
# The test repository is available at: tests/advanced-test-repo/
# It contains:
# - Multiple Helm charts with different exposure levels
# - Dockerfiles for various services
# - Sample source code files
# - NetworkPolicy templates for testing network security analysis
```

**Note**: The `tests/advanced-test-repo/` directory is now committed as static test data and should be available automatically.

### Code Quality Standards

- **Linting**: Ruff for code quality
- **Formatting**: Black for consistent style
- **Testing**: pytest with coverage
- **Documentation**: Keep docstrings and comments updated

## Troubleshooting

### Common Issues

#### Release Fails Due to Dirty Working Directory

```bash
# Check for uncommitted changes
git status

# Commit or stash changes
git add . && git commit -m "chore: prepare for release"
# OR
git stash
```

#### Version Files Out of Sync

```bash
# Synchronize all version files
make release-sync

# Verify synchronization
grep -r "__version__" src/
```

#### GitHub Actions Fail Due to Missing Dependencies

```bash
# Check if all dependencies are in pyproject.toml
# Common missing dependencies:
# - pytest-cov for coverage
# - Additional test dependencies

# Add missing dependencies
uv pip install pytest-cov
```

#### Tests Fail After Changes

```bash
# Run specific failing test
make test

# Run with detailed output
pytest -xvs  # Stop on first failure, verbose, no capture

# Check coverage
pytest --cov=src/reticulum --cov-report=html
```

#### Advanced Tests Skipped Due to Missing Test Repository

If advanced tests are skipped with "Advanced test repository not found":

```bash
# Run advanced tests
make advanced-tests

# Or run all tests
make test-all
```

**Note**: The test repository is now committed as static test data and should be available automatically.

#### Environment Detection Issues

If environment detection fails:

```bash
# Check current environment
make help

# Force specific environment
PYTHON_RUN="python -m" make test  # Use system Python
PYTHON_RUN=".venv/bin/python -m" make test  # Use virtual environment

# Install missing dependencies
make dev-setup  # Uses uv to install dependencies
```

### Debugging Release Script

If the release script fails:

```bash
# Run with debug output
bash -x scripts/release.sh minor

# Check individual steps manually
make dev-check
python -m commitizen bump --increment MINOR
make release-sync
```

## File Structure Reference

### Key Files for Version Management

- `pyproject.toml` - Primary version source
- `src/reticulum/__init__.py` - Python package version
- `src/reticulum/cli.py` - CLI version display
- `README.md` - Documentation version references

### Development Scripts

- `scripts/release.sh` - Automated release management
- `scripts/dev-check.sh` - Development quality checks
- `scripts/run-advanced-tests.sh` - Advanced test scenarios
- `tests/advanced-test-repo/` - Static test repository (committed to version control)

## CI/CD Pipeline

### GitHub Actions Workflows

- **Test**: Multi-python version testing on push/PR
- **Publish**: Package build and PyPI deployment on tag push
- **Advanced Tests**: Complex scenario testing

### Release Automation

When you push a version tag (e.g., `v0.5.1`):
1. Tests run across all supported Python versions
2. Package is built and published to PyPI
3. GitHub release is created with auto-generated notes

## Getting Help

- Check this DEVELOPER.md first
- Review existing issues on GitHub
- Check GitHub Actions logs for specific errors
- Ensure all dependencies are properly installed

---

**Remember**: Always run `make dev-check` before committing changes and `make check` before creating releases.