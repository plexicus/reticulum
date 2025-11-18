# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2025-11-18

### Added
- **Environment-agnostic testing**: Automatic detection of Python environments (Poetry → venv → uv → system Python)
- **Standard requirements files**: Created `requirements.txt` and `requirements-dev.txt` for pip-based installation
- **Comprehensive testing command**: Added interactive `/testing` slash command with multiple test categories
- **Enhanced documentation**: Updated DEVELOPER.md with multiple environment manager support
- **Enhanced documentation**: Added comprehensive release and testing guidance to CLAUDE.md
- **Improved version management**: Updated version-bump command to default to minor releases
- **Intelligent commit automation**: Added `/commit-push` command with automatic CHANGELOG updates and English validation
- **NetworkPolicy analysis**: Added comprehensive Kubernetes NetworkPolicy analysis to detect internet egress capabilities
- **Security risk assessment**: Enhanced security risk assessment with egress risk multipliers
- **Test coverage**: Added 11 comprehensive test methods for NetworkPolicy analysis functionality
- **File discovery**: Implemented glob pattern-based file discovery with duplicate prevention
- **Multi-document YAML support**: Added support for parsing multi-document Kubernetes manifests
- **Risk scoring algorithm**: Implemented risk scoring for egress capabilities (HIGH/MEDIUM/LOW)
- **Integration**: Seamlessly integrated NetworkPolicy analysis with existing Reticulum security scanning workflow

### Changed
- **Environment detection**: Updated Makefile and all scripts to use detected environment instead of hard-coded Poetry
- **Code quality improvements**: Fixed linting issues, formatting, and bare except clauses
- **Documentation simplification**: Removed redundant testing details from CLAUDE.md, now references `/testing` command
- **Project cleanup**: Removed unnecessary `.devcontainer` directory (Reticulum uses Docker for security scanning, not development)

## [Unreleased]

