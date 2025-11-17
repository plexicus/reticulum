"""
Integration tests for Security Scanner functionality.
"""

import json
import tempfile
import os
from pathlib import Path
import pytest

from reticulum.security_scanner import SecurityScanner
from reticulum.findings_mapper import FindingsMapper
from reticulum.enhanced_prioritizer import EnhancedPrioritizer


class TestSecurityScanner:
    """Test security scanner integration."""

    def test_security_scanner_initialization(self):
        """Test that security scanner initializes correctly."""
        scanner = SecurityScanner()
        assert scanner is not None
        assert scanner.docker_runner is not None
        assert scanner.enhanced_prioritizer is not None

    def test_enhanced_prioritizer_logic(self):
        """Test enhanced prioritization logic."""
        prioritizer = EnhancedPrioritizer()

        # Test priority calculation
        assert prioritizer._calculate_enhanced_priority("HIGH", 10.0) == "HIGH"
        assert prioritizer._calculate_enhanced_priority("HIGH", 0.0) == "HIGH"
        assert prioritizer._calculate_enhanced_priority("MEDIUM", 15.0) == "HIGH"
        assert prioritizer._calculate_enhanced_priority("LOW", 20.0) == "LOW"  # LOW exposure weight is too low to reach MEDIUM
        assert prioritizer._calculate_enhanced_priority("LOW", 0.0) == "LOW"

    def test_findings_mapper_initialization(self):
        """Test findings mapper initialization."""
        mock_report = {
            "prioritized_services": [
                {
                    "service_name": "test-service",
                    "chart_name": "test-chart",
                    "dockerfile_path": "charts/test-chart/Dockerfile",
                    "source_code_paths": ["src/"]
                }
            ]
        }

        mapper = FindingsMapper(mock_report, "/tmp/test-repo")
        assert mapper is not None
        assert "charts/test-chart/Dockerfile" in mapper.services_by_path
        assert "src/" in mapper.services_by_path

    def test_mock_trivy_sarif_parsing(self):
        """Test parsing of mock Trivy SARIF data."""
        mock_trivy_sarif = {
            "runs": [
                {
                    "results": [
                        {
                            "level": "error",
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {
                                            "uri": "charts/test-chart/Dockerfile"
                                        }
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        mock_report = {
            "prioritized_services": [
                {
                    "service_name": "test-service",
                    "chart_name": "test-chart",
                    "dockerfile_path": "charts/test-chart/Dockerfile",
                    "source_code_paths": ["src/"]
                }
            ]
        }

        mapper = FindingsMapper(mock_report, "/tmp/test-repo")
        mapping = mapper.map_trivy_findings(mock_trivy_sarif)

        assert mapping["summary"]["total_findings"] == 1
        assert mapping["summary"]["mapped_findings"] == 1
        assert "test-service" in mapping["services"]

    def test_priority_modification_logic(self):
        """Test that priorities are modified correctly based on findings."""
        prioritizer = EnhancedPrioritizer()

        mock_report = {
            "prioritized_services": [
                {
                    "service_name": "high-exposure-service",
                    "risk_level": "HIGH",
                    "chart_name": "test-chart",
                    "dockerfile_path": "charts/test-chart/Dockerfile"
                },
                {
                    "service_name": "low-exposure-service",
                    "risk_level": "LOW",
                    "chart_name": "test-chart2",
                    "dockerfile_path": "charts/test-chart2/Dockerfile"
                }
            ]
        }

        mock_trivy_mapping = {
            "services": {
                "high-exposure-service": {
                    "service_info": {
                        "service_name": "high-exposure-service",
                        "risk_level": "HIGH"
                    },
                    "trivy_findings": [
                        {"level": "error"},
                        {"level": "warning"}
                    ]
                }
            },
            "summary": {"total_findings": 2, "mapped_findings": 2, "unmapped_findings": 0}
        }

        mock_semgrep_mapping = {
            "services": {
                "high-exposure-service": {
                    "service_info": {
                        "service_name": "high-exposure-service",
                        "risk_level": "HIGH"
                    },
                    "semgrep_findings": [
                        {"level": "warning"}
                    ]
                }
            },
            "summary": {"total_findings": 1, "mapped_findings": 1, "unmapped_findings": 0}
        }

        enhanced_report = prioritizer.enhance_prioritization(
            mock_report, mock_trivy_mapping, mock_semgrep_mapping
        )

        assert "enhanced_summary" in enhanced_report
        assert "prioritized_services" in enhanced_report

        # Check that high-exposure service with findings remains HIGH
        high_service = next(
            s for s in enhanced_report["prioritized_services"]
            if s["service_name"] == "high-exposure-service"
        )
        assert high_service["enhanced_risk_level"] == "HIGH"
        assert high_service["security_risk_score"] > 0

        # Check that low-exposure service without findings remains LOW
        low_service = next(
            s for s in enhanced_report["prioritized_services"]
            if s["service_name"] == "low-exposure-service"
        )
        assert low_service["enhanced_risk_level"] == "LOW"


class TestSecurityScannerIntegration:
    """Integration tests for the complete security scanner workflow."""

    def test_security_scanner_with_mock_data(self):
        """Test security scanner with mock repository data."""
        # Create a temporary test repository
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Create minimal Helm chart structure
            chart_dir = repo_path / "charts" / "test-service"
            chart_dir.mkdir(parents=True)

            # Create Chart.yaml
            (chart_dir / "Chart.yaml").write_text("""
apiVersion: v2
name: test-service
description: Test service for security scanning
version: 0.1.0
""")

            # Create values.yaml
            (chart_dir / "values.yaml").write_text("""
service:
  type: ClusterIP
  port: 8080

image:
  repository: nginx
  tag: latest
""")

            # Create Dockerfile
            (chart_dir / "Dockerfile").write_text("""
FROM nginx:latest
COPY . /app
WORKDIR /app
""")

            # Test that security scanner can be initialized with this repo
            scanner = SecurityScanner()

            # Note: We don't actually run the full scan in tests since it requires
            # Docker and external tools, but we verify the components work
            assert scanner is not None

    def test_cli_command_structure(self):
        """Test that CLI commands are properly structured."""
        # Import the CLI module to verify it loads without errors
        from reticulum import cli
        assert cli is not None

        # Test that the security scanner can be imported
        from reticulum.security_scanner import SecurityScanner
        assert SecurityScanner is not None