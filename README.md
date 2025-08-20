# Reticulum

**Exposure Scanner for Cloud Infrastructure Security Analysis**

Reticulum is a powerful tool that analyzes monorepos containing Helm charts to identify internet exposure and map affected source code paths. It provides comprehensive security assessment for DevSecOps and Cloud Security teams.

## Features

- **Multi-environment analysis** (dev, staging, prod)
- **Internet exposure detection** via Ingress, LoadBalancer, NodePort
- **Source code path mapping** from Dockerfiles
- **Master paths consolidation** with highest exposure level
- **JSON output** with network topology and Mermaid diagrams
- **Modular architecture** with specialized analyzers for each concern

## Requirements

- Python >= 3.9
- PyYAML: YAML parsing for Helm charts and configurations

### Optional External Tools

- **Helm CLI**: For chart validation and templating
- **Docker**: For Dockerfile validation
- **kubectl**: For Kubernetes resource validation

## Installation

### From PyPI (Recommended)

```bash
# Install the latest version
pip install reticulum

# Or with uv (faster)
uv add reticulum
```

### From Source

This project uses Poetry for dependency management. To get started:

```bash
# Clone the repository
git clone https://github.com/plexicus/reticulum.git
cd reticulum

# Install dependencies
poetry install

# Activate the virtual environment
poetry shell
```

## Usage

Reticulum can be used in multiple ways after installation:

### Command Line Interface

#### Via Poetry (recommended for development)
```bash
# Default mode - Container exposure analysis
poetry run reticulum /path/to/your/repo

# Paths mode - Source code path analysis
poetry run reticulum /path/to/your/repo --paths
```

#### Via Python Module
```bash
# Default mode - Container exposure analysis
python -m reticulum /path/to/your/repo

# Paths mode - Source code path analysis  
python -m reticulum /path/to/your/repo --paths
```

#### After Installation
```bash
# Install the package
pip install .

# Use directly
reticulum /path/to/your/repo
reticulum /path/to/your/repo --paths
```

### Python API
```python
from reticulum import ExposureScanner

# Create scanner instance
scanner = ExposureScanner()

# Scan a repository
results = scanner.scan_repo("/path/to/your/repo")

# Access results
print(f"Found {results['scan_summary']['total_containers']} containers")
print(f"High exposure: {results['scan_summary']['high_exposure']}")
```

## Output Formats

### Default Mode (Container Analysis)
Returns JSON with:
- **Container exposure analysis**: Detailed breakdown of each container's exposure level
- **Network topology mapping**: How containers connect and expose each other
- **Mermaid diagram**: Visualization-ready diagram code
- **Scan summary**: High-level statistics

```json
{
  "repo_path": "/path/to/repo",
  "scan_summary": {
    "total_containers": 5,
    "high_exposure": 2,
    "medium_exposure": 1,
    "low_exposure": 2,
    "charts_analyzed": 3
  },
  "containers": [...],
  "network_topology": {...},
  "mermaid_diagram": "graph TD\n..."
}
```

### Paths Mode (Source Code Analysis)
Returns JSON with:
- **Master paths**: Consolidated source code paths with highest exposure levels
- **Path-to-container mapping**: Which containers affect which source code
- **Exposure consolidation**: Summary of risk levels by codebase area

```json
{
  "repo_path": "/path/to/repo", 
  "scan_summary": {...},
  "master_paths": {
    "src/": {
      "path": "src/",
      "exposure_level": "HIGH",
      "exposure_score": 3,
      "container_names": ["api-container", "web-container"],
      "primary_container": "api-container"
    }
  }
}
```

## Exposure Levels

- **🔴 HIGH**: Direct internet exposure (Ingress, LoadBalancer, NodePort)
- **🟡 MEDIUM**: Connected to HIGH exposure containers (internal services)
- **🟢 LOW**: Internal only, no internet access or HIGH container connections

## Architecture

Reticulum is built with a **modular architecture** that separates concerns for better maintainability, testing, and extensibility:

### Core Modules

- **`ExposureAnalyzer`** - Analyzes Helm charts for exposure patterns
- **`DockerfileAnalyzer`** - Parses Dockerfiles and extracts source code paths
- **`DependencyAnalyzer`** - Analyzes service dependencies and exposure levels
- **`PathConsolidator`** - Consolidates source code paths and builds master paths
- **`MermaidBuilder`** - Generates network topology diagrams
- **`CLI`** - Command-line interface and argument parsing

### Benefits

