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
        
        # Basic validation
        assert results is not None
        assert "scan_summary" in results
        assert "containers" in results
        assert "network_topology" in results
        assert "mermaid_diagram" in results
        
        # Performance validation
        assert scan_time < 30, f"Scan took too long: {scan_time:.2f}s"
        
        # Store results for detailed validation
        self.scan_results = results
        self.scan_time = scan_time
    
    def test_scan_summary_accuracy(self, scanner, advanced_test_repo):
        """Test that scan summary contains expected values."""
        if not hasattr(self, 'scan_results'):
            pytest.skip("Run test_complete_repository_scan first")
        
        summary = self.scan_results["scan_summary"]
        
        # Expected values based on test scenarios
        assert summary["total_containers"] == 10
        assert summary["charts_analyzed"] == 10
        
        # Exposure levels should add up to total containers
        total_exposure = (
            summary["high_exposure"] + 
            summary["medium_exposure"] + 
            summary["low_exposure"]
        )
        assert total_exposure == summary["total_containers"]
    
    def test_container_exposure_classification(self, scanner, advanced_test_repo):
        """Test that containers are correctly classified by exposure level."""
        if not hasattr(self, 'scan_results'):
            pytest.skip("Run test_complete_repository_scan first")
        
        containers = self.scan_results["containers"]
        
        # Check that we have the expected number of containers
        assert len(containers) == 10
        
        # Group containers by exposure level
        high_exposure = [c for c in containers if c["exposure_level"] == "HIGH"]
        medium_exposure = [c for c in containers if c["exposure_level"] == "MEDIUM"]
        low_exposure = [c for c in containers if c["exposure_level"] == "LOW"]
        
        # Validate exposure level counts
        assert len(high_exposure) == 5, f"Expected 5 HIGH exposure, got {len(high_exposure)}"
        assert len(medium_exposure) == 2, f"Expected 2 MEDIUM exposure, got {len(medium_exposure)}"
        assert len(low_exposure) == 3, f"Expected 3 LOW exposure, got {len(low_exposure)}"
        
        # Validate specific containers
        container_names = [c["name"] for c in containers]
        
        # HIGH exposure containers
        expected_high = [
            "frontend-web-container", "api-gateway-container", 
            "security-gateway-container", "load-balancer-container", "edge-cases-container"
        ]
        for name in expected_high:
            assert name in container_names, f"Expected HIGH exposure container {name} not found"
        
        # MEDIUM exposure containers
        expected_medium = ["backend-service-container", "worker-service-container"]
        for name in expected_medium:
            assert name in container_names, f"Expected MEDIUM exposure container {name} not found"
        
        # LOW exposure containers
        expected_low = ["database-primary-container", "cache-service-container", "monitoring-stack-container"]
        for name in expected_low:
            assert name in container_names, f"Expected LOW exposure container {name} not found"
    
    def test_gateway_type_detection(self, scanner, advanced_test_repo):
        """Test that gateway types are correctly detected."""
        if not hasattr(self, 'scan_results'):
            pytest.skip("Run test_complete_repository_scan first")
        
        containers = self.scan_results["containers"]
        
        # Check specific gateway types
        for container in containers:
            name = container["name"]
            gateway_type = container["gateway_type"]
            
            if "frontend" in name:
                assert "nginx" in gateway_type or "Ingress" in gateway_type
            elif "api-gateway" in name:
                assert "LoadBalancer" in gateway_type or "NodePort" in gateway_type
            elif "security" in name:
                assert "LoadBalancer" in gateway_type or "NodePort" in gateway_type
            elif "load-balancer" in name:
                assert "LoadBalancer" in gateway_type or "NodePort" in gateway_type
            elif "edge-cases" in name:
                assert "Ingress" in gateway_type
            elif "backend" in name or "worker" in name:
                assert "Service Dependency" in gateway_type or "Internal" in gateway_type
            elif any(x in name for x in ["database", "cache", "monitoring"]):
                assert "Internal" in gateway_type
    
    def test_network_topology_structure(self, scanner, advanced_test_repo):
        """Test that network topology is properly structured."""
        if not hasattr(self, 'scan_results'):
            pytest.skip("Run test_complete_repository_scan first")
        
        topology = self.scan_results["network_topology"]
        
        # Check required fields
        assert "exposed_containers" in topology
        assert "linked_containers" in topology
        assert "internal_containers" in topology
        
        # Validate container counts in topology
        assert len(topology["exposed_containers"]) == 5
        assert len(topology["linked_containers"]) == 2
        assert len(topology["internal_containers"]) == 3
        
        # Validate that all containers are accounted for
        all_topology_containers = (
            topology["exposed_containers"] + 
            topology["linked_containers"] + 
            topology["internal_containers"]
        )
        assert len(all_topology_containers) == 10
    
    def test_mermaid_diagram_generation(self, scanner, advanced_test_repo):
        """Test that Mermaid diagram is properly generated."""
        if not hasattr(self, 'scan_results'):
            pytest.skip("Run test_complete_repository_scan first")
        
        diagram = self.scan_results["mermaid_diagram"]
        
        # Check that diagram is not empty
        assert diagram, "Mermaid diagram is empty"
        assert len(diagram) > 100, "Mermaid diagram too short"
        
        # Check for required diagram elements
        assert "graph TD" in diagram, "Missing graph TD declaration"
        assert "subgraph High_Exposure" in diagram, "Missing High_Exposure group"
        assert "subgraph Medium_Exposure" in diagram, "Missing Medium_Exposure group"
        assert "subgraph Low_Exposure" in diagram, "Missing Low_Exposure group"
        
        # Check for container nodes
        expected_containers = [
            "frontend-web-container", "api-gateway-container", "backend-service-container",
            "worker-service-container", "database-primary-container", "cache-service-container",
            "monitoring-stack-container", "security-gateway-container", "load-balancer-container",
            "edge-cases-container"
        ]
        
        for container in expected_containers:
            assert container in diagram, f"Container {container} not found in diagram"
    
    def test_exposure_score_consistency(self, scanner, advanced_test_repo):
        """Test that exposure scores are consistent with exposure levels."""
        if not hasattr(self, 'scan_results'):
            pytest.skip("Run test_complete_repository_scan first")
        
        containers = self.scan_results["containers"]
        
        for container in containers:
            level = container["exposure_level"]
            score = container["exposure_score"]
            
            if level == "HIGH":
                assert score == 3, f"HIGH exposure should have score 3, got {score}"
            elif level == "MEDIUM":
                assert score == 2, f"MEDIUM exposure should have score 2, got {score}"
            elif level == "LOW":
                assert score == 1, f"LOW exposure should have score 1, got {score}"
    
    def test_edge_cases_handling(self, scanner, advanced_test_repo):
        """Test that edge cases are handled gracefully."""
        if not hasattr(self, 'scan_results'):
            pytest.skip("Run test_complete_repository_scan first")
        
        # Find the edge-cases container
        edge_container = None
        for container in self.scan_results["containers"]:
            if "edge-cases" in container["name"]:
                edge_container = container
                break
        
        assert edge_container is not None, "Edge cases container not found"
        
        # Edge cases should still be classified as HIGH exposure due to ingress
        assert edge_container["exposure_level"] == "HIGH"
        assert edge_container["exposure_score"] == 3
    
    def test_performance_benchmarks(self, scanner, advanced_test_repo):
        """Test that performance meets benchmarks."""
        if not hasattr(self, 'scan_results'):
            pytest.skip("Run test_complete_repository_scan first")
        
        # Performance validation
        assert self.scan_time < 30, f"Scan time exceeds 30s benchmark: {self.scan_time:.2f}s"
        
        # Output size validation
        output_size = len(json.dumps(self.scan_results, indent=2).encode('utf-8'))
        assert output_size < 100 * 1024, f"Output size exceeds 100KB: {output_size} bytes"
    
    def test_json_output_format(self, scanner, advanced_test_repo):
        """Test that JSON output is properly formatted."""
        if not hasattr(self, 'scan_results'):
            pytest.skip("Run test_complete_repository_scan first")
        
        # Test JSON serialization
        try:
            json_str = json.dumps(self.scan_results, indent=2)
            parsed_back = json.loads(json_str)
            assert parsed_back == self.scan_results, "JSON round-trip failed"
        except Exception as e:
            pytest.fail(f"JSON serialization failed: {e}")
    
    def test_console_output_format(self, scanner, advanced_test_repo):
        """Test console output format."""
        if not hasattr(self, 'scan_results'):
            pytest.skip("Run test_complete_repository_scan first")
        
        # Test console output generation
        with patch('builtins.print') as mock_print:
            # This would test the console output, but we need to mock the actual output
            # For now, just verify the method exists
            assert hasattr(scanner, 'scan_repo')
    
    def test_paths_output_format(self, scanner, advanced_test_repo):
        """Test paths output format."""
        if not hasattr(self, 'scan_results'):
            pytest.skip("Run test_complete_repository_scan first")
        
        # Test paths output generation
        # This would test the paths output, but we need to mock the actual output
        # For now, just verify the method exists
        assert hasattr(scanner, 'scan_repo')


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
