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
```

### Dev Container
This project includes VS Code Dev Container configuration for consistent development environments.

## License

MIT License - Copyright (c) 2025 Plexicus, LLC

## Author

Jose Palanco <jose.palanco@plexicus.ai>
