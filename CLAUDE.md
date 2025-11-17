# CLAUDE.md

This file provides Claude Code (claude.ai/code) with specific guidance for working with this repository.

## Primary Documentation Sources

**ALWAYS consult these files in order:**
1. **DEVELOPER.md** - Complete development workflows, version management, release processes
2. **README.md** - User-facing documentation and usage
3. **This file (CLAUDE.md)** - Claude-specific guidance only

## Claude-Specific Guidelines

### Documentation Priority
- **Development workflows**: Use `DEVELOPER.md` exclusively
- **Release management**: Use `DEVELOPER.md` for all version bump decisions and processes
- **Troubleshooting**: Use `DEVELOPER.md` for common issues and solutions

### Critical Reminders for Claude

1. **Version Management**:
   - Always check `DEVELOPER.md` before any version changes
   - Follow semantic versioning guidelines strictly
   - Use exact version numbers as requested by user

2. **Release Process**:
   - Never assume version bump type - ask user or check `DEVELOPER.md`
   - Always run quality checks (`make check`)
   - Verify version synchronization after releases

3. **Development Workflow**:
   - Use `make dev-check` before committing changes
   - Run `make test-all` before releases
   - Follow commit message conventions from `DEVELOPER.md`

4. **Error Handling**:
   - Check `DEVELOPER.md` troubleshooting section first
   - Look for common GitHub Actions failures and solutions
   - Verify dependencies are properly declared

### Common Pitfalls to Avoid

- **Version confusion**: Always confirm exact version numbers with user
- **Redundant documentation**: Don't duplicate information from `DEVELOPER.md`
- **Missing dependencies**: Ensure all test/CI dependencies are in `pyproject.toml`
- **Unsynced versions**: Use `make release-sync` when version files get out of sync

## Quick Reference

### Essential Commands (Detailed in DEVELOPER.md)
- `make dev-check` - Development quality checks
- `make test-all` - All tests including advanced scenarios
- `make check` - Full quality checks (lint + format + test)
- `make release-sync` - Fix version synchronization issues

### When to Ask for Clarification
- Version bump type (patch/minor/major)
- Release timing and strategy
- Complex architectural decisions
- Any uncertainty about development workflow

## Creating a New Release

This section provides Claude-specific guidance for creating releases in Reticulum. The repository uses an automated release management system with semantic versioning.

### Release Decision Framework

**Default Release Strategy**:
- **Minor releases** (x.Y.z) - Default for new features and enhancements
- **Patch releases** (x.y.Z) - Bug fixes and minor changes only
- **Major releases** (X.y.z) - Breaking changes (requires explicit user request)

**When to use each release type**:
- **Minor**: New features, backward-compatible API changes, significant enhancements
- **Patch**: Bug fixes, documentation updates, minor improvements
- **Major**: Breaking API changes, major architectural shifts

**Claude Protocol**: Default to minor releases unless user specifically requests patch or major.

### Pre-Release Preparation Checklist

**Before creating any release, ALWAYS verify**:
1. **Clean working directory**: `git status` must show no uncommitted changes
2. **Main branch**: You must be on the `main` branch
3. **Quality checks pass**: `make check` (lint + format + test)
4. **All tests pass**: `make test-all` (including advanced scenarios)
5. **Version synchronization**: `make release-sync` if versions are mismatched

### Release Execution Commands

**Use these Makefile commands for releases**:
```bash
# Patch release (bug fixes: 0.4.3 → 0.4.4)
make release-patch

# Minor release (new features: 0.4.3 → 0.5.0) - DEFAULT
make release-minor

# Major release (breaking changes: 0.4.3 → 1.0.0)
make release-major
```

**What happens during release creation**:
1. Environment validation (branch, git status)
2. Quality checks (linting, formatting, tests)
3. Version calculation based on semantic versioning
4. Update `pyproject.toml` and synchronize all version files
5. Git commit with intelligent commit message
6. Git tag creation (`vX.Y.Z`)
7. Final validation and success summary

### Post-Release Steps

**After successful release creation**:
```bash
# Push both the commit and tag to trigger CI/CD
git push origin main vX.Y.Z
```

**GitHub Actions will automatically**:
- Run comprehensive tests across Python versions
- Build the package with Poetry
- Publish to PyPI
- Create GitHub Release with changelog

### Version Synchronization

**Use when version files get out of sync**:
```bash
make release-sync
```

**Files managed by version synchronization**:
- `pyproject.toml` (source of truth)
- `src/reticulum/__init__.py`
- `src/reticulum/cli.py`
- `README.md`

### Claude-Specific Release Protocol

**Safety Checks**:
- Always confirm release type with user unless explicitly specified
- Never proceed if quality checks fail
- Verify working directory is clean before starting
- Check for critical TODO/FIXME comments that block releases

**When to Ask**:
- Release type is ambiguous or not specified
- Working directory has uncommitted changes
- Quality checks fail
- Version files are out of sync

**Success Verification**:
- All version files synchronized
- Git tag created successfully
- Working directory remains clean
- Release summary displayed with next steps

## Testing in Reticulum

This section provides Claude-specific guidance for testing in Reticulum. The project has a comprehensive testing framework with multiple test types and execution methods.

