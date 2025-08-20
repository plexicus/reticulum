#!/usr/bin/env python3
"""
Validation script for Reticulum scanner results.
Compares actual scan output with expected results.
"""

import json
import sys
from typing import Dict, Any, List

class ResultValidator:
    def __init__(self, expected_results: Dict[str, Any]):
        self.expected = expected_results
        self.errors = []
        self.warnings = []
        
    def validate_scan_summary(self, actual: Dict[str, Any]) -> bool:
        """Validate scan summary fields."""
        print("🔍 Validating Scan Summary...")
        
        expected_summary = self.expected["scan_summary"]
        actual_summary = actual.get("scan_summary", {})
        
        # For charts_analyzed, we expect exact match
        if "charts_analyzed" in actual_summary:
            expected_charts = expected_summary.get("charts_analyzed")
            actual_charts = actual_summary.get("charts_analyzed")
            if expected_charts != actual_charts:
                self.errors.append(f"Scan Summary charts_analyzed: Expected {expected_charts}, got {actual_charts}")
                return False
            else:
                print(f"  ✅ charts_analyzed: {actual_charts}")
        
        # For container counts, we expect at least the expected number
        if "total_containers" in actual_summary:
            expected_total = expected_summary.get("total_containers")
            actual_total = actual_summary.get("total_containers")
            if actual_total < expected_total:
                self.errors.append(f"Scan Summary total_containers: Expected at least {expected_total}, got {actual_total}")
                return False
            else:
                print(f"  ✅ total_containers: {actual_total} (expected at least {expected_total})")
        
        # For exposure levels, we expect at least the expected numbers
        exposure_fields = ["high_exposure", "medium_exposure", "low_exposure"]
        for field in exposure_fields:
            if field in actual_summary:
                expected_val = expected_summary.get(field, 0)
                actual_val = actual_summary.get(field, 0)
                if actual_val < expected_val:
                    self.errors.append(f"Scan Summary {field}: Expected at least {expected_val}, got {actual_val}")
                    return False
                else:
                    print(f"  ✅ {field}: {actual_val} (expected at least {expected_val})")
        
        return True
    
    def validate_containers(self, actual: List[Dict[str, Any]]) -> bool:
        """Validate container configurations."""
        print("\n🐳 Validating Containers...")
        
        expected_containers = self.expected["containers"]
        
        # For edge cases, we expect more containers due to multiple detections
        # So we'll be more flexible with the count
        if len(actual) >= len(expected_containers):
            print(f"  ✅ Container count: {len(actual)} (expected at least {len(expected_containers)})")
        else:
            self.errors.append(f"Container count: Expected at least {len(expected_containers)}, got {len(actual)}")
            return False
        
        # Group containers by chart name to handle multiple detections
        containers_by_chart = {}
        for container in actual:
            chart_name = container.get("chart", "unknown")
            if chart_name not in containers_by_chart:
                containers_by_chart[chart_name] = []
            containers_by_chart[chart_name].append(container)
        
        print(f"  📊 Charts found: {len(containers_by_chart)}")
        for chart_name, containers in containers_by_chart.items():
            print(f"    - {chart_name}: {len(containers)} containers")
        
        # Validate that we have containers for all expected charts
        expected_charts = set(cont.get("chart") for cont in expected_containers)
        actual_charts = set(containers_by_chart.keys())
        
        if not expected_charts.issubset(actual_charts):
            missing_charts = expected_charts - actual_charts
            self.errors.append(f"Missing charts: {missing_charts}")
            return False
        
        # Validate exposure levels for each chart
        for chart_name in expected_charts:
            chart_containers = containers_by_chart[chart_name]
            
            # Find expected container for this chart
            expected_container = next((c for c in expected_containers if c.get("chart") == chart_name), None)
            if not expected_container:
                continue
                
            # Check that at least one container has the expected exposure level
            expected_level = expected_container.get("exposure_level")
            expected_score = expected_container.get("exposure_score")
            
            chart_has_correct_exposure = False
            for container in chart_containers:
                if (container.get("exposure_level") == expected_level and 
                    container.get("exposure_score") == expected_score):
                    chart_has_correct_exposure = True
                    break
            
            if not chart_has_correct_exposure:
                self.errors.append(f"Chart {chart_name} missing correct exposure level {expected_level} with score {expected_score}")
                return False
        
        print("  ✅ All charts have correct exposure levels")
        return True
    
    def validate_network_topology(self, actual: Dict[str, Any]) -> bool:
        """Validate network topology."""
        print("\n🌐 Validating Network Topology...")
        
        expected_topology = self.expected["network_topology"]
        actual_topology = actual.get("network_topology", {})
        
        topology_fields = ["exposed_containers", "linked_containers", "internal_containers"]
        
        for field in topology_fields:
            expected_val = expected_topology.get(field, [])
            actual_val = actual_topology.get(field, [])
            
            # For exposed containers, we expect at least the expected ones
            if field == "exposed_containers":
                if len(actual_val) >= len(expected_val):
                    print(f"  ✅ {field}: {len(actual_val)} containers (expected at least {len(expected_val)})")
                else:
                    self.errors.append(f"Network Topology {field}: Expected at least {len(expected_val)}, got {len(actual_val)}")
                    return False
            else:
                # For other fields, exact match
                if isinstance(expected_val, list):
                    expected_val = sorted(expected_val)
                if isinstance(actual_val, list):
                    actual_val = sorted(actual_val)
                
                if expected_val == actual_val:
                    print(f"  ✅ {field}: {len(actual_val)} containers")
                else:
                    self.errors.append(f"Network Topology {field}: Expected {expected_val}, got {actual_val}")
                    return False
        
        return True
    
    def validate_mermaid_diagram(self, actual: str) -> bool:
        """Validate Mermaid diagram."""
        print("\n📊 Validating Mermaid Diagram...")
        
        if not actual:
            self.errors.append("Mermaid diagram is empty")
            return False
        
        # Check for basic diagram structure
        if "graph TD" not in actual:
            self.errors.append("Mermaid diagram missing 'graph TD' declaration")
            return False
        
        if "subgraph High_Exposure" not in actual:
            self.errors.append("Mermaid diagram missing High_Exposure group")
            return False
        
        if "subgraph Medium_Exposure" not in actual:
            self.errors.append("Mermaid diagram missing Medium_Exposure group")
            return False
        
        if "subgraph Low_Exposure" not in actual:
            self.errors.append("Mermaid diagram missing Low_Exposure group")
            return False
        
        print("  ✅ Mermaid diagram structure is valid")
        return True
    
    def validate_performance(self, scan_time: float, output_size: int) -> bool:
        """Validate performance benchmarks."""
        print("\n🚀 Validating Performance...")
        
        # Performance benchmarks
        if scan_time > 30:
            self.warnings.append(f"Scan time ({scan_time:.2f}s) exceeds 30s benchmark")
        
        if output_size > 100 * 1024:  # 100KB
            self.warnings.append(f"Output size ({output_size} bytes) exceeds 100KB benchmark")
        
        print(f"  ✅ Scan Time: {scan_time:.2f}s")
        print(f"  ✅ Output Size: {output_size} bytes")
        
        return True
    
    def run_validation(self, actual_results: Dict[str, Any], scan_time: float = 0.0) -> bool:
        """Run complete validation."""
        print("🧪 Starting Result Validation...")
        print("=" * 50)
        
        success = True
        
        # Validate scan summary
        if not self.validate_scan_summary(actual_results):
            success = False
        
        # Validate containers
        if not self.validate_containers(actual_results.get("containers", [])):
            success = False
        
        # Validate network topology
        if not self.validate_network_topology(actual_results):
            success = False
        
        # Validate Mermaid diagram
        if not self.validate_mermaid_diagram(actual_results.get("mermaid_diagram", "")):
            success = False
        
        # Validate performance
        output_size = len(json.dumps(actual_results, indent=2).encode('utf-8'))
        self.validate_performance(scan_time, output_size)
        
        # Print results
        print("\n" + "=" * 50)
        print("📊 VALIDATION RESULTS")
        print("=" * 50)
        
        if success:
            print("✅ ALL VALIDATIONS PASSED!")
        else:
            print("❌ SOME VALIDATIONS FAILED!")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        return success

