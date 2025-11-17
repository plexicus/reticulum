# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2025-11-17

### Added
- **Enhanced documentation**: Added comprehensive release and testing guidance to CLAUDE.md
- **Improved version management**: Updated version-bump command to default to minor releases

### Changed
- **Documentation cleanup**: Updated README.md, scripts/README.md, CLAUDE.md, and DEVELOPER.md to remove legacy terminology
- **Script consolidation**: Finalized transition from 6 scripts to 3 streamlined scripts with shared library

### Removed
- **Legacy functionality**: Removed legacy command aliases and deprecated functionality
  - Removed legacy Makefile aliases: `quick-check`, `pre-release`, `version-sync`, `version-bump-patch`, `version-bump-minor`, `version-bump-major`
  - Removed legacy `main()` function from `src/reticulum/main.py`
  - Updated all documentation to reflect current command structure

### Notes
- This release completes the script consolidation and legacy removal process
- All functionality preserved through new command structure: `dev-check`, `dev-check-fix`, `release-sync`, `release-patch`, `release-minor`, `release-major`