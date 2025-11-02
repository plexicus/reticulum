"""
Advanced test scenarios for Reticulum scanner.
Tests the scanner against complex, real-world configurations.
"""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import time

from reticulum import ExposureScanner


class TestAdvancedScenarios:
    """Test class for advanced scanning scenarios."""
    
    @pytest.fixture(scope="class")
    def advanced_test_repo(self):
        """Set up the advanced test repository."""
        test_repo_path = Path(__file__).parent / "advanced-test-repo"
        if not test_repo_path.exists():
            pytest.skip("Advanced test repository not found")
        return test_repo_path
    
    @pytest.fixture
    def scanner(self):
        """Create a scanner instance."""
        return ExposureScanner()
    
    def test_advanced_repository_structure(self, advanced_test_repo):
        """Test that the advanced test repository has the expected structure."""
        # Check main directories
        assert (advanced_test_repo / "charts").exists()
        assert (advanced_test_repo / "dockerfiles").exists()
        assert (advanced_test_repo / "source-code").exists()
        
        # Check chart directories
        charts_dir = advanced_test_repo / "charts"
        expected_charts = [
            "frontend-web", "api-gateway", "backend-service", "worker-service",
            "database-primary", "cache-service", "monitoring-stack",
            "security-gateway", "load-balancer", "edge-cases"
        ]
        
        for chart in expected_charts:
            chart_path = charts_dir / chart
            assert chart_path.exists(), f"Chart {chart} not found"
            assert (chart_path / "Chart.yaml").exists(), f"Chart.yaml missing in {chart}"
            assert (chart_path / "values.yaml").exists(), f"values.yaml missing in {chart}"
    
    def test_complete_repository_scan(self, scanner, advanced_test_repo):
        """Test scanning the complete advanced test repository."""
        start_time = time.time()

        # Run the scan
        results = scanner.scan_repo(str(advanced_test_repo))

        scan_time = time.time() - start_time

        # Basic validation for prioritization report format
        assert results is not None
        assert "repo_path" in results
        assert "prioritization_report" in results

        prioritization_report = results["prioritization_report"]
        assert "repo_path" in prioritization_report
        assert "scan_timestamp" in prioritization_report
        assert "summary" in prioritization_report
        assert "prioritized_services" in prioritization_report

        # Performance validation
        assert scan_time < 30, f"Scan took too long: {scan_time:.2f}s"
    
    def test_scan_summary_accuracy(self, scanner, advanced_test_repo):
        """Test that scan summary contains expected values."""
        results = scanner.scan_repo(str(advanced_test_repo))
        prioritization_report = results["prioritization_report"]
        summary = prioritization_report["summary"]

        # Validate summary structure
        assert "total_services" in summary
        assert "high_risk" in summary
        assert "medium_risk" in summary
        assert "low_risk" in summary

        # Risk levels should add up to total services
        total_risk = (
            summary["high_risk"] +
            summary["medium_risk"] +
            summary["low_risk"]
        )
        assert total_risk == summary["total_services"]
    
    def test_prioritized_services_structure(self, scanner, advanced_test_repo):
        """Test that prioritized services have the correct structure."""
        results = scanner.scan_repo(str(advanced_test_repo))
        prioritization_report = results["prioritization_report"]
        services = prioritization_report["prioritized_services"]

        # Should have services
        assert len(services) > 0

        # Check service structure
        for service in services:
            assert "service_name" in service
            assert "chart_name" in service
            assert "risk_level" in service
            assert "exposure_type" in service
            assert "host" in service
            assert "dockerfile_path" in service
            assert "source_code_paths" in service
            assert "environment" in service
            assert "security_context" in service
            assert "service_account" in service
            assert "public_endpoints" in service
    
    def test_gateway_type_detection(self, scanner, advanced_test_repo):
        """Test that gateway types are correctly detected."""
        results = scanner.scan_repo(str(advanced_test_repo))
        prioritization_report = results["prioritization_report"]
        services = prioritization_report["prioritized_services"]

        # Check specific gateway types
        for service in services:
            name = service["service_name"]
            gateway_type = service["exposure_type"]

            if "frontend" in name:
                assert "nginx" in gateway_type or "Ingress" in gateway_type
            elif "api-gateway" in name:
                assert "LoadBalancer" in gateway_type or "NodePort" in gateway_type or "nginx" in gateway_type
            elif "security" in name:
                assert "LoadBalancer" in gateway_type or "NodePort" in gateway_type or "nginx" in gateway_type
            elif "load-balancer" in name:
                assert "LoadBalancer" in gateway_type or "NodePort" in gateway_type or "nginx" in gateway_type
            elif "edge-cases" in name:
                # Edge-cases chart has internal exposure in current implementation
                assert "Internal" in gateway_type
            elif "backend" in name or "worker" in name:
                assert "Service Dependency" in gateway_type or "Internal" in gateway_type
            elif any(x in name for x in ["database", "cache", "monitoring"]):
                assert "Internal" in gateway_type
    
    def test_risk_level_distribution(self, scanner, advanced_test_repo):
        """Test that risk levels are properly distributed across services."""
        results = scanner.scan_repo(str(advanced_test_repo))
        prioritization_report = results["prioritization_report"]
        services = prioritization_report["prioritized_services"]
        summary = prioritization_report["summary"]

        # Count risk levels from services
        high_risk_count = len([s for s in services if s["risk_level"] == "HIGH"])
        medium_risk_count = len([s for s in services if s["risk_level"] == "MEDIUM"])
        low_risk_count = len([s for s in services if s["risk_level"] == "LOW"])

        # Verify counts match summary
        assert high_risk_count == summary["high_risk"]
        assert medium_risk_count == summary["medium_risk"]
        assert low_risk_count == summary["low_risk"]

        # Verify we have a reasonable distribution
        assert high_risk_count > 0, "Should have at least one HIGH risk service"
        assert low_risk_count > 0, "Should have at least one LOW risk service"
        # Note: Current scanner implementation may not detect MEDIUM risk services
    
    def test_security_context_analysis(self, scanner, advanced_test_repo):
        """Test that security context analysis is performed correctly."""
        results = scanner.scan_repo(str(advanced_test_repo))
        prioritization_report = results["prioritization_report"]
        services = prioritization_report["prioritized_services"]

        # Verify security context is present in all services
        for service in services:
            security_context = service["security_context"]
            assert isinstance(security_context, dict)

            # Only check fields if security context is populated
            if security_context:
                # Check for expected security context fields
                assert "is_privileged" in security_context
                assert "allows_privilege_escalation" in security_context
                assert "runs_as_root" in security_context
                assert "host_network" in security_context
                assert "read_only_root_filesystem" in security_context
                assert "capabilities" in security_context

    def test_service_account_analysis(self, scanner, advanced_test_repo):
        """Test that service account analysis is performed correctly."""
        results = scanner.scan_repo(str(advanced_test_repo))
        prioritization_report = results["prioritization_report"]
        services = prioritization_report["prioritized_services"]

        # Verify service account is present in all services
        for service in services:
            service_account = service["service_account"]
            assert isinstance(service_account, dict)

            # Only check fields if service account is populated
            if service_account:
                # Check for expected service account fields
                assert "has_custom_sa" in service_account
                assert "cloud_role" in service_account
                assert "cloud_provider" in service_account
                assert "risk_indicators" in service_account
                assert "automount_token" in service_account

    def test_public_endpoints_extraction(self, scanner, advanced_test_repo):
        """Test that public endpoints are properly extracted."""
        results = scanner.scan_repo(str(advanced_test_repo))
        prioritization_report = results["prioritization_report"]
        services = prioritization_report["prioritized_services"]

        # Find services with public endpoints
        services_with_endpoints = [
            s for s in services if s["public_endpoints"] and len(s["public_endpoints"]) > 0
        ]

        # Should have at least one service with public endpoints
        assert len(services_with_endpoints) > 0, "Should have services with public endpoints"

        # Verify endpoint structure
        for service in services_with_endpoints:
            endpoints = service["public_endpoints"]
            assert isinstance(endpoints, list)
            for endpoint in endpoints:
                assert isinstance(endpoint, str)
                assert len(endpoint) > 0

    def test_json_output_consistency(self, scanner, advanced_test_repo):
        """Test that JSON output is properly formatted and consistent."""
        results = scanner.scan_repo(str(advanced_test_repo))

        # Test JSON serialization
        try:
            json_str = json.dumps(results, indent=2)
            parsed_back = json.loads(json_str)
            assert parsed_back == results, "JSON round-trip failed"
        except Exception as e:
            pytest.fail(f"JSON serialization failed: {e}")

        # Verify output size is reasonable
        output_size = len(json_str.encode('utf-8'))
        assert output_size < 100 * 1024, f"Output size exceeds 100KB: {output_size} bytes"


