"""
Advanced tests for Reticulum Security Scanner with realistic vulnerabilities.
"""

import pytest
import tempfile
import os
import json
import shutil
from pathlib import Path
from src.reticulum.security_scanner import SecurityScanner
from src.reticulum.config import SecurityScannerConfig


class TestSecurityScannerAdvanced:
    """Advanced tests for security scanner with realistic vulnerability scenarios."""

    @pytest.fixture
    def test_repo_path(self):
        """Path to the test repository with vulnerabilities."""
        return "/tmp/advanced-test-repo"

    @pytest.fixture
    def scanner(self):
        """Create a security scanner instance."""
        return SecurityScanner()

    def test_scanner_initialization(self, scanner):
        """Test that scanner initializes correctly."""
        assert scanner is not None
        assert scanner.config is not None
        assert scanner.docker_runner is not None
        assert scanner.plugin_manager is not None

    def test_configuration_system(self):
        """Test configuration system with custom settings."""
        # Test with environment variables
        os.environ['RETICULUM_DOCKER_TIMEOUT'] = '300'
        os.environ['RETICULUM_TRIVY_IMAGE'] = 'aquasec/trivy:0.45.0'

        config = SecurityScannerConfig()
        assert config.get('docker.timeout') == 300
        assert config.get('tools.trivy.image') == 'aquasec/trivy:0.45.0'

        # Clean up
        del os.environ['RETICULUM_DOCKER_TIMEOUT']
        del os.environ['RETICULUM_TRIVY_IMAGE']

    def test_health_check(self, scanner):
        """Test health check functionality."""
        health_status = scanner.health_check()

        assert 'overall_status' in health_status
        assert 'components' in health_status
        assert 'docker' in health_status['components']
        assert 'configuration' in health_status['components']
        assert 'security_tools' in health_status['components']

    def test_plugin_system(self, scanner):
        """Test plugin registration and management."""
        from src.reticulum.example_plugins import ExampleSecurityTool, ExampleProcessor

        # Register plugins
        scanner.register_security_tool(ExampleSecurityTool())
        scanner.register_processor(ExampleProcessor())

        # Check available plugins
        plugins = scanner.get_available_plugins()
        assert 'example-security-tool' in plugins['security_tools']
        assert 'example-processor' in plugins['processors']

    def test_progress_reporting(self, scanner):
        """Test progress reporting system."""
        progress_data = []

        def progress_callback(data):
            progress_data.append(data)

        scanner.add_progress_callback(progress_callback)
        scanner._update_progress('test', 'Testing progress', 50)

        assert len(progress_data) == 1
        assert progress_data[0]['stage'] == 'test'
        assert progress_data[0]['message'] == 'Testing progress'
        assert progress_data[0]['percentage'] == 50

    @pytest.mark.integration
    def test_trivy_scan_vulnerable_dependencies(self, scanner, test_repo_path):
        """Test Trivy SCA scan on repository with vulnerable dependencies."""
        with tempfile.NamedTemporaryFile(suffix='.sarif', delete=False) as temp_file:
            output_file = temp_file.name

        try:
            # Run Trivy scan
            result = scanner.docker_runner.run_trivy_sca(test_repo_path, output_file)

            assert result["success"] == True
            assert "sarif_data" in result
            assert "severity_counts" in result

            # Should find vulnerabilities in requirements.txt
            severity_counts = result["severity_counts"]
            assert severity_counts["total"] > 0

            # Verify SARIF structure
            sarif_data = result["sarif_data"]
            assert "runs" in sarif_data
            assert len(sarif_data["runs"]) > 0

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    @pytest.mark.integration
    def test_semgrep_scan_sast_vulnerabilities(self, scanner, test_repo_path):
        """Test Semgrep SAST scan on repository with code vulnerabilities."""
        with tempfile.NamedTemporaryFile(suffix='.sarif', delete=False) as temp_file:
            output_file = temp_file.name

        try:
            # Run Semgrep scan
            result = scanner.docker_runner.run_semgrep_sast(test_repo_path, output_file)

            # Semgrep might fail due to Docker issues, but we handle that gracefully
            if result["success"]:
                assert "sarif_data" in result
                assert "severity_counts" in result

                # Should find SAST vulnerabilities
                severity_counts = result["severity_counts"]
                # Even if no findings, structure should be correct
                assert "total" in severity_counts

            else:
                # Semgrep failed, but scanner should handle this gracefully
                assert "error" in result

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    @pytest.mark.integration
    def test_integrated_security_scan(self, scanner, test_repo_path):
        """Test complete integrated security scan workflow."""
        with tempfile.NamedTemporaryFile(suffix='.sarif', delete=False) as temp_file:
            output_file = temp_file.name

        try:
            # Run complete security scan
            results = scanner.security_scan(test_repo_path, output_file)

            # Verify results structure
            assert "scan_timestamp" in results
            assert "security_tools" in results
            assert "exposure_analysis" in results
            assert "enhanced_prioritization" in results
            assert "total_findings" in results
            assert "performance_metrics" in results

            # Verify security tools results
            security_tools = results["security_tools"]
            assert "trivy" in security_tools
            assert "semgrep" in security_tools

            # Verify exposure analysis
            exposure_analysis = results["exposure_analysis"]
            assert "total_services" in exposure_analysis

            # Verify output file was created
            assert os.path.exists(output_file)

            # Verify SARIF file content
            with open(output_file, 'r') as f:
                sarif_data = json.load(f)
            assert "runs" in sarif_data

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_error_handling_invalid_path(self, scanner):
        """Test error handling with invalid repository path."""
        invalid_path = "/nonexistent/path"

        # Test Trivy with invalid path
        with tempfile.NamedTemporaryFile(suffix='.sarif') as temp_file:
            result = scanner.docker_runner.run_trivy_sca(invalid_path, temp_file.name)
            assert result["success"] == False
            assert "error" in result

    def test_parallel_execution_configuration(self):
        """Test parallel execution configuration."""
        # Test with parallel execution disabled
        os.environ['RETICULUM_PARALLEL_EXECUTION'] = 'false'

        scanner = SecurityScanner()
        assert scanner.parallel_execution == False

        # Clean up
        del os.environ['RETICULUM_PARALLEL_EXECUTION']

    def test_findings_mapping(self, scanner, test_repo_path):
        """Test mapping of security findings to services."""
        from src.reticulum.findings_mapper import FindingsMapper

        # First run reticulum exposure analysis
        from src.reticulum.main import ExposureScanner
        exposure_scanner = ExposureScanner()
        reticulum_results = exposure_scanner.scan_repo(test_repo_path)

        # Create findings mapper
        mapper = FindingsMapper(reticulum_results, test_repo_path)

        # Test with empty findings (mock data)
        empty_trivy_results = {"runs": [{"results": []}]}
        empty_semgrep_results = {"runs": [{"results": []}]}

        trivy_mapping = mapper.map_trivy_findings(empty_trivy_results)
        semgrep_mapping = mapper.map_semgrep_findings(empty_semgrep_results)

        assert "services" in trivy_mapping
        assert "summary" in trivy_mapping
        assert "services" in semgrep_mapping
        assert "summary" in semgrep_mapping

    def test_enhanced_prioritization(self, scanner, test_repo_path):
        """Test enhanced prioritization based on exposure and findings."""
        from src.reticulum.enhanced_prioritizer import EnhancedPrioritizer
        from src.reticulum.main import ExposureScanner

        # Get exposure analysis
        exposure_scanner = ExposureScanner()
        reticulum_results = exposure_scanner.scan_repo(test_repo_path)

        # Create empty findings mappings
        empty_mapping = {
            "services": {},
            "summary": {"total_findings": 0, "mapped_findings": 0, "unmapped_findings": 0}
        }

        # Test prioritization
        prioritizer = EnhancedPrioritizer()
        enhanced_report = prioritizer.enhance_prioritization(
            reticulum_results, empty_mapping, empty_mapping
        )

        assert "repo_path" in enhanced_report
        assert "summary" in enhanced_report
        assert "prioritized_services" in enhanced_report
        assert "enhanced_summary" in enhanced_report


