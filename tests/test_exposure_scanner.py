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
        assert scanner.results["dot_diagram"] == ""
        
        # Check that analyzers are initialized
        assert hasattr(scanner, 'exposure_analyzer')
        assert hasattr(scanner, 'dockerfile_analyzer')
        assert hasattr(scanner, 'dependency_analyzer')
        assert hasattr(scanner, 'path_consolidator')
        assert hasattr(scanner, 'dot_builder')
    
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

    def test_analyze_service_account(self):
        """Test service account analysis."""
        from reticulum.exposure_analyzer import ExposureAnalyzer

        analyzer = ExposureAnalyzer()

        # Test with no service account
        values_no_sa = {}
        sa_info = analyzer._analyze_service_account(values_no_sa)
        assert sa_info["has_custom_sa"] == False
        assert sa_info["cloud_role"] is None
        assert sa_info["cloud_provider"] is None
        assert sa_info["risk_indicators"] == []
        assert sa_info["automount_token"] == False

        # Test with custom service account
        values_custom_sa = {
            "serviceAccount": {
                "create": True,
                "name": "custom-sa",
                "automountServiceAccountToken": False
            }
        }
        sa_info = analyzer._analyze_service_account(values_custom_sa)
        assert sa_info["has_custom_sa"] == True
        assert sa_info["automount_token"] == False

        # Test with AWS IAM role
        values_aws = {
            "serviceAccount": {
                "create": True,
                "annotations": {
                    "eks.amazonaws.com/role-arn": "arn:aws:iam::123456789012:role/test-role"
                }
            }
        }
        sa_info = analyzer._analyze_service_account(values_aws)
        assert sa_info["has_custom_sa"] == True
        assert sa_info["cloud_role"] == "arn:aws:iam::123456789012:role/test-role"
        assert sa_info["cloud_provider"] == "aws"
        assert "aws_iam_binding" in sa_info["risk_indicators"]

        # Test with GCP workload identity
        values_gcp = {
            "serviceAccount": {
                "annotations": {
                    "iam.gke.io/gcp-service-account": "test-service@project.iam.gserviceaccount.com"
                }
            }
        }
        sa_info = analyzer._analyze_service_account(values_gcp)
        assert sa_info["cloud_role"] == "test-service@project.iam.gserviceaccount.com"
        assert sa_info["cloud_provider"] == "gcp"
        assert "gcp_workload_identity" in sa_info["risk_indicators"]

        # Test with Azure workload identity
        values_azure = {
            "serviceAccount": {
                "annotations": {
                    "azure.workload.identity/client-id": "12345678-1234-1234-1234-123456789012"
                }
            }
        }
        sa_info = analyzer._analyze_service_account(values_azure)
        assert sa_info["cloud_role"] == "12345678-1234-1234-1234-123456789012"
        assert sa_info["cloud_provider"] == "azure"
        assert "azure_workload_identity" in sa_info["risk_indicators"]

    def test_analyze_capabilities(self):
        """Test Linux capabilities analysis."""
        from reticulum.exposure_analyzer import ExposureAnalyzer

        analyzer = ExposureAnalyzer()

        # Test with no security context
        values_no_sec = {}
        caps_info = analyzer._analyze_capabilities(values_no_sec)
        assert caps_info["added"] == []
        assert caps_info["dropped"] == []
        assert caps_info["risk_level"] == "low"

        # Test with dangerous capabilities
        values_dangerous = {
            "securityContext": {
                "capabilities": {
                    "add": ["SYS_ADMIN", "NET_ADMIN", "NET_RAW", "SYS_PTRACE"]
                }
            }
        }
        caps_info = analyzer._analyze_capabilities(values_dangerous)
        assert len(caps_info["added"]) == 4

        # Check that dangerous capabilities are detected with correct risk levels
        added_caps = {cap["capability"]: cap["risk"] for cap in caps_info["added"]}
        assert added_caps["SYS_ADMIN"] == "critical"
        assert added_caps["NET_ADMIN"] == "critical"
        assert added_caps["NET_RAW"] == "high"
        assert added_caps["SYS_PTRACE"] == "high"

    def test_analyze_security_context(self):
        """Test security context analysis."""
        from reticulum.exposure_analyzer import ExposureAnalyzer

        analyzer = ExposureAnalyzer()

        # Test with no security context
        values_no_sec = {}
        sec_info = analyzer._analyze_security_context(values_no_sec)
        assert sec_info["is_privileged"] == False
        assert sec_info["allows_privilege_escalation"] == False
        assert sec_info["runs_as_root"] == False
        assert sec_info["host_network"] == False
        assert sec_info["read_only_root_filesystem"] == True

        # Test with dangerous security context
        values_dangerous = {
            "securityContext": {
                "privileged": True,
                "allowPrivilegeEscalation": True,
                "runAsUser": 0,
                "readOnlyRootFilesystem": False
            },
            "hostNetwork": True
        }
        sec_info = analyzer._analyze_security_context(values_dangerous)
        assert sec_info["is_privileged"] == True
        assert sec_info["allows_privilege_escalation"] == True
        assert sec_info["runs_as_root"] == True
        assert sec_info["host_network"] == True
        assert sec_info["read_only_root_filesystem"] == False

        # Test capabilities integration
        assert "capabilities" in sec_info

    def test_extract_public_endpoints(self):
        """Test public endpoints extraction."""
        from reticulum.exposure_analyzer import ExposureAnalyzer

        analyzer = ExposureAnalyzer()

        # Test with no exposes
        container_no_exposes = {"exposes": []}
        endpoints = analyzer._extract_public_endpoints(container_no_exposes)
        assert endpoints == []

        # Test with endpoint exposes
        container_with_endpoints = {
            "exposes": [
                {"type": "endpoint", "value": "example.com/api"},
                {"type": "endpoint", "value": "app.example.com/dashboard"},
                {"type": "port", "value": 8080},  # Should be ignored
                {"type": "endpoint", "value": "api.example.com/v1"}
            ]
        }
        endpoints = analyzer._extract_public_endpoints(container_with_endpoints)
        assert len(endpoints) == 3
        assert "example.com/api" in endpoints
        assert "app.example.com/dashboard" in endpoints
        assert "api.example.com/v1" in endpoints
        assert 8080 not in endpoints  # Ports should not be included

    def test_prioritization_report_includes_new_features(self):
        """Test that prioritization report includes all new security features."""
        from reticulum.main import ExposureScanner

        scanner = ExposureScanner()

        # Mock containers with security features
        scanner.results["containers"] = [
            {
                "name": "test-container",
                "chart": "test-chart",
                "exposure_level": "HIGH",
                "gateway_type": "Ingress",
                "host": "example.com",
                "dockerfile_path": "",
                "source_code_path": [],
                "environment": "base",
                "security_context": {
                    "is_privileged": False,
                    "allows_privilege_escalation": True,
                    "runs_as_root": False,
                    "host_network": False,
                    "read_only_root_filesystem": True,
                    "capabilities": {
                        "added": [{"capability": "NET_ADMIN", "risk": "critical"}],
                        "dropped": [],
                        "risk_level": "low"
                    }
                },
                "service_account": {
                    "has_custom_sa": True,
                    "cloud_role": "arn:aws:iam::123456789012:role/test-role",
                    "cloud_provider": "aws",
                    "risk_indicators": ["aws_iam_binding"],
                    "automount_token": False
                },
                "exposes": [
                    {"type": "endpoint", "value": "example.com/api"}
                ]
            }
        ]

        report = scanner._build_prioritization_report()

        # Check that all new features are included in the report
        service_info = report["prioritized_services"][0]
        assert service_info["service_name"] == "test-container"
        assert service_info["risk_level"] == "HIGH"

        # Check security context
        assert "security_context" in service_info
        assert service_info["security_context"]["allows_privilege_escalation"] == True
        assert "capabilities" in service_info["security_context"]

        # Check service account
        assert "service_account" in service_info
        assert service_info["service_account"]["has_custom_sa"] == True
        assert service_info["service_account"]["cloud_provider"] == "aws"

        # Check public endpoints
        assert "public_endpoints" in service_info
        assert "example.com/api" in service_info["public_endpoints"]


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

    def test_cli_dot_export(self, tmp_path):
        """Test CLI DOT file export functionality."""
        from reticulum.cli import create_parser
        from reticulum.main import ExposureScanner
        from unittest.mock import patch

        # Create a temporary repository with a simple chart
        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()
        chart_dir = repo_path / "test-chart"
        chart_dir.mkdir()

        # Create Chart.yaml
        (chart_dir / "Chart.yaml").write_text("""
apiVersion: v2
name: test-chart
description: Test chart
version: 0.1.0
""")

        # Create values.yaml with exposure
        (chart_dir / "values.yaml").write_text("""
ingress:
  enabled: true
  hosts:
    - host: "test.example.com"
      paths:
        - path: "/"
          pathType: "Prefix"
""")

        # Test DOT export
        dot_file = tmp_path / "test.dot"

        # Mock the CLI execution
        with patch('sys.argv', ['reticulum', str(repo_path), '--dot', str(dot_file)]):
            parser = create_parser()
            args = parser.parse_args()

            scanner = ExposureScanner()
            results = scanner.scan_repo(args.repository_path)

            # Simulate DOT export
            from reticulum.dot_builder import DOTBuilder
            dot_builder = DOTBuilder()
            dot_builder.save_dot_file(results["containers"], str(dot_file))

        # Verify DOT file was created
        assert dot_file.exists()
        content = dot_file.read_text()
        assert "digraph G" in content
        assert "test-chart" in content