- **🎯 Single Responsibility** - Each module has one clear purpose
- **🧪 Easier Testing** - Test individual components in isolation
- **👥 Better Collaboration** - Multiple developers can work on different modules
- **🔧 Easier Maintenance** - Fix bugs in specific functionality without touching others
- **📚 Better Documentation** - Each module can be documented separately
- **🚀 Easier Extension** - Add new features by creating new modules

## Development

### Prerequisites
- Python 3.9+
- Poetry

### Setup Development Environment
```bash
# Install development dependencies
poetry install --with dev

# Run tests
poetry run pytest

# Format code
poetry run black src/

# Lint code
poetry run ruff check src/
```

### Quality Assurance & Release Management

Reticulum includes a comprehensive quality assurance system with **strict gates** that **require all tests to pass** before allowing releases.

#### Quick Quality Checks
```bash
# Daily development checks (non-interactive)
make quick-check

# All quality checks (lint + format + test)
make check
```

#### Pre-Release Verification
```bash
# Full pre-release verification (interactive)
make pre-release

# Strict release check (all tests + version sync)
make release-strict
```

#### Version Synchronization
```bash
# Check version consistency across all files
make version-sync
```

**⚠️ IMPORTANT: Tests MUST pass before creating tags or releases!**

The system includes multiple quality gates:
- ✅ **Linting** with ruff (auto-fix enabled)
- ✅ **Formatting** with black (auto-format enabled)  
- ✅ **Tests** with pytest (11 test suite)
- ✅ **Version sync** between pyproject.toml, __init__.py, and git tags
- ❌ **Blocks release** if any gate fails

### Project Structure
```
src/reticulum/
├── __init__.py          # Package exports
├── main.py              # Main ExposureScanner orchestrator
├── exposure_analyzer.py # Helm chart exposure detection
├── dockerfile_analyzer.py # Dockerfile parsing & path extraction
├── dependency_analyzer.py # Service dependency analysis
├── path_consolidator.py # Source code path consolidation
├── mermaid_builder.py   # Mermaid diagram generation
├── cli.py               # Command-line interface
└── __main__.py          # Module execution entry point

scripts/
├── quick-check.sh       # Quick quality checks (non-interactive)
├── pre-release-check.sh # Full pre-release verification
├── version-sync.sh      # Version consistency verification
└── README.md            # Scripts documentation

.github/workflows/
├── publish.yml          # CI/CD: test, lint, build, publish to PyPI
└── release.yml          # GitHub release automation
```

### Dev Container
This project includes VS Code Dev Container configuration for consistent development environments.

### Release Workflow

**🚨 CRITICAL: Always run quality checks before releases!**

```bash
# 1. Ensure all tests pass
make release-strict

# 2. If successful, create tag
git tag v0.x.x
git push origin v0.x.x

# 3. GitHub Actions will automatically:
#    - Run all tests
#    - Build package
#    - Publish to PyPI
```

**Never create tags without passing all quality gates!**

## Quality Assurance System

Reticulum implements a **zero-tolerance quality system** that prevents releases with failing tests or quality issues.

### Quality Gates

| Gate | Tool | Action | Failure Result |
|------|------|--------|----------------|
| **Linting** | ruff | Auto-fix + verify | ❌ Release blocked |
| **Formatting** | black | Auto-format + verify | ❌ Release blocked |
| **Testing** | pytest | Run 11 test suite | ❌ Release blocked |
| **Version Sync** | Custom script | Verify consistency | ❌ Release blocked |

### Available Commands

```bash
# Development
make install          # Install dependencies
make test            # Run tests only
make lint            # Run linting only
make format          # Format code only
make check           # All quality checks
make dev             # Setup development environment

# Quality Assurance
make quick-check     # Quick daily checks
make pre-release     # Full pre-release verification
make version-sync    # Version consistency check
make release-strict  # Strict release workflow

# Utilities
make clean           # Clean temporary files
make help            # Show all available commands
```

### Why This Matters

- **🚫 Prevents broken releases** - No tags without passing tests
- **🔒 Maintains code quality** - Automated linting and formatting
- **📊 Ensures consistency** - Version sync across all files
- **🧪 Guarantees reliability** - All tests must pass
- **🚀 Streamlines workflow** - One command for complete verification

For detailed script documentation, see [`scripts/README.md`](scripts/README.md).

## License

MIT License - Copyright (c) 2025 Plexicus, LLC

## Author

Jose Palanco <jose.palanco@plexicus.ai>
