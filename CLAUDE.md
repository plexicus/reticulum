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
   - Always run pre-release checks (`make check`)
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

---

**Remember**: `DEVELOPER.md` contains all comprehensive development documentation. This file is for Claude-specific guidance only.