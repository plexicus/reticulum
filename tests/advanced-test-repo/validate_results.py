#!/usr/bin/env python3
"""
Validation script for Reticulum scanner results.
Compares actual scan output with expected results for prioritization format.
"""

import json
import sys
from typing import Dict, Any, List

class ResultValidator:
    def __init__(self, expected_results: Dict[str, Any]):
        self.expected = expected_results
        self.errors = []
        self.warnings = []

    def validate_prioritization_report(self, actual: Dict[str, Any]) -> bool:
        """Validate prioritization report structure."""
        print("🔍 Validating Prioritization Report...")

        # CLI output is the prioritization report itself, not wrapped
        prioritization_report = actual

        # Validate required fields
        required_fields = ["repo_path", "scan_timestamp", "summary", "prioritized_services"]
        for field in required_fields:
            if field not in prioritization_report:
                self.errors.append(f"Missing required field in prioritization report: {field}")
                return False

        print("  ✅ Prioritization report structure is valid")
        return True

    def validate_prioritization_summary(self, actual: Dict[str, Any]) -> bool:
        """Validate prioritization summary fields."""
        print("\n📊 Validating Prioritization Summary...")

        expected_summary = self.expected["summary"]
        actual_summary = actual["summary"]

        # For total_services, we expect at least the expected number
        if "total_services" in actual_summary:
            expected_total = expected_summary.get("total_services")
            actual_total = actual_summary.get("total_services")
            if actual_total < expected_total:
                self.errors.append(f"Summary total_services: Expected at least {expected_total}, got {actual_total}")
                return False
            else:
                print(f"  ✅ total_services: {actual_total} (expected at least {expected_total})")

        # For risk levels, we expect at least the expected numbers
        risk_fields = ["high_risk", "medium_risk", "low_risk"]
        for field in risk_fields:
            if field in actual_summary:
                expected_val = expected_summary.get(field, 0)
                actual_val = actual_summary.get(field, 0)
                if actual_val < expected_val:
                    self.errors.append(f"Summary {field}: Expected at least {expected_val}, got {actual_val}")
                    return False
                else:
                    print(f"  ✅ {field}: {actual_val} (expected at least {expected_val})")

        return True

    def validate_prioritized_services(self, actual: List[Dict[str, Any]]) -> bool:
        """Validate prioritized services structure and content."""
        print("\n🐳 Validating Prioritized Services...")

        expected_services = self.expected["prioritized_services"]
        actual_services = actual["prioritized_services"]

        # For edge cases, we expect more services due to multiple detections
        # So we'll be more flexible with the count
        if len(actual_services) >= len(expected_services):
            print(f"  ✅ Service count: {len(actual_services)} (expected at least {len(expected_services)})")
        else:
            self.errors.append(f"Service count: Expected at least {len(expected_services)}, got {len(actual_services)}")
            return False

        # Group services by chart name to handle multiple detections
        services_by_chart = {}
        for service in actual_services:
            chart_name = service.get("chart_name", "unknown")
            if chart_name not in services_by_chart:
                services_by_chart[chart_name] = []
            services_by_chart[chart_name].append(service)

        print(f"  📊 Charts found: {len(services_by_chart)}")
        for chart_name, services in services_by_chart.items():
            print(f"    - {chart_name}: {len(services)} services")

        # Validate that we have services for all expected charts
        expected_charts = set(service.get("chart_name") for service in expected_services)
        actual_charts = set(services_by_chart.keys())

        if not expected_charts.issubset(actual_charts):
            missing_charts = expected_charts - actual_charts
            self.errors.append(f"Missing charts: {missing_charts}")
            return False

        # Validate risk levels and exposure types for each chart
        for chart_name in expected_charts:
            chart_services = services_by_chart[chart_name]

            # Find expected service for this chart
            expected_service = next((s for s in expected_services if s.get("chart_name") == chart_name), None)
            if not expected_service:
                continue

            # Check that at least one service has the expected risk level and exposure type
            expected_risk = expected_service.get("risk_level")
            expected_exposure = expected_service.get("exposure_type")

            chart_has_correct_risk = False
            for service in chart_services:
                if (service.get("risk_level") == expected_risk and
                    expected_exposure in service.get("exposure_type", "")):
                    chart_has_correct_risk = True
                    break

            if not chart_has_correct_risk:
                self.errors.append(f"Chart {chart_name} missing correct risk level {expected_risk} with exposure type {expected_exposure}")
                return False

        # Validate service structure for all services
        required_service_fields = [
            "service_name", "chart_name", "risk_level", "exposure_type",
            "host", "dockerfile_path", "source_code_paths", "environment",
            "security_context", "service_account", "public_endpoints"
        ]

        for service in actual_services:
            for field in required_service_fields:
                if field not in service:
                    self.errors.append(f"Service {service.get('service_name', 'unknown')} missing required field: {field}")
                    return False

        print("  ✅ All charts have correct risk levels and exposure types")
        print("  ✅ All services have required fields")
        return True

    def validate_security_features(self, actual: List[Dict[str, Any]]) -> bool:
        """Validate security context and service account analysis."""
        print("\n🔒 Validating Security Features...")

        actual_services = actual["prioritized_services"]

        # Validate security context structure
        for service in actual_services:
            security_context = service["security_context"]

            # Check that security_context is a dict
            if not isinstance(security_context, dict):
                self.errors.append(f"Service {service['service_name']} has invalid security_context type")
                return False

            # Only validate fields if security_context is populated
            if security_context:
                required_sec_fields = [
                    "is_privileged", "allows_privilege_escalation", "runs_as_root",
                    "host_network", "read_only_root_filesystem", "capabilities"
                ]
                for field in required_sec_fields:
                    if field not in security_context:
                        self.errors.append(f"Service {service['service_name']} security_context missing field: {field}")
                        return False

        # Validate service account structure
        for service in actual_services:
            service_account = service["service_account"]

            # Check that service_account is a dict
            if not isinstance(service_account, dict):
                self.errors.append(f"Service {service['service_name']} has invalid service_account type")
                return False

            # Only validate fields if service_account is populated
            if service_account:
                required_sa_fields = [
                    "has_custom_sa", "cloud_role", "cloud_provider",
                    "risk_indicators", "automount_token"
                ]
                for field in required_sa_fields:
                    if field not in service_account:
                        self.errors.append(f"Service {service['service_name']} service_account missing field: {field}")
                        return False

        print("  ✅ Security context and service account structures are valid")
        return True

    def validate_public_endpoints(self, actual: List[Dict[str, Any]]) -> bool:
        """Validate public endpoints extraction."""
        print("\n🌐 Validating Public Endpoints...")

        actual_services = actual["prioritized_services"]

        # Find services with public endpoints
        services_with_endpoints = [
            s for s in actual_services if s["public_endpoints"] and len(s["public_endpoints"]) > 0
        ]

        # Should have at least one service with public endpoints
        if len(services_with_endpoints) == 0:
            self.errors.append("No services found with public endpoints")
            return False

        # Verify endpoint structure
        for service in services_with_endpoints:
            endpoints = service["public_endpoints"]
            if not isinstance(endpoints, list):
                self.errors.append(f"Service {service['service_name']} has invalid public_endpoints type")
                return False

            for endpoint in endpoints:
                if not isinstance(endpoint, str) or len(endpoint) == 0:
                    self.errors.append(f"Service {service['service_name']} has invalid endpoint: {endpoint}")
                    return False

        print(f"  ✅ Found {len(services_with_endpoints)} services with public endpoints")
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

        # Validate prioritization report structure
        if not self.validate_prioritization_report(actual_results):
            success = False

        # Validate prioritization summary
        if not self.validate_prioritization_summary(actual_results):
            success = False

        # Validate prioritized services
        if not self.validate_prioritized_services(actual_results):
            success = False

        # Validate security features
        if not self.validate_security_features(actual_results):
            success = False

        # Validate public endpoints
        if not self.validate_public_endpoints(actual_results):
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
    
    # Expected results based on test scenarios (prioritization format)
    expected_results = {
        "summary": {
            "total_services": 10,
            "high_risk": 5,
            "medium_risk": 2,
            "low_risk": 3
        },
        "prioritized_services": [
            {
                "service_name": "frontend-web-container",
                "chart_name": "frontend-web",
                "risk_level": "HIGH",
                "exposure_type": "nginx",
                "host": "frontend.example.com"
            },
            {
                "service_name": "api-gateway-container",
                "chart_name": "api-gateway",
                "risk_level": "HIGH",
                "exposure_type": "LoadBalancer/NodePort",
                "host": "Direct Internet Access"
            },
            {
                "service_name": "backend-service-container",
                "chart_name": "backend-service",
                "risk_level": "MEDIUM",
                "exposure_type": "Service Dependency",
                "host": "N/A"
            },
            {
                "service_name": "worker-service-container",
                "chart_name": "worker-service",
                "risk_level": "MEDIUM",
                "exposure_type": "Service Dependency",
                "host": "N/A"
            },
            {
                "service_name": "database-primary-container",
                "chart_name": "database-primary",
                "risk_level": "LOW",
                "exposure_type": "Internal",
                "host": "N/A"
            },
            {
                "service_name": "cache-service-container",
                "chart_name": "cache-service",
                "risk_level": "LOW",
                "exposure_type": "Internal",
                "host": "N/A"
            },
            {
                "service_name": "monitoring-stack-container",
                "chart_name": "monitoring-stack",
                "risk_level": "LOW",
                "exposure_type": "Internal",
                "host": "N/A"
            },
            {
                "service_name": "security-gateway-container",
                "chart_name": "security-gateway",
                "risk_level": "HIGH",
                "exposure_type": "LoadBalancer/NodePort",
                "host": "Direct Internet Access"
            },
            {
                "service_name": "load-balancer-container",
                "chart_name": "load-balancer",
                "risk_level": "HIGH",
                "exposure_type": "LoadBalancer/NodePort",
                "host": "Direct Internet Access"
            },
            {
                "service_name": "edge-cases-container",
                "chart_name": "edge-cases",
                "risk_level": "HIGH",
                "exposure_type": "Ingress",
                "host": "edge.example.com"
            }
        ]
    }
    
    # Run validation
    validator = ResultValidator(expected_results)
    success = validator.run_validation(actual_results)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
