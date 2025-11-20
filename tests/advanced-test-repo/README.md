# 🔍 Advanced Test Repository for Reticulum Scanner

This repository contains comprehensive test scenarios for the Reticulum security scanner, covering all types of container exposure, network topologies, and security configurations.

## 🎯 **Test Scenarios Covered**

### **1. High Exposure Services**
- **Ingress-enabled services** with multiple hosts and paths
- **LoadBalancer services** with direct internet access
- **NodePort services** with external port exposure
- **Cloud-specific configurations** (Azure, AWS, GCP)
- **External host configurations**

### **2. Medium Exposure Services**
- **Service dependencies** connected to HIGH exposure services
- **Internal services** with specific security requirements
- **Linked services** in complex architectures

### **3. Low Exposure Services**
- **Internal-only services** with no external access
- **Database services** with restricted access
- **Monitoring services** for internal use

### **4. Complex Network Topologies**
- **Multi-tier architectures** with service dependencies
- **Microservices patterns** with inter-service communication
- **Security gateways** and proxy configurations

### **5. Edge Cases**
- **Malformed configurations** for robustness testing
- **Deep nesting** for performance testing
- **Large arrays** and complex data structures
- **Mixed security levels** in single charts

## 🏗️ **Repository Structure**

```
advanced-test-repo/
├── charts/
│   ├── frontend-web/          # HIGH: Ingress enabled
│   ├── api-gateway/           # HIGH: LoadBalancer + Ingress
│   ├── backend-service/       # MEDIUM: Connected to API
│   ├── worker-service/        # MEDIUM: Background processing
│   ├── database-primary/      # LOW: Internal only
│   ├── cache-service/         # LOW: Internal only
│   ├── monitoring-stack/      # LOW: Internal monitoring
│   ├── security-gateway/      # HIGH: Security proxy
│   ├── load-balancer/         # HIGH: Traffic distribution
│   └── edge-cases/            # Various edge case scenarios
├── dockerfiles/               # Sample Dockerfiles for each service
├── source-code/               # Sample source code for analysis
└── test-scenarios.md         # Detailed test scenario descriptions
```

## 🧪 **Testing Strategy**

### **Automated Testing**
- **Unit tests** for individual chart analysis
- **Integration tests** for complete repository scanning
- **Performance tests** for large repository handling
- **Edge case tests** for robustness validation

### **Manual Validation**
- **Visual inspection** of generated outputs
- **Cross-reference** with expected results
- **Performance benchmarking** on different systems

## 🚀 **Usage**

```bash
# Clone the repository
git clone <this-repo>

# Run Reticulum scanner
reticulum . --json > scan-results.json

# Run with different output formats
reticulum . --console
reticulum . --paths

# Validate results against expected outputs
python validate_results.py scan-results.json
```

## 📊 **Expected Results**

Each test scenario includes:
- **Expected exposure levels** for validation
- **Expected network topology** for verification
- **Expected Mermaid diagrams** for visualization
- **Performance benchmarks** for comparison

## 🔧 **Maintenance**

This repository is designed to be:
- **Version controlled** with the scanner releases
- **Extensible** for new test scenarios
- **Documented** for easy understanding
- **Automated** for continuous testing
