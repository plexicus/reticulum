"""Tests for the ExposureScanner class."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from reticulum import ExposureScanner


class TestExposureScanner:
    """Test cases for ExposureScanner."""
    
    def test_init(self):
        """Test ExposureScanner initialization."""
        scanner = ExposureScanner()
        
        assert scanner.results["repo_path"] == ""
        assert scanner.results["scan_summary"] == {}
        assert scanner.results["containers"] == []
        assert scanner.results["master_paths"] == {}
        assert scanner.results["network_topology"] == {}
        assert scanner.results["mermaid_diagram"] == ""
        
        # Check that analyzers are initialized
        assert hasattr(scanner, 'exposure_analyzer')
        assert hasattr(scanner, 'dockerfile_analyzer')
        assert hasattr(scanner, 'dependency_analyzer')
        assert hasattr(scanner, 'path_consolidator')
        assert hasattr(scanner, 'mermaid_builder')
    
    def test_scan_repo_not_found(self):
        """Test scanning a non-existent repository."""
        scanner = ExposureScanner()
        
        with pytest.raises(FileNotFoundError):
            scanner.scan_repo("/non/existent/path")
    
    @patch('pathlib.Path.glob')
    def test_scan_repo_no_charts(self, mock_glob):
        """Test scanning a repository with no Helm charts."""
        mock_glob.return_value = []  # No Chart.yaml files
        
        scanner = ExposureScanner()
        results = scanner.scan_repo("/tmp")
        
        assert results["scan_summary"]["error"] == "No Helm charts found in repository"
    
    def test_build_summary(self):
        """Test summary building with sample containers."""
        scanner = ExposureScanner()
        
        # Add sample containers
        scanner.results["containers"] = [
            {"exposure_level": "HIGH", "chart": "chart1"},
            {"exposure_level": "MEDIUM", "chart": "chart2"},
            {"exposure_level": "LOW", "chart": "chart3"},
            {"exposure_level": "HIGH", "chart": "chart1"},
            {"exposure_level": "LOW", "chart": "test-chart"}
        ]
        
        scanner._build_summary()
        
        summary = scanner.results["scan_summary"]
        assert summary["total_containers"] == 5
        assert summary["high_exposure"] == 2
        assert summary["medium_exposure"] == 1
        assert summary["low_exposure"] == 2
        assert summary["charts_analyzed"] == 4
    
    def test_build_network_topology(self):
        """Test network topology building."""
        scanner = ExposureScanner()
        
        # Add sample containers
        scanner.results["containers"] = [
            {"name": "high1", "exposure_level": "HIGH"},
            {"name": "high2", "exposure_level": "HIGH"},
            {"name": "medium1", "exposure_level": "MEDIUM"},
            {"name": "low1", "exposure_level": "LOW"},
        ]
        
        scanner._build_network_topology()
        
        topology = scanner.results["network_topology"]
        assert "high1" in topology["exposed_containers"]
        assert "high2" in topology["exposed_containers"]
        assert "medium1" in topology["linked_containers"]
        assert "low1" in topology["internal_containers"]


class TestExposureAnalyzer:
    """Test cases for ExposureAnalyzer."""
    
    def test_create_container_info(self):
        """Test container info creation."""
        from reticulum.exposure_analyzer import ExposureAnalyzer
        
        analyzer = ExposureAnalyzer()
        
        container_info = analyzer._create_container_info(
            chart_name="test-chart",
            gateway_type="Ingress",
            host="test.example.com",
            chart_dir=Path("/tmp"),
            repo_path=Path("/tmp"),
            score=3,
            level="HIGH",
            env_name="prod"
        )
        
        assert container_info["name"] == "test-chart-prod-container"
        assert container_info["chart"] == "test-chart"
        assert container_info["environment"] == "prod"
        assert container_info["gateway_type"] == "Ingress"
        assert container_info["host"] == "test.example.com"
        assert container_info["exposure_score"] == 3
        assert container_info["exposure_level"] == "HIGH"
        assert "test-chart" in container_info["access_chain"]


class TestDockerfileAnalyzer:
    """Test cases for DockerfileAnalyzer."""
    
    def test_consolidate_source_paths(self):
        """Test source path consolidation."""
        from reticulum.dockerfile_analyzer import DockerfileAnalyzer
        
        analyzer = DockerfileAnalyzer()
        
        # Test with "." in paths (special case - returns only "./")
        raw_paths = [".", "src", "src/app", "src/utils", "config"]
        consolidated = analyzer._consolidate_source_paths(raw_paths, Path("/tmp"))
        assert consolidated == ["./"]  # When "." is present, only return "./"
        
        # Test without "." in paths
        raw_paths_no_dot = ["src", "src/app", "src/utils", "config"]
        consolidated_no_dot = analyzer._consolidate_source_paths(raw_paths_no_dot, Path("/tmp"))
        assert "src/" in consolidated_no_dot
        assert "config/" in consolidated_no_dot


class TestPathConsolidator:
    """Test cases for PathConsolidator."""
    
    def test_get_highest_exposure_level(self):
        """Test exposure level determination."""
        from reticulum.path_consolidator import PathConsolidator
        
        consolidator = PathConsolidator()
        
        # Test priority: HIGH > MEDIUM > LOW
        containers = [
            {"exposure_level": "LOW"},
            {"exposure_level": "MEDIUM"},
            {"exposure_level": "LOW"}
        ]
        
        highest = consolidator._get_highest_exposure_level(containers)
        assert highest == "MEDIUM"
        
        # Test HIGH priority
        containers.append({"exposure_level": "HIGH"})
        highest = consolidator._get_highest_exposure_level(containers)
        assert highest == "HIGH"
    
    def test_find_most_exposed_container(self):
        """Test finding most exposed container."""
        from reticulum.path_consolidator import PathConsolidator
        
        consolidator = PathConsolidator()
        
        containers = [
            {"name": "low", "exposure_score": 1},
            {"name": "high", "exposure_score": 3},
            {"name": "medium", "exposure_score": 2}
        ]
        
        most_exposed = consolidator._find_most_exposed_container(containers)
        assert most_exposed["name"] == "high"
        assert most_exposed["exposure_score"] == 3


class TestMermaidBuilder:
    """Test cases for MermaidBuilder."""
    
    def test_build_diagram_empty(self):
        """Test Mermaid diagram building with no containers."""
        from reticulum.mermaid_builder import MermaidBuilder
        
        builder = MermaidBuilder()
        
        diagram = builder.build_diagram([])
        assert "No containers found" in diagram
        assert "graph TD" in diagram
    
    def test_build_diagram_with_containers(self):
        """Test Mermaid diagram building with containers."""
        from reticulum.mermaid_builder import MermaidBuilder
        
        builder = MermaidBuilder()
        
        containers = [
            {"name": "high1", "exposure_level": "HIGH"},
            {"name": "medium1", "exposure_level": "MEDIUM", "exposed_by": ["high1"]},
            {"name": "low1", "exposure_level": "LOW"}
        ]
        
        diagram = builder.build_diagram(containers)
        assert "graph TD" in diagram
        assert "Internet" in diagram
        assert "high1" in diagram
        assert "medium1" in diagram
        assert "low1" in diagram
        assert "subgraph Exposure_Levels" in diagram