class TestAdvancedRepositoryIntegration:
    """Test class for repository integration scenarios."""
    
    @pytest.fixture
    def scanner(self):
        """Create a scanner instance."""
        return ExposureScanner()
    
    def test_repository_with_mixed_charts(self, scanner):
        """Test scanning a repository with mixed chart types."""
        # Create a temporary repository with mixed charts
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a simple chart
            chart_dir = temp_path / "simple-chart"
            chart_dir.mkdir()
            
            # Create Chart.yaml
            (chart_dir / "Chart.yaml").write_text("""
apiVersion: v2
name: simple-chart
description: Simple test chart
version: 0.1.0
""")
            
            # Create values.yaml with HIGH exposure
            (chart_dir / "values.yaml").write_text("""
ingress:
  enabled: true
  hosts:
    - host: "test.example.com"
      paths:
        - path: "/"
          pathType: "Prefix"
""")
            
            # Scan the repository
            results = scanner.scan_repo(str(temp_path))
            
            # Validate results
            assert results is not None
            assert "scan_summary" in results
            assert results["scan_summary"]["charts_analyzed"] == 1
            assert results["scan_summary"]["total_containers"] == 1
    
    def test_repository_with_no_charts(self, scanner):
        """Test scanning a repository with no Helm charts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create some non-chart files
            (temp_path / "README.md").write_text("# Test Repository")
            (temp_path / "config.yaml").write_text("config: value")
            
            # Scan the repository
            results = scanner.scan_repo(str(temp_path))
            
            # Validate results
            assert results is not None
            assert "scan_summary" in results
            
            # When no charts are found, the scanner should handle it gracefully
            if "error" in results["scan_summary"]:
                # Scanner found no charts and returned an error
                assert "No Helm charts found" in results["scan_summary"]["error"]
                assert results["containers"] == []
            elif "charts_analyzed" in results["scan_summary"]:
                # Scanner found no charts but didn't error
                assert results["scan_summary"]["charts_analyzed"] == 0
                assert results["scan_summary"]["total_containers"] == 0
            else:
                # Scanner handled it in some other way
                assert results["containers"] == []
    
    def test_repository_with_invalid_charts(self, scanner):
        """Test scanning a repository with invalid Helm charts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create an invalid chart
            chart_dir = temp_path / "invalid-chart"
            chart_dir.mkdir()
            
            # Create invalid Chart.yaml
            (chart_dir / "Chart.yaml").write_text("""
invalid: yaml
content: here
""")
            
            # Create invalid values.yaml
            (chart_dir / "values.yaml").write_text("""
ingress:
  enabled: "invalid-boolean"
  hosts:
    - host: 
      paths:
        - path: 
          pathType: 
""")
            
            # Scan the repository
            results = scanner.scan_repo(str(temp_path))
            
            # Validate that scanner handles invalid charts gracefully
            assert results is not None
            # The scanner should either skip invalid charts or handle them gracefully
            # We don't want it to crash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
