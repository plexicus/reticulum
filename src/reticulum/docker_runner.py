"""
Docker Runner for Security Tools

Handles execution of Trivy and Semgrep via Docker containers
with timeout mechanisms, retry logic, and enhanced error handling.
"""

import json
import subprocess
import tempfile
import time
from typing import Dict, Any
import os


class DockerRunner:
    """Manages Docker container execution for security tools."""

    # Configuration constants
    DEFAULT_TIMEOUT = 600  # 10 minutes
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    DEFAULT_MEMORY_LIMIT = "1g"  # 1GB memory limit
    DEFAULT_CPU_LIMIT = "1.0"  # 1 CPU core

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        memory_limit: str = DEFAULT_MEMORY_LIMIT,
        cpu_limit: str = DEFAULT_CPU_LIMIT,
    ):
        """
        Initialize Docker runner.

        Args:
            timeout: Maximum execution time in seconds for Docker commands
            max_retries: Maximum number of retry attempts for transient failures
            memory_limit: Memory limit for Docker containers (e.g., "1g", "512m")
            cpu_limit: CPU limit for Docker containers (e.g., "1.0", "0.5")
        """
        self.temp_dir = tempfile.mkdtemp(prefix="reticulum_security_")
        self.timeout = timeout
        self.max_retries = max_retries
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit

        # Tool-specific configurations (can be set by SecurityScanner)
        self.trivy_image = "aquasec/trivy:latest"
        self.trivy_severity_levels = "CRITICAL,HIGH,MEDIUM,LOW"
        self.semgrep_image = "returntocorp/semgrep:latest"
        self.semgrep_config = "auto"

    def _execute_docker_command(self, cmd: list, description: str) -> Dict[str, Any]:
        """
        Execute Docker command with timeout and retry logic.

        Args:
            cmd: Docker command as list of arguments
            description: Description of the command for error messages

        Returns:
            Dictionary with execution results
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    print(
                        f"🔄 Retry attempt {attempt}/{self.max_retries} for {description}..."
                    )
                    time.sleep(self.RETRY_DELAY * attempt)  # Exponential backoff

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=self.timeout,
                )

                return {
                    "success": True,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                }

            except subprocess.TimeoutExpired:
                last_error = f"{description} timed out after {self.timeout} seconds"
                print(f"⏰ {last_error}")

            except subprocess.CalledProcessError as e:
                last_error = f"{description} failed with exit code {e.returncode}"
                print(f"❌ {last_error}")

                # Don't retry on certain exit codes that indicate permanent failures
                if e.returncode in [125, 126, 127]:  # Docker command errors
                    break

            except Exception as e:
                last_error = f"{description} failed: {str(e)}"
                print(f"❌ {last_error}")

        return {
            "success": False,
            "error": last_error,
            "stderr": (
                getattr(last_error, "stderr", "")
                if hasattr(last_error, "stderr")
                else ""
            ),
        }

    def run_trivy_sca(self, repo_path: str, output_file: str) -> Dict[str, Any]:
        """
        Run Trivy SCA scan on repository.

        Args:
            repo_path: Path to repository to scan
            output_file: Path to save SARIF results

        Returns:
            Dictionary with scan results and metadata
        """
        # Input validation
        if not self._validate_repository_path(repo_path):
            return {"success": False, "error": f"Invalid repository path: {repo_path}"}

        if not self._validate_output_path(output_file):
            return {
                "success": False,
                "error": f"Invalid output file path: {output_file}",
            }

        print("🔍 Running Trivy SCA scan...")

        # Mount repository as volume and run Trivy with resource limits
        abs_repo_path = os.path.abspath(repo_path)
        cmd = [
            "docker",
            "run",
            "--rm",
            "--memory",
            self.memory_limit,
            "--cpus",
            self.cpu_limit,
            "-v",
            f"{abs_repo_path}:/repo:ro",
            "-v",
            f"{os.path.dirname(output_file)}:/output",
            self.trivy_image,
            "fs",
            "/repo",
            "--format",
            "sarif",
            "--output",
            f"/output/{os.path.basename(output_file)}",
            "--severity",
            self.trivy_severity_levels,
        ]

        # Execute Docker command with timeout and retry logic
        execution_result = self._execute_docker_command(cmd, "Trivy SCA scan")

        if not execution_result["success"]:
            return {
                "success": False,
                "error": execution_result["error"],
                "stderr": execution_result.get("stderr", ""),
            }

        try:
            # Parse results
            with open(output_file, "r") as f:
                sarif_data = json.load(f)

            # Count vulnerabilities by severity
            severity_counts = self._count_trivy_severities(sarif_data)

            print(
                f"✅ Trivy scan completed: {severity_counts['total']} vulnerabilities found"
            )
            for severity, count in severity_counts.items():
                if severity != "total" and count > 0:
                    print(f"   - {severity.capitalize()}: {count}")

            return {
                "success": True,
                "sarif_data": sarif_data,
                "severity_counts": severity_counts,
                "output_file": output_file,
            }

        except Exception as e:
            print(f"❌ Failed to parse Trivy results: {e}")
            return {
                "success": False,
                "error": f"Failed to parse Trivy results: {str(e)}",
                "stderr": execution_result.get("stderr", ""),
            }

    def run_semgrep_sast(self, repo_path: str, output_file: str) -> Dict[str, Any]:
        """
        Run Semgrep SAST scan on repository.

        Args:
            repo_path: Path to repository to scan
            output_file: Path to save SARIF results

        Returns:
            Dictionary with scan results and metadata
        """
        # Input validation
        if not self._validate_repository_path(repo_path):
            return {"success": False, "error": f"Invalid repository path: {repo_path}"}

        if not self._validate_output_path(output_file):
            return {
                "success": False,
                "error": f"Invalid output file path: {output_file}",
            }

        print("🔍 Running Semgrep SAST scan...")

        # Mount repository as volume and run Semgrep with resource limits
        abs_repo_path = os.path.abspath(repo_path)
        cmd = [
            "docker",
            "run",
            "--rm",
            "--memory",
            self.memory_limit,
            "--cpus",
            self.cpu_limit,
            "-v",
            f"{abs_repo_path}:/repo:ro",
            "-v",
            f"{os.path.dirname(output_file)}:/output",
            self.semgrep_image,
            "scan",
            "--config",
            self.semgrep_config,
            "--sarif",
            "--output",
            f"/output/{os.path.basename(output_file)}",
            "/repo",
        ]

        # Execute Docker command with timeout and retry logic
        execution_result = self._execute_docker_command(cmd, "Semgrep SAST scan")

        if not execution_result["success"]:
            return {
                "success": False,
                "error": execution_result["error"],
                "stderr": execution_result.get("stderr", ""),
            }

        try:
            # Parse results
            with open(output_file, "r") as f:
                sarif_data = json.load(f)

            # Count issues by severity
            severity_counts = self._count_semgrep_severities(sarif_data)

            print(
                f"✅ Semgrep scan completed: {severity_counts['total']} code issues found"
            )
            for severity, count in severity_counts.items():
                if severity != "total" and count > 0:
                    print(f"   - {severity.capitalize()}: {count}")

            return {
                "success": True,
                "sarif_data": sarif_data,
                "severity_counts": severity_counts,
                "output_file": output_file,
            }

        except Exception as e:
            print(f"❌ Failed to parse Semgrep results: {e}")
            return {
                "success": False,
                "error": f"Failed to parse Semgrep results: {str(e)}",
                "stderr": execution_result.get("stderr", ""),
            }

    def _count_trivy_severities(self, sarif_data: Dict[str, Any]) -> Dict[str, int]:
        """Count vulnerabilities by severity from Trivy SARIF results."""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0}

        for run in sarif_data.get("runs", []):
            for result in run.get("results", []):
                severity = result.get("level", "warning").lower()
                # Map SARIF levels to Trivy severities
                if severity == "error":
                    counts["critical"] += 1
                elif severity == "warning":
                    counts["high"] += 1
                elif severity == "note":
                    counts["medium"] += 1
                else:
                    counts["low"] += 1
                counts["total"] += 1

        return counts

    def _count_semgrep_severities(self, sarif_data: Dict[str, Any]) -> Dict[str, int]:
        """Count issues by severity from Semgrep SARIF results."""
        counts = {"error": 0, "warning": 0, "info": 0, "total": 0}

        for run in sarif_data.get("runs", []):
            for result in run.get("results", []):
                severity = result.get("level", "warning").lower()
                if severity in counts:
                    counts[severity] += 1
                counts["total"] += 1

        return counts

    def _validate_repository_path(self, repo_path: str) -> bool:
        """
        Validate repository path for security and correctness.

        Args:
            repo_path: Path to validate

        Returns:
            True if path is valid, False otherwise
        """
        try:
            abs_path = os.path.abspath(repo_path)

            # Check if path exists and is a directory
            if not os.path.exists(abs_path):
                print(f"❌ Repository path does not exist: {abs_path}")
                return False

            if not os.path.isdir(abs_path):
                print(f"❌ Repository path is not a directory: {abs_path}")
                return False

            # Check for path traversal attempts
            if ".." in repo_path:
                print(f"⚠️  Suspicious repository path detected: {repo_path}")
                # Allow but log warning

            # Allow absolute paths (common in CI environments and tests)
            if repo_path.startswith("/"):
                # Check if it's a test path (common patterns)
                if (
                    "/tmp/" in repo_path
                    or "/var/tmp/" in repo_path
                    or "/tmp/advanced-test-repo" in repo_path
                ):
                    print(f"📝 Test repository path detected: {repo_path}")
                else:
                    print(f"📁 Absolute repository path: {repo_path}")

            return True

        except Exception as e:
            print(f"❌ Error validating repository path: {e}")
            return False

    def _validate_output_path(self, output_file: str) -> bool:
        """
        Validate output file path for security and correctness.

        Args:
            output_file: Path to validate

        Returns:
            True if path is valid, False otherwise
        """
        try:
            output_dir = os.path.dirname(output_file)

            # Check if output directory exists and is writable
            if not os.path.exists(output_dir):
                # Try to create the directory
                os.makedirs(output_dir, exist_ok=True)

            if not os.access(output_dir, os.W_OK):
                print(f"❌ Output directory is not writable: {output_dir}")
                return False

            # Check for path traversal attempts
            if ".." in output_file:
                print(f"❌ Output file path contains path traversal: {output_file}")
                return False

            return True

        except Exception as e:
            print(f"❌ Error validating output path: {e}")
            return False

    def cleanup(self):
        """Clean up temporary files."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
