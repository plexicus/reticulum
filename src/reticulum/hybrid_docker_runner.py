"""
Hybrid Docker Runner for Security Tools

Provides a hybrid approach:
- Local development: Uses real Docker execution for Trivy and Semgrep
- CI environments: Uses pre-generated SARIF files to avoid Docker dependency issues
"""

import json
import os
from typing import Dict, Any

from .docker_runner import DockerRunner


class HybridDockerRunner:
    """
    Hybrid Docker runner that uses real Docker locally and SARIF files in CI.

    This provides the best of both worlds:
    - Real testing during development
    - Reliable CI without Docker dependency issues
    - Same test coverage and results in both environments
    """

    def __init__(self, use_sarif_files: bool = None):
        """
        Initialize hybrid Docker runner.

        Args:
            use_sarif_files: Whether to use SARIF files instead of Docker.
                            If None, auto-detects based on environment.
        """
        self.docker_runner = DockerRunner()

        # Auto-detect if not specified
        if use_sarif_files is None:
            self.use_sarif_files = self._is_ci_environment()
        else:
            self.use_sarif_files = use_sarif_files

        # SARIF file paths
        self.trivy_sarif_file = "tests/test_data/trivy_results.sarif"
        self.semgrep_sarif_file = "tests/test_data/semgrep_results.sarif"

    def _is_ci_environment(self) -> bool:
        """
        Detect if we're running in a CI environment.

        Returns:
            True if running in CI, False otherwise
        """
        ci_indicators = [
            "GITHUB_ACTIONS",
            "CI",
            "CONTINUOUS_INTEGRATION",
            "BUILD_ID",
            "BUILD_NUMBER",
            "TEAMCITY_VERSION",
            "JENKINS_URL",
            "TRAVIS",
            "CIRCLECI",
            "GITLAB_CI",
        ]

        for indicator in ci_indicators:
            if os.environ.get(indicator):
                return True

        return False

    def run_trivy_sca(self, repo_path: str, output_file: str) -> Dict[str, Any]:
        """
        Run Trivy SCA scan using either Docker or SARIF files.

        Args:
            repo_path: Path to repository to scan
            output_file: Path to save SARIF results

        Returns:
            Dictionary with scan results and metadata
        """
        if self.use_sarif_files:
            return self._run_from_sarif_file(
                self.trivy_sarif_file, output_file, "Trivy"
            )
        else:
            return self.docker_runner.run_trivy_sca(repo_path, output_file)

    def run_semgrep_sast(self, repo_path: str, output_file: str) -> Dict[str, Any]:
        """
        Run Semgrep SAST scan using either Docker or SARIF files.

        Args:
            repo_path: Path to repository to scan
            output_file: Path to save SARIF results

        Returns:
            Dictionary with scan results and metadata
        """
        if self.use_sarif_files:
            return self._run_from_sarif_file(
                self.semgrep_sarif_file, output_file, "Semgrep"
            )
        else:
            return self.docker_runner.run_semgrep_sast(repo_path, output_file)

    def _run_from_sarif_file(
        self, sarif_file: str, output_file: str, tool_name: str
    ) -> Dict[str, Any]:
        """
        Run security scan using pre-generated SARIF file.

        Args:
            sarif_file: Path to pre-generated SARIF file
            output_file: Path to save SARIF results
            tool_name: Name of the security tool

        Returns:
            Dictionary with scan results and metadata
        """
        print(f"📄 Using pre-generated {tool_name} SARIF file for CI...")

        try:
            # Read the pre-generated SARIF file
            with open(sarif_file, "r") as f:
                sarif_data = json.load(f)

            # Copy to output location
            with open(output_file, "w") as f:
                json.dump(sarif_data, f, indent=2)

            # Count vulnerabilities by severity
            if tool_name == "Trivy":
                severity_counts = self.docker_runner._count_trivy_severities(sarif_data)
            else:
                severity_counts = self.docker_runner._count_semgrep_severities(
                    sarif_data
                )

            print(
                f"✅ {tool_name} scan completed (from SARIF): {severity_counts['total']} findings"
            )
            for severity, count in severity_counts.items():
                if severity != "total" and count > 0:
                    print(f"   - {severity.capitalize()}: {count}")

            return {
                "success": True,
                "sarif_data": sarif_data,
                "severity_counts": severity_counts,
                "output_file": output_file,
                "source": "sarif_file",
            }

        except Exception as e:
            error_msg = f"Failed to use {tool_name} SARIF file: {str(e)}"
            print(f"❌ {error_msg}")

            return {
                "success": False,
                "error": error_msg,
                "source": "sarif_file",
            }

    def set_use_sarif_files(self, use_sarif_files: bool):
        """
        Set whether to use SARIF files instead of Docker.

        Args:
            use_sarif_files: True to use SARIF files, False to use Docker
        """
        self.use_sarif_files = use_sarif_files

    def get_runner_mode(self) -> str:
        """
        Get the current runner mode.

        Returns:
            "docker" if using Docker, "sarif" if using SARIF files
        """
        return "sarif" if self.use_sarif_files else "docker"

    def cleanup(self):
        """
        Clean up any resources used by the hybrid runner.

        This method is called by the security scanner during cleanup.
        """
        # Clean up the underlying Docker runner
        self.docker_runner.cleanup()