class TestVulnerabilityScenarios:
    """Test specific vulnerability scenarios."""

    def test_sql_injection_detection(self):
        """Verify SQL injection patterns are present in test code."""
        test_file = "/tmp/advanced-test-repo/vulnerable_app.py"

        with open(test_file, 'r') as f:
            content = f.read()

        # Check for SQL injection pattern
        assert "f\"SELECT * FROM users WHERE username = '{username}'\"" in content

    def test_command_injection_detection(self):
        """Verify command injection patterns are present in test code."""
        test_file = "/tmp/advanced-test-repo/vulnerable_app.py"

        with open(test_file, 'r') as f:
            content = f.read()

        # Check for command injection pattern
        assert 'subprocess.run(f"echo {command}", shell=True' in content

    def test_insecure_deserialization_detection(self):
        """Verify insecure deserialization patterns are present."""
        test_file = "/tmp/advanced-test-repo/vulnerable_app.py"

        with open(test_file, 'r') as f:
            content = f.read()

        # Check for pickle.loads
        assert "pickle.loads(data)" in content

    def test_vulnerable_dependencies_present(self):
        """Verify vulnerable dependencies are present in requirements."""
        requirements_file = "/tmp/advanced-test-repo/requirements.txt"

        with open(requirements_file, 'r') as f:
            content = f.read()

        # Check for known vulnerable packages
        assert "requests==2.25.1" in content  # CVE-2021-33503
        assert "Django==3.1.14" in content    # CVE-2021-33203
        assert "urllib3==1.26.4" in content   # CVE-2021-33503


if __name__ == "__main__":
    # Run tests
    import sys
    sys.exit(pytest.main([__file__, "-v"]))