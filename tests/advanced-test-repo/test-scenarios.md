# 🧪 Test Scenarios for Reticulum Scanner

This document describes the expected results for each test scenario in the advanced test repository.

## 📊 **Expected Scan Results**

### **Scan Summary**
- **total_containers**: 10
- **high_exposure**: 5
- **medium_exposure**: 2
- **low_exposure**: 3
- **charts_analyzed**: 10

## 🎯 **Individual Chart Analysis**

### **1. frontend-web (HIGH Exposure)**
- **Exposure Level**: HIGH
- **Exposure Score**: 3
- **Gateway Type**: nginx
- **Hosts**: www.example.com, app.example.com, api.example.com
- **Paths**: /, /home, /about, /app, /dashboard, /api/v1, /api/v2
- **Expected Containers**: 1 (frontend-web-container)

### **2. api-gateway (HIGH Exposure)**
- **Exposure Level**: HIGH
- **Exposure Score**: 3
- **Gateway Type**: LoadBalancer/NodePort + nginx
- **Hosts**: gateway.example.com
- **Paths**: /api, /auth, /webhook
- **Expected Containers**: 1 (api-gateway-container)

### **3. backend-service (MEDIUM Exposure)**
- **Exposure Level**: MEDIUM
- **Exposure Score**: 2
- **Gateway Type**: Service Dependency
- **Host**: Connected to: api-gateway
- **Expected Containers**: 1 (backend-service-container)

### **4. worker-service (MEDIUM Exposure)**
- **Exposure Level**: MEDIUM
- **Exposure Score**: 2
- **Gateway Type**: Service Dependency
- **Host**: Connected to: api-gateway
- **Expected Containers**: 1 (worker-service-container)

### **5. database-primary (LOW Exposure)**
- **Exposure Level**: LOW
- **Exposure Score**: 1
- **Gateway Type**: Internal
- **Host**: No external access
- **Expected Containers**: 1 (database-primary-container)

### **6. cache-service (LOW Exposure)**
- **Exposure Level**: LOW
- **Exposure Score**: 1
- **Gateway Type**: Internal
- **Host**: No external access
- **Expected Containers**: 1 (cache-service-container)

### **7. monitoring-stack (LOW Exposure)**
- **Exposure Level**: LOW
- **Exposure Score**: 1
- **Gateway Type**: Internal
- **Host**: No external access
- **Expected Containers**: 1 (monitoring-stack-container)

### **8. security-gateway (HIGH Exposure)**
- **Exposure Level**: HIGH
- **Exposure Score**: 3
- **Gateway Type**: LoadBalancer/NodePort + nginx
- **Hosts**: security.example.com
- **Paths**: /, /admin, /api
- **Expected Containers**: 1 (security-gateway-container)

### **9. load-balancer (HIGH Exposure)**
- **Exposure Level**: HIGH
- **Exposure Score**: 3
- **Gateway Type**: LoadBalancer/NodePort
- **Host**: Direct Internet Access
- **Expected Containers**: 1 (load-balancer-container)

### **10. edge-cases (HIGH Exposure)**
- **Exposure Level**: HIGH
- **Exposure Score**: 3
- **Gateway Type**: Ingress
- **Hosts**: test.example.com
- **Expected Containers**: 1 (edge-cases-container)

## 🌐 **Expected Network Topology**

### **Exposed Containers (HIGH)**
- frontend-web-container
- api-gateway-container
- security-gateway-container
- load-balancer-container
- edge-cases-container

### **Linked Containers (MEDIUM)**
- backend-service-container
- worker-service-container

### **Internal Containers (LOW)**
- database-primary-container
- cache-service-container
- monitoring-stack-container

## 📊 **Expected Mermaid Diagram**

The diagram should show:
- **Internet connections** to all HIGH exposure containers
- **Service dependencies** between MEDIUM and HIGH exposure containers
- **Proper grouping** by exposure levels
- **All 10 containers** properly categorized

## 🧪 **Testing Commands**

```bash
# Basic scan
reticulum . --json > scan-results.json

# Console output
reticulum . --console

# Paths analysis
reticulum . --paths

# Validate results
python validate_results.py scan-results.json
```

## ✅ **Validation Checklist**

- [ ] **Scan Summary**: 10 containers, 5 HIGH, 2 MEDIUM, 3 LOW
- [ ] **Container Names**: All containers properly named
- [ ] **Exposure Levels**: Correct classification for each service
- [ ] **Gateway Types**: Accurate gateway type detection
- [ ] **Host Information**: Correct host data for each service
- [ ] **Network Topology**: Proper grouping by exposure level
- [ ] **Mermaid Diagram**: Complete and accurate visualization
- [ ] **Performance**: Scan completes within reasonable time
- [ ] **Error Handling**: No crashes or errors during scan
- [ ] **Edge Cases**: Malformed configurations handled gracefully

## 🚀 **Performance Benchmarks**

- **Scan Time**: Should complete in < 30 seconds
- **Memory Usage**: Should not exceed 512MB
- **CPU Usage**: Should not spike above 80%
- **Output Size**: JSON output should be < 100KB

## 🔍 **Edge Case Testing**

The edge-cases chart tests:
- **Malformed configurations** - Should handle gracefully
- **Conflicting settings** - Should resolve conflicts
- **Invalid data types** - Should handle type errors
- **Deep nesting** - Should not cause performance issues
- **Large arrays** - Should process efficiently
- **Mixed data types** - Should handle type variations