def main():
    """Main validation function."""
    if len(sys.argv) != 2:
        print("Usage: python validate_results.py <scan_results.json>")
        sys.exit(1)
    
    results_file = sys.argv[1]
    
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            actual_results = json.load(f)
    except Exception as e:
        print(f"Error loading results file: {e}")
        sys.exit(1)
    
    # Expected results based on test scenarios
    expected_results = {
        "scan_summary": {
            "total_containers": 10,
            "high_exposure": 5,
            "medium_exposure": 2,
            "low_exposure": 3,
            "charts_analyzed": 10
        },
        "containers": [
            {
                "name": "frontend-web-container",
                "chart": "frontend-web",
                "exposure_level": "HIGH",
                "exposure_score": 3,
                "gateway_type": "nginx"
            },
            {
                "name": "api-gateway-container",
                "chart": "api-gateway",
                "exposure_level": "HIGH",
                "exposure_score": 3,
                "gateway_type": "LoadBalancer/NodePort"
            },
            {
                "name": "backend-service-container",
                "chart": "backend-service",
                "exposure_level": "MEDIUM",
                "exposure_score": 2,
                "gateway_type": "Service Dependency"
            },
            {
                "name": "worker-service-container",
                "chart": "worker-service",
                "exposure_level": "MEDIUM",
                "exposure_score": 2,
                "gateway_type": "Service Dependency"
            },
            {
                "name": "database-primary-container",
                "chart": "database-primary",
                "exposure_level": "LOW",
                "exposure_score": 1,
                "gateway_type": "Internal"
            },
            {
                "name": "cache-service-container",
                "chart": "cache-service",
                "exposure_level": "LOW",
                "exposure_score": 1,
                "gateway_type": "Internal"
            },
            {
                "name": "monitoring-stack-container",
                "chart": "monitoring-stack",
                "exposure_level": "LOW",
                "exposure_score": 1,
                "gateway_type": "Internal"
            },
            {
                "name": "security-gateway-container",
                "chart": "security-gateway",
                "exposure_level": "HIGH",
                "exposure_score": 3,
                "gateway_type": "LoadBalancer/NodePort"
            },
            {
                "name": "load-balancer-container",
                "chart": "load-balancer",
                "exposure_level": "HIGH",
                "exposure_score": 3,
                "gateway_type": "LoadBalancer/NodePort"
            },
            {
                "name": "edge-cases-container",
                "chart": "edge-cases",
                "exposure_level": "HIGH",
                "exposure_score": 3,
                "gateway_type": "Ingress"
            }
        ],
        "network_topology": {
            "exposed_containers": [
                "frontend-web-container",
                "api-gateway-container",
                "security-gateway-container",
                "load-balancer-container",
                "edge-cases-container"
            ],
            "linked_containers": [
                "backend-service-container",
                "worker-service-container"
            ],
            "internal_containers": [
                "database-primary-container",
                "cache-service-container",
                "monitoring-stack-container"
            ]
        }
    }
    
    # Run validation
    validator = ResultValidator(expected_results)
    success = validator.run_validation(actual_results)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
