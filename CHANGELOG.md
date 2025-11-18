## v0.6.9 (2025-11-18)

### Feat

- enhance test repository setup and developer experience

## v0.6.8 (2025-11-18)

### Fix

- prevent double-commit in release script when Commitizen already committed changes

## v0.6.7 (2025-11-18)

### Fix

- regenerate CHANGELOG using Commitizen for standardization

## v0.6.6 (2025-11-18)

## v0.6.5 (2025-11-18)

### Feat

- integrate Commitizen for automated version management and CHANGELOG generation

## v0.6.4 (2025-11-18)

### Feat

- update README with enhanced description and official logo

### Fix

- restore complete CHANGELOG history after version bump
- restore proper CHANGELOG structure with [Unreleased] on single line
- update CHANGELOG structure for release process
- remove duplicate [Unreleased] section in CHANGELOG
- restore version 0.6.3 and maintain CHANGELOG structure

## v0.6.3 (2025-11-18)

### Fix

- remove color codes from output system to prevent git commit failures
- update version synchronization system

## v0.6.2 (2025-11-18)

### Fix

- replace hard Poetry dependency with flexible Python environment detection
- synchronize version files to v0.6.1 across all project files
- update version-bump command to use release script for complete automation

## v0.6.1 (2025-11-18)

### Fix

- bump version to 0.6.1 with CHANGELOG updates
- improve CHANGELOG restructuring logic in version-bump command
- improve CHANGELOG restructuring logic in version-bump command

## v0.6.0 (2025-11-18)

### Feat

- bump version to 0.6.0 with CHANGELOG updates
- enhance /version-bump command with CHANGELOG management
- add intelligent commit-push command with CHANGELOG automation
- implement environment-agnostic testing infrastructure
- add comprehensive /testing slash command
- add integrated security scanner and custom slash command

### Fix

- correct CHANGELOG.md version from 1.0.0 to 0.6.0
- correct CLI argument parsing in test
- make security scanner tests CI-friendly

### Refactor

- improve code quality and test reliability
- remove unused mermaid_builder.py

## v0.5.3 (2025-11-02)

## v0.5.2 (2025-11-02)

### Fix

- remove unused exception variables to pass linting
- improve Dockerfile detection and dependency analysis
- remove advanced-test-repo from git tracking

## v0.5.1 (2025-11-02)

### Fix

- sync all version files to v0.5.1
- manually set version to 0.5.1 as requested
- update release notes with correct CLI usage examples
- add pytest-cov dependency for coverage support

## v0.5.0 (2025-11-02)

### Feat

- add dynamic test repository generation

### Fix

- improve CLI version extraction with awk
- resolve GitHub Actions failures and version synchronization issues

## v0.4.6 (2025-11-02)

### Feat

- replace Mermaid with Graphviz DOT diagram generation
- add comprehensive advanced test repository with 10 Helm charts

## v0.4.5 (2025-08-21)

### Feat

- implement unified script system

### Fix

- prevent stdout contamination in sync_all_versions
- correct array handling in sync functions

### Refactor

- complete script unification with 62% code reduction

## v0.4.3 (2025-08-21)

### Fix

- sync all version files to v0.4.3
- revert to token-based PyPI publishing

## v0.4.2 (2025-08-21)

### Fix

- sync all version files to v0.4.2
- resolve GitHub Actions warnings and enable Trusted Publishing

## v0.4.1 (2025-08-21)

### Feat

- enhance version synchronization system with automated cross-platform consistency
- implement enhanced exposes and depends_on fields for comprehensive service analysis

### Fix

- ensure releases are marked as latest and not draft
- update GitHub Actions to use modern release action
- sync all version files to v0.4.1
- sync all version files to v4.1.2
- ensure console output uses same data source as JSON output
- correct all critical bugs in reticulum scanner - restore environment-specific analysis and exposure detection logic

### Refactor

- clean up scripts and change version to 0.4.1

## v0.3.2 (2025-08-20)

### Feat

- make scripts fully unattended and intelligent - no more user prompts

## v0.3.1 (2025-08-20)

### Feat

- improve JSON output formatting - always pretty formatted like jq (v0.3.1)

## v0.3.0 (2025-08-20)

### Feat

- bump version to 0.3.0 - major quality assurance system release
- enhance scripts with strict quality gates - tests MUST pass before release

## v0.2.3 (2025-08-20)

### Feat

- add version-sync target to Makefile for version consistency checks
- add version synchronization script to prevent version mismatches

### Fix

- update version to 0.2.3 to match git tag v0.2.3

## v0.2.2 (2025-08-20)

### Feat

- add quality check scripts and Makefile for proactive release management

### Fix

- sync version to 0.2.2 in pyproject.toml and __init__.py

## v0.2.1 (2025-08-20)

### Fix

- container naming includes environment for non-base environments

## v0.2.0 (2025-08-20)

### Feat

- implement intelligent exposure analyzer with regex patterns and consolidation

### Fix

- improve file discovery to properly detect values.yaml files

## v0.1.0 (2025-08-20)

### Feat

- add PyPI publishing configuration and GitHub Actions

### Fix

- resolve linting and formatting issues
- install project in CI to make tests work
## [Unreleased]

### Added
- **Added**: New file: `assets/images/reticulum-logo.png`\n

