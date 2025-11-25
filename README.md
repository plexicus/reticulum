# Reticulum

**Cloud-Native Contextual Security Prioritizer by PLEXICUS**

![Reticulum Logo](assets/images/reticulum-logo.png)

[![By PLEXICUS](https://img.shields.io/badge/By-PLEXICUS-blueviolet)](https://www.plexicus.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Production Ready](https://img.shields.io/badge/Status-Production%20Ready-success)]()

> **By:** [PLEXICUS](https://www.plexicus.ai) - AI-Driven ASPM Platform

Reticulum is a high-performance security analysis engine that prioritizes vulnerabilities based on their **actual exposure** in Kubernetes environments. Instead of treating all HIGH/CRITICAL vulnerabilities equally, Reticulum analyzes your deployment architecture (Ingress, Istio, Service Mesh) to determine which services are truly exposed and adjusts risk scores accordingly.

## 🎯 Core Principle

**"Context is King."**

A **MEDIUM** severity vulnerability in a public-facing, privileged authentication service is **CRITICAL**.
A **HIGH** severity vulnerability in a locked-down, internal-only worker is **LOW PRIORITY**.

Reticulum automates this logic.

## 🚀 Key Features

### 🧠 Advanced Rule Engine
- **Custom Logic**: Define prioritization rules using simple YAML.
- **Contextual Scoring**: Boost scores for critical services (Auth, Payments) or reduce them for internal tools.
- **Flexible Targets**: Match against Helm Chart metadata, `values.yaml` configurations, or specific vulnerability findings.
- [**View Full Rule Documentation**](RULES.md)

### 🌐 Exposure Detection
Automatically detects public exposure vectors:
- **Ingress Controllers**: NGINX, Traefik, HAProxy
- **Service Mesh**: Istio VirtualServices & Gateways
- **Gateway API**: HTTPRoutes
- **Cloud LoadBalancers**: Service type `LoadBalancer`
- **Ambassador/Emissary**: Mappings

### 🛡️ Security Context Analysis
Adjusts risk based on deep configuration analysis:
- **Privileged Containers**: Drastically increases risk score.
- **Service Account Mounting**: Detects dangerous token automounting.
- **Capabilities**: Identifies dangerous Linux capabilities (e.g., `SYS_ADMIN`).

### 🔌 Native Integrations
- **Infrastructure**: Trivy (Container & FS scanning)
- **Code**: Semgrep (SAST)
- **Output**: JSON reports, Enriched SARIF, CLI summaries

## 📦 Installation


### **🐳 Docker (Recommended)**

Reticulum supports multi-architecture builds out of the box (Apple Silicon/ARM64 and Intel/AMD64).

1. **Build the image:**  
   docker build -t reticulum .

2. Run with analysis data:  
   Since Reticulum runs inside a container, you must mount the directory containing your code and SARIF reports.  
   # Mount current directory to /data and analyze 
   ```bash 
   docker run --rm -v $(pwd):/data reticulum \  
     -p /data/tests/monorepo-06 \  
     -s /data/tests/monorepo-06/trivy.sarif
   ```


### **🛠️ Build from Source**

#### Prerequisites
- [D Language Compiler](https://dlang.org/download.html) (DMD or LDC2)
- [DUB](https://code.dlang.org/download) (Package Manager)
- [Trivy](https://trivy.dev/) & [Semgrep](https://semgrep.dev/) (Scanners)

#### Build from Source
```bash
git clone https://github.com/plexicus/reticulum.git
cd reticulum
dub build --compiler=ldc2
```

## ⚡ Quick Start

### 1. Scan your Monorepo
Use the helper script to generate SARIF files from your source:
```bash
./run_tools.sh tests/monorepo-06
```

### 2. Run Reticulum
Analyze the results with contextual awareness:
```bash
./reticulum -p tests/monorepo-06 -s tests/monorepo-06/trivy.sarif
```

### 3. See the Difference
Reticulum will output a prioritized list of vulnerabilities, highlighting why certain issues were escalated (e.g., `Public Exposure`, `Privileged`).

## 🧪 Test Scenarios

The repository includes comprehensive test monorepos demonstrating Reticulum's capabilities:

| Monorepo | Scenario | Key Feature Tested |
|----------|----------|-------------------|
| **monorepo-01** | Baseline Ingress | NGINX Ingress detection |
| **monorepo-02** | Service Mesh | Istio VirtualService detection |
| **monorepo-03** | Gateway API | Kubernetes Gateway API support |
| **monorepo-04** | Polyglot | React/Ruby stack analysis |
| **monorepo-05** | Ambassador | Emissary-Ingress mappings |
| **monorepo-06** | **Context Demo** | **Multi-service prioritization (Public vs Internal)** |
| **monorepo-07** | **Rule Validation** | **Systematic rule engine testing** |

## 🎨 Priority Levels

| Priority | Score | Description | Action |
|----------|-------|-------------|--------|
| **P0_BLEEDING** | 90-100 | Critical public exposure | **FIX IMMEDIATELY** |
| **P1_CRITICAL** | 70-89 | High risk, potential breach | Fix within 24h |
| **P2_HIGH** | 50-69 | Moderate risk | Fix in next sprint |
| **P3_MEDIUM** | 30-49 | Internal/Mitigated | Backlog |
| **P4_LOW** | 0-29 | Informational | Monitor |

## 🛠 Project Structure

```
reticulum-d/
├── src/
│   ├── app.d           # CLI Entry Point
│   ├── analyzer.d      # Exposure Analysis Logic
│   ├── ingestor.d      # SARIF Processing & Scoring
│   ├── rules/          # Rule Engine Implementation
│   └── discovery.d     # Service Discovery
├── rules/              # Default YAML Rules
│   ├── exposure/       # Exposure Detection Rules
│   ├── security/       # Security Hardening Rules
│   └── scoring/        # Classification & Scoring
└── tests/              # Test Monorepos
```

## 🤝 Contributing

Contributions are welcome! Please read [RULES.md](RULES.md) to understand how to add new detection logic.

## 👥 Maintainer

**Jose Ramon Palanco**  
Email: [jose.palanco@plexicus.ai](mailto:jose.palanco@plexicus.ai)  

## 🏢 PLEXICUS

This open-source project is by **[PLEXICUS](https://www.plexicus.ai)** - AI-Driven Security for Cloud-Native.

Visit [www.plexicus.ai](https://www.plexicus.ai) to learn more.

---
*Reticulum is a prioritization tool. Always validate findings.*
