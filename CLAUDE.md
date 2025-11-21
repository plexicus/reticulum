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
- **Premature CHANGELOG updates**: Never modify CHANGELOG.md outside of release process

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

### Commit Best Practices
- **Use Commitizen for commits**: Use `cz commit` for conventional commit format with automatic CHANGELOG generation
- **Use `/commit-push` command**: For simple commit creation and pushing (no CHANGELOG updates)
- **English only**: All commit messages and CHANGELOG entries must be in English
- **Descriptive messages**: Use clear, descriptive commit messages that explain the "why"
- **Interactive mode**: Use `/commit-push` without arguments for guided commit creation

### Commitizen Integration

Reticulum now uses **Commitizen** for automated version management and CHANGELOG generation:

**Key Benefits**:
- **Automatic CHANGELOG generation**: Based on conventional commit messages
- **Semantic versioning**: Automatic version bumps based on commit types
- **Version synchronization**: Updates all version files automatically
- **Resilient CHANGELOG management**: Built-in recovery mechanisms

**Commitizen Commands**:
```bash
# Create conventional commit
cz commit

# Check commit format compliance
cz check --rev-range HEAD~10..HEAD

# Bump version (used internally by release script)
cz bump --yes --changelog --increment patch|minor|major
```

**Release Workflow**:
1. Make changes with conventional commits (`cz commit`)
2. Run quality checks (`make check`)
3. Use release commands (`make release-patch|minor|major`)
4. Commitizen handles version bumping and CHANGELOG updates automatically

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
3. **Commitizen version bump**: Automatic version calculation and CHANGELOG updates
4. **Version synchronization**: All version files updated automatically
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
- Build the package with standard Python build tools
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

**CHANGELOG.md management**:
- **Development phase**: Use conventional commits (`cz commit`) for automatic CHANGELOG updates
- **Release process**: Commitizen automatically moves `[Unreleased]` changes to new version section
- **Resilient system**: Built-in recovery mechanisms for CHANGELOG corruption
- **Never modify manually**: Always use conventional commits for CHANGELOG updates

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

**Use the `/testing` command for comprehensive testing** instead of this documentation. The testing command provides:

- Interactive test category selection
- Detailed result summaries and performance metrics
- Auto-fix capabilities for code quality issues
- Comprehensive test result archiving

**Quick Reference**:
- `/testing` - Interactive testing with category selection
- `/testing quick` - Quick development quality checks
- `/testing advanced` - Advanced integration scenarios
- `/testing complete` - Full test suite (basic + advanced)
- `/testing --fix` - Auto-fix mode for code quality issues

For detailed testing workflows, development commands, and troubleshooting, refer to `DEVELOPER.md`.

---

##  **CRITICAL**: 

- `DEVELOPER.md` contains all comprehensive development documentation. This file is for Claude-specific guidance only.
- Use always the .venv/bin/python generated by `make dev-setup`
- All temporal tests and analysis data must be created in `/tmp/`
