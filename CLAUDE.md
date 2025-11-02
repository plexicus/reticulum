# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**IMPORTANT**: Always check `DEVELOPER.md` for comprehensive development workflows, version management, release processes, and troubleshooting guides.

## Project Overview

Reticulum is a prioritization report generator that analyzes Kubernetes Helm charts and generates security prioritization reports for external tools. It provides structured prioritization data mapping services to their risk levels, code paths, and Dockerfiles.

## Development Commands

### Setup and Installation
```bash
# Install dependencies
poetry install

# Setup development environment
make dev-setup
```

### Testing
```bash
# Run basic tests
make test

# Run advanced test scenarios
make advanced-tests

# Run all tests including advanced scenarios
make test-all

# Run tests with coverage
poetry run pytest tests/ --cov=src/reticulum --cov-report=html
```

### Quality Assurance
```bash
# Run all quality checks (lint, format, test)
make check

# Development quality check (daily use)
make dev-check

# Development quality check with auto-fix
make dev-check-fix

# Lint code
make lint

# Format code
make format

# Clean up generated files
make clean
```

### Release Management

**See `DEVELOPER.md` for comprehensive release workflows, version bump guidelines, and troubleshooting.**

```bash
# Create patch release (x.y.Z)
make release-patch

# Create minor release (x.Y.z)
make release-minor

# Create major release (X.y.z)
make release-major

# Synchronize version files only
make release-sync
```

## Architecture

### Core Components

**ExposureScanner** (`src/reticulum/main.py:19`) - Main orchestrator class that coordinates the analysis process:
- Scans repositories for Helm charts
- Orchestrates specialized analyzers
- Builds comprehensive results structure

**Specialized Analyzers:**
- **ExposureAnalyzer** (`src/reticulum/exposure_analyzer.py:12`) - Analyzes Helm charts for exposure patterns
- **DependencyAnalyzer** (`src/reticulum/dependency_analyzer.py:12`) - Analyzes dependencies between containers
- **DockerfileAnalyzer** (`src/reticulum/dockerfile_analyzer.py`) - Finds and analyzes Dockerfiles
- **PathConsolidator** (`src/reticulum/path_consolidator.py`) - Consolidates source code paths
- **DOTBuilder** (`src/reticulum/dot_builder.py:10`) - Generates Graphviz DOT diagrams for network topology visualization

### Analysis Workflow

1. **Chart Discovery** - Find all `Chart.yaml` files in repository
2. **Exposure Analysis** - Analyze values.yaml and templates for exposure patterns
3. **Dependency Analysis** - Reconstruct containers from dependencies
4. **Internal Detection** - Identify LOW exposure containers
5. **Dockerfile Enrichment** - Find and analyze Dockerfiles
6. **Path Consolidation** - Build master source code paths
7. **Topology Building** - Generate network topology and DOT diagrams

### Exposure Classification

- **HIGH**: Direct internet access (LoadBalancer, Ingress, NodePort)
- **MEDIUM**: Connected to HIGH exposure services
- **LOW**: Internal-only, no external access

## CLI Interface

**Entry Point**: `src/reticulum/cli.py:195`

### Usage
```bash
# Generate prioritization report (compact JSON)
reticulum /path/to/repo

# Generate pretty formatted prioritization report
reticulum /path/to/repo --json

# Export network topology as Graphviz DOT file
reticulum /path/to/repo --dot network.dot
```

## Testing Strategy

### Test Structure
- **Unit Tests**: `tests/test_exposure_scanner.py` - Core functionality testing
- **Advanced Scenarios**: `tests/test_advanced_scenarios.py` - Complex real-world scenarios
- **Test Markers**: slow, integration, advanced, performance, edge_cases

### Test Configuration
- Coverage reporting enabled (HTML, XML, terminal)
- Strict markers for test organization
- Performance benchmarks and edge case handling

## Development Workflow

**For detailed development workflows, version management, and release processes, always consult `DEVELOPER.md`.**

### Quality Assurance
- **Linting**: Ruff for code quality
- **Formatting**: Black for consistent code style
- **Testing**: Comprehensive pytest suite
- **Version Management**: Automated version synchronization

### Scripts
- `scripts/dev-check.sh` - Development quality checks
- `scripts/release.sh` - Release management
- `scripts/run-advanced-tests.sh` - Advanced test scenarios

## Configuration Files

- `pyproject.toml` - Poetry configuration and dependencies
- `pytest.ini` - Testing configuration with coverage settings
- `Makefile` - Development and release targets

## Key Patterns

### Exposure Detection
- Service types (LoadBalancer, NodePort, ClusterIP)
- Ingress configurations
- Cloud-specific load balancers
- Security contexts (privileged, hostNetwork)
- External ports and cloud integrations

### Dependency Analysis
- Service-to-service dependencies
- Database and cache dependencies
- Message queue integrations
- Monitoring and storage dependencies

### Output Format
- **Prioritization Report**: Structured JSON with services sorted by risk level, including Dockerfile paths and source code paths