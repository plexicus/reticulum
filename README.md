# Reticulum

**Exposure Scanner for Cloud Infrastructure Security Analysis**

Reticulum is a powerful tool that analyzes monorepos containing Helm charts to identify internet exposure and map affected source code paths. It provides comprehensive security assessment for DevSecOps and Cloud Security teams.

## Features

- **Multi-environment analysis** (dev, staging, prod)
- **Internet exposure detection** via Ingress, LoadBalancer, NodePort
- **Source code path mapping** from Dockerfiles
- **Master paths consolidation** with highest exposure level
- **JSON output** with network topology and Mermaid diagrams

## Requirements

- Python >= 3.9
- PyYAML: YAML parsing for Helm charts and configurations

### Optional External Tools

- **Helm CLI**: For chart validation and templating
- **Docker**: For Dockerfile validation
- **kubectl**: For Kubernetes resource validation

## Installation

This project uses Poetry for dependency management. To get started:

```bash
# Clone the repository
git clone <repository-url>
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

### Dev Container
This project includes VS Code Dev Container configuration for consistent development environments.

## License

MIT License - Copyright (c) 2024 Plexicus, LLC

## Author

Jose Palanco <jose.palanco@plexicus.ai>
