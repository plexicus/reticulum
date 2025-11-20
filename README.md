# Reticulum

## Combat Cloud-Native Application Alert Fatigue

![Reticulum Logo](assets/images/reticulum-logo.png)

[![PyPI version](https://badge.fury.io/py/reticulum.svg)](https://badge.fury.io/py/reticulum)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/plexicus/reticulum)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**Latest Release: v0.7.0**

## What is Reticulum?

**Reticulum** is a security prioritization tool designed to combat cloud-native application alert fatigue. For every vulnerability detected, it tracks the container and examines the Helm chart configuration in Kubernetes to determine its actual exposure, helping security teams focus on what is truly critical.

Reticulum analyzes cloud infrastructure, particularly Kubernetes Helm charts, and generates structured security prioritization reports that map services to their risk levels, code paths, and Dockerfiles.

## Key Features

- **Prioritization Focus**: Generates security prioritization reports for external tools
- **Risk Classification**: Categorizes services by exposure level (HIGH, MEDIUM, LOW)
- **Code Path Mapping**: Maps services to their Dockerfiles and source code paths
- **Structured Output**: Clean JSON format optimized for external tool consumption
- **Graph Visualization**: Export network topology as Graphviz DOT files
- **High Performance**: Fast scanning of large repositories
- **Production Ready**: 100% reliable and accurate with comprehensive testing
- **Performance Optimized**: Excellent performance with large repositories
- **Edge Case Handling**: Robust handling of complex configurations

## Quick Start

### Installation
```bash
# Install uv (prerequisite)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install reticulum
uv venv
uv pip install reticulum
```

### Basic Usage
```bash
# Generate prioritization report
reticulum scan /path/to/repository

# Generate pretty formatted JSON output
reticulum scan /path/to/repository --json

# Export network topology
reticulum scan /path/to/repository --dot network.dot

# Run comprehensive security scan
reticulum security-scan /path/to/repository
```

### Example Output
```json
{
  "repo_path": "/path/to/repository",
  "scan_timestamp": "2025-11-02T10:30:00",
  "summary": {
    "total_services": 10,
    "high_risk": 3,
    "medium_risk": 4,
    "low_risk": 3
  },
  "prioritized_services": [
    {
      "service_name": "api-gateway-prod-container",
      "chart_name": "api-gateway",
      "risk_level": "HIGH",
      "exposure_type": "Ingress",
      "host": "api.example.com",
      "dockerfile_path": "services/api-gateway/Dockerfile",
      "source_code_paths": [
        "services/api-gateway/src",
        "services/api-gateway/app"
      ],
      "environment": "prod"
    }
  ]
}
```

## Installation

### Prerequisites

Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### **From PyPI (Recommended)**
```bash
# Create virtual environment
uv venv

# Install reticulum
uv pip install reticulum
```

### **From Source**
```bash
git clone https://github.com/plexicus/reticulum.git
cd reticulum

# Create virtual environment
uv venv

# Install in development mode
uv pip install -e ".[dev]"
```

## Usage

### **Available Commands**

Reticulum provides two main commands:

- **`scan`** - Exposure analysis and prioritization
- **`security-scan`** - Integrated security scanning with Trivy and Semgrep

### **Exposure Analysis (`scan` command)**

Analyze Helm charts and generate exposure-based prioritization reports.

```bash
# Basic exposure analysis
reticulum scan /path/to/repository

# Pretty formatted JSON output
reticulum scan /path/to/repository --json

# Export network topology as Graphviz DOT file
reticulum scan /path/to/repository --dot network.dot
```

**Options for `scan` command:**
- `--json` - Pretty print JSON output (always formatted like jq)
- `--dot FILE` - Export network topology as Graphviz DOT file

### **Security Scanning (`security-scan` command)**

Run comprehensive security scan with Trivy SCA, Semgrep SAST, and exposure analysis.

```bash
# Run complete security scan
reticulum security-scan /path/to/repository

# Save enhanced SARIF report to file
reticulum security-scan /path/to/repository --output results.sarif
```

**Options for `security-scan` command:**
- `--output, -o FILE` - Save enhanced SARIF report to file

### **Global Options**
- `--version` - Show program's version number
- `--help` - Show help message for any command

### **Practical Examples**

```bash
# Get help for specific commands
reticulum --help
reticulum scan --help
reticulum security-scan --help

# Check version
reticulum --version

# Scan a repository and save DOT file for visualization
reticulum scan /path/to/kubernetes-repo --dot topology.dot

# Run security scan and save SARIF report for CI/CD integration
reticulum security-scan /path/to/kubernetes-repo --output security-results.sarif

# Pipe scan results to jq for further processing
reticulum scan /path/to/repo --json | jq '.prioritized_services[] | select(.risk_level == "HIGH")'
```

### **Output Format**

The tool generates a prioritization report with the following structure:

```json
{
  "repo_path": "/path/to/repository",
  "scan_timestamp": "2025-11-02T10:30:00",
  "summary": {
    "total_services": 10,
    "high_risk": 3,
    "medium_risk": 4,
    "low_risk": 3
  },
  "prioritized_services": [
    {
      "service_name": "api-gateway-prod-container",
      "chart_name": "api-gateway",
      "risk_level": "HIGH",
      "exposure_type": "Ingress",
      "host": "api.example.com",
      "dockerfile_path": "services/api-gateway/Dockerfile",
      "source_code_paths": [
        "services/api-gateway/src",
        "services/api-gateway/app"
      ],
      "environment": "prod"
    }
  ]
}
```

**Key Fields:**
- **repo_path**: Path to the scanned repository
- **scan_timestamp**: ISO timestamp of the scan
- **summary**: Statistics (total services, risk level counts)
- **prioritized_services**: Array of services sorted by risk level (HIGH → MEDIUM → LOW)
  - **service_name**: Name of the container/service
  - **chart_name**: Name of the Helm chart
  - **risk_level**: Exposure level (HIGH/MEDIUM/LOW)
  - **exposure_type**: Type of exposure (Ingress, LoadBalancer, etc.)
  - **host**: Hostname or exposure description
  - **dockerfile_path**: Path to Dockerfile (if found)
  - **source_code_paths**: Array of source code paths (if found)
  - **environment**: Environment name (base, dev, prod, etc.)

## Configuration

### **Environment Variables**
- `RETICULUM_LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `RETICULUM_TIMEOUT`: Set scan timeout in seconds
- `RETICULUM_MAX_WORKERS`: Set maximum concurrent workers

### **Configuration Files**
- `pyproject.toml`: Project configuration and dependencies
- `pytest.ini`: Testing configuration
- `.github/workflows/`: CI/CD workflow definitions

## Performance Benchmarks

- **Scan Time**: < 30 seconds for complex repositories
- **Memory Usage**: < 512MB peak usage
- **Output Size**: < 100KB for typical scans
- **Scalability**: Handles repositories with 100+ charts

## Support & Community

- **Issues**: [GitHub Issues](https://github.com/plexicus/reticulum/issues)
- **Discussions**: [GitHub Discussions](https://github.com/plexicus/reticulum/discussions)
- **Documentation**: [Project Wiki](https://github.com/plexicus/reticulum/wiki)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

For detailed development workflows, testing strategies, and release processes, see [DEVELOPER.md](DEVELOPER.md).

### **Development Workflow**
```bash
# Fork and clone
git clone https://github.com/your-username/reticulum.git
cd reticulum

# Setup development environment
make dev-setup

# Make changes and test
make test-all

# Quality checks
make check

# Commit and push
git commit -am "feat: add new feature"
git push origin feature-branch
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Plexicus, LLC

## Acknowledgments

- **Kubernetes Community**: For the excellent Helm chart ecosystem
- **Python Community**: For the robust testing and development tools
- **Security Community**: For continuous feedback and improvement suggestions

## Troubleshooting

### **Advanced Tests Skipped Due to Missing Test Repository**

If advanced tests are skipped with "Advanced test repository not found":

```bash
# Run advanced tests
make advanced-tests

# Or run all tests
make test-all
```

**Note**: The test repository is now committed as static test data and should be available automatically.

---

**Reticulum** - Making cloud infrastructure security scanning accessible, reliable, and comprehensive.