class TestDOTBuilder:
    """Test cases for DOTBuilder."""

    def test_build_diagram_empty(self):
        """Test DOT diagram building with no containers."""
        from reticulum.dot_builder import DOTBuilder

        builder = DOTBuilder()

        diagram = builder.build_diagram([])
        assert "No containers found" in diagram
        assert "digraph G" in diagram

    def test_build_diagram_with_containers(self):
        """Test DOT diagram building with containers."""
        from reticulum.dot_builder import DOTBuilder

        builder = DOTBuilder()

        containers = [
            {"name": "high1", "exposure_level": "HIGH", "gateway_type": "Ingress"},
            {"name": "medium1", "exposure_level": "MEDIUM", "exposed_by": ["high1"]},
            {"name": "low1", "exposure_level": "LOW"}
        ]

        diagram = builder.build_diagram(containers)
        assert "digraph G" in diagram
        assert "Internet" in diagram
        assert "high1" in diagram
        assert "medium1" in diagram
        assert "low1" in diagram
        assert "subgraph cluster_high" in diagram
        assert "subgraph cluster_medium" in diagram
        assert "subgraph cluster_low" in diagram

    def test_sanitize_node_name(self):
        """Test node name sanitization for DOT format."""
        from reticulum.dot_builder import DOTBuilder

        builder = DOTBuilder()

        # Test various problematic names
        assert builder._sanitize_node_name("test-container") == "test_container"
        assert builder._sanitize_node_name("test container") == "test_container"
        assert builder._sanitize_node_name("test.container") == "test_container"
        assert builder._sanitize_node_name("123container") == "node_123container"

    def test_save_dot_file(self, tmp_path):
        """Test saving DOT diagram to file."""
        from reticulum.dot_builder import DOTBuilder

        builder = DOTBuilder()

        containers = [
            {"name": "test-container", "exposure_level": "HIGH", "gateway_type": "Ingress"}
        ]

        file_path = tmp_path / "test.dot"
        builder.save_dot_file(containers, str(file_path))

        assert file_path.exists()
        content = file_path.read_text()
        assert "digraph G" in content
        assert "test_container" in content