### Testing Philosophy & Organization

**Test Hierarchy**:
- **Basic Tests**: Component-level validation in `tests/test_exposure_scanner.py`, `tests/test_security_scanner.py`
- **Advanced Tests**: Complex scenario testing in `tests/test_advanced_scenarios.py`, `tests/test_security_scanner_advanced.py`

**Test Categories**:
- **Unit Tests**: Individual component validation
- **Integration Tests**: Component interaction testing
- **Advanced Scenarios**: Complex real-world configurations
- **Performance Benchmarks**: Scan time and resource usage validation

### Test Execution Commands

**Use this decision tree for choosing test commands**:

```bash
# Quick development testing (recommended for daily use)
make dev-check

# Basic test suite only
make test

# Advanced integration scenarios
make advanced-tests

# Complete test suite (basic + advanced)
make test-all

# Coverage reporting
make test  # Uses detected environment for pytest
```

**Environment-Agnostic Testing**: All commands now work with Poetry, virtualenv, uv, or system Python. The Makefile automatically detects your environment.

**When to use each command**:
- **`make dev-check`**: Daily development, pre-commit validation
- **`make test`**: Quick verification, basic functionality
- **`make advanced-tests`**: Complex scenario validation, performance testing
- **`make test-all`**: Pre-release validation, comprehensive testing

### Advanced Testing System

**Advanced Test Repository**:
- Dynamically generated test repository with 10+ Helm charts
- Various exposure levels (HIGH, MEDIUM, LOW)
- Complex network topologies and edge cases
- Generated via: `poetry run python scripts/create-test-repo.py`

**Advanced Test Script (`scripts/run-advanced-tests.sh`)**:
- Validates test repository structure
- Runs exposure analysis on multiple configurations
- Tests network topology analysis
- Performs performance benchmarks (< 30s scan time)
- Generates detailed test logs and summaries

**Test Results**:
- Results stored in `test-results/` directory
- Timestamped logs for each test run
- Performance metrics and validation reports

### Test Categories & Markers

**Pytest Markers for Specific Test Categories**:
```bash
# Run specific test categories
make test  # Uses detected environment for pytest with markers

# Example with specific markers
$(python -m) pytest tests/test_advanced_scenarios.py -m advanced
$(python -m) pytest tests/test_advanced_scenarios.py -m performance
$(python -m) pytest tests/test_advanced_scenarios.py -m edge_cases
$(python -m) pytest tests/test_advanced_scenarios.py -m integration
$(python -m) pytest tests/test_advanced_scenarios.py -m slow
```

**Marker Definitions**:
- **`advanced`**: Complex integration scenarios
- **`performance`**: Performance benchmarks and timing tests
- **`edge_cases`**: Boundary conditions and error handling
- **`integration`**: Component interaction testing
- **`slow`**: Long-running tests (use sparingly)

### CI/CD Testing Integration

**GitHub Actions Testing**:
- **Main Pipeline**: Tests on Python 3.9, 3.10, 3.11, 3.12
- **Advanced Testing Pipeline**: Dedicated complex scenario testing
- **Automated Quality Checks**: Linting, formatting, dependency validation

**CI Testing Steps**:
1. Generate test repository
2. Run pytest test suite
3. Execute linting checks (ruff)
4. Validate code formatting (black)
5. Run advanced test scenarios
6. Generate coverage reports

### Development Workflow Integration

**Daily Development Testing**:
```bash
# Quick quality check (includes tests)
make dev-check

# Auto-fix issues and test
make dev-check-fix

# Full test suite before commits
make test-all
```

**Pre-Release Testing Requirements**:
- All basic tests must pass (`make test`)
- All advanced tests must pass (`make advanced-tests`)
- Performance benchmarks must meet requirements (< 30s scan time)
- No critical TODO/FIXME comments blocking release

**Troubleshooting Failed Tests**:
1. Check test logs in `test-results/` directory
2. Verify test repository exists and is valid
3. Check for dependency issues (`make dev-setup` or install with detected environment)
4. Look for specific error messages in pytest output
5. Run individual test files to isolate issues
6. Verify environment detection (`make help` shows current environment)

### Claude-Specific Testing Protocol

**Safety Checks Before Testing**:
- Ensure dependencies are installed (`make dev-setup` or use detected environment)
- Verify test repository exists (`tests/advanced-test-repo/`)
- Check for clean working directory
- Confirm you're in the project root directory
- Verify environment detection (`make help`)

**When to Ask for Clarification**:
- Test failures that are unclear or complex
- Performance benchmark failures
- Advanced test repository generation issues
- CI/CD test failures that need investigation

**Success Verification**:
- All tests pass without errors
- Performance benchmarks meet requirements
- Test logs show successful execution
- Coverage reports generated (if requested)

**Testing Decision Protocol**:
- **Daily Development**: Use `make dev-check`
- **Feature Validation**: Use `make test-all`
- **Performance Testing**: Use `make advanced-tests`
- **Pre-Release**: Use `make test-all` and verify all requirements

---

**Remember**: `DEVELOPER.md` contains all comprehensive development documentation. This file is for Claude-specific guidance only.