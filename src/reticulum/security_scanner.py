"""
Security Scanner Orchestrator

Main orchestrator that runs Trivy SCA, Semgrep SAST, and reticulum
in an integrated security scanning workflow.
"""

import json
import tempfile
import os
import threading
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from .docker_runner import DockerRunner
from .findings_mapper import FindingsMapper
from .enhanced_prioritizer import EnhancedPrioritizer
from .main import ExposureScanner
from .config import SecurityScannerConfig
from .plugin_base import PluginManager


class SecurityScanner:
    """Orchestrates integrated security scanning workflow."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize Security Scanner.

        Args:
            config_file: Optional path to configuration file
        """
        self.config = SecurityScannerConfig(config_file)

        # Validate configuration before proceeding
        if not self.config.validate():
            print("⚠️  Configuration validation failed, using defaults with warnings")

        # Initialize components with configuration
        docker_config = self.config.get_docker_config()
        self.docker_runner = DockerRunner(
            timeout=docker_config.get("timeout"),
            max_retries=docker_config.get("max_retries"),
            memory_limit=docker_config.get("memory_limit"),
            cpu_limit=docker_config.get("cpu_limit"),
        )

        # Update Docker runner with tool-specific configurations
        self._configure_tools()

        self.enhanced_prioritizer = EnhancedPrioritizer()
        self.temp_dir = tempfile.mkdtemp(prefix="reticulum_security_")

        # Get scanner configuration
        scanner_config = self.config.get_scanner_config()
        self.parallel_execution = scanner_config.get("parallel_execution", True)
        self.enable_trivy = scanner_config.get("enable_trivy", True)
        self.enable_semgrep = scanner_config.get("enable_semgrep", True)
        self.output_format = scanner_config.get("output_format", "sarif")

        # Performance configuration
        perf_config = self.config.get_performance_config()
        self.max_workers = perf_config.get("max_workers", 2)
        self.cache_results = perf_config.get("cache_results", False)
        self.cache_ttl = perf_config.get("cache_ttl", 3600)

        # Progress tracking
        self.scan_start_time = None
        self.current_stage = None
        self.progress_callbacks = []

        # Plugin system
        self.plugin_manager = PluginManager()

    def _run_parallel_scans(
        self, repo_path: str
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Run Trivy and Semgrep scans in parallel.

        Args:
            repo_path: Path to repository to scan

        Returns:
            Tuple of (trivy_results, semgrep_results)
        """
        trivy_results = {}
        semgrep_results = {}

        def run_trivy():
            nonlocal trivy_results
            trivy_output = os.path.join(self.temp_dir, "trivy_results.sarif")
            trivy_results = self.docker_runner.run_trivy_sca(repo_path, trivy_output)

        def run_semgrep():
            nonlocal semgrep_results
            semgrep_output = os.path.join(self.temp_dir, "semgrep_results.sarif")
            semgrep_results = self.docker_runner.run_semgrep_sast(
                repo_path, semgrep_output
            )

        # Create and start threads
        trivy_thread = threading.Thread(target=run_trivy)
        semgrep_thread = threading.Thread(target=run_semgrep)

        print("🚀 Starting parallel security scans...")
        trivy_thread.start()
        semgrep_thread.start()

        # Wait for both threads to complete
        trivy_thread.join()
        semgrep_thread.join()

        return trivy_results, semgrep_results

    def _update_progress(
        self, stage: str, message: str, percentage: Optional[int] = None
    ):
        """
        Update progress tracking and notify callbacks.

        Args:
            stage: Current scan stage
            message: Progress message
            percentage: Optional progress percentage (0-100)
        """
        self.current_stage = stage
        progress_data = {
            "stage": stage,
            "message": message,
            "percentage": percentage,
            "timestamp": datetime.now().isoformat(),
        }

        # Print progress to console
        if percentage is not None:
            print(f"📊 [{stage}] {message} ({percentage}%)")
        else:
            print(f"📊 [{stage}] {message}")

        # Notify registered callbacks
        for callback in self.progress_callbacks:
            try:
                callback(progress_data)
            except Exception as e:
                print(f"⚠️  Progress callback failed: {e}")

    def _get_elapsed_time(self) -> float:
        """Get elapsed time since scan started."""
        if self.scan_start_time:
            return time.time() - self.scan_start_time
        return 0.0

    def add_progress_callback(self, callback):
        """
        Add a progress callback function.

        Args:
            callback: Function that receives progress data dict
        """
        self.progress_callbacks.append(callback)

    def _calculate_progress_percentage(
        self, current_step: int, total_steps: int
    ) -> int:
        """Calculate progress percentage based on current step."""
        return min(100, max(0, int((current_step / total_steps) * 100)))

    def security_scan(
        self, repo_path: str, output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform integrated security scan.

        Args:
            repo_path: Path to repository to scan
            output_file: Optional path for SARIF output

        Returns:
            Comprehensive scan results
        """
        self.scan_start_time = time.time()
        total_steps = 8  # Total number of major steps in the scan process
        current_step = 0

        self._update_progress("initialization", "Starting security scan...", 0)

        # Step 1: Run security scans (parallel or sequential)
        current_step += 1
        self._update_progress(
            "security_scans",
            "Running security tools...",
            self._calculate_progress_percentage(current_step, total_steps),
        )

        if self.parallel_execution:
            trivy_results, semgrep_results = self._run_parallel_scans(repo_path)
        else:
            trivy_results = self._run_trivy_scan(repo_path)
            semgrep_results = self._run_semgrep_scan(repo_path)

        # Handle scan failures
        if not trivy_results["success"]:
            self._update_progress("error", "Trivy scan failed", 100)
            return self._create_error_result("Trivy scan failed", trivy_results)

        if not semgrep_results["success"]:
            self._update_progress(
                "warning",
                "Semgrep scan failed, continuing with partial results",
                self._calculate_progress_percentage(current_step, total_steps),
            )
            print(
                f"⚠️  Semgrep scan failed: {semgrep_results.get('error', 'Unknown error')}"
            )
            print("   Continuing with Trivy results only...")
            # Create empty semgrep results to continue
            semgrep_results = {
                "success": False,
                "sarif_data": {"runs": [{"results": []}]},
                "severity_counts": {"total": 0, "error": 0, "warning": 0, "info": 0},
            }

        # Step 3: Run reticulum exposure analysis
        current_step += 1
        self._update_progress(
            "exposure_analysis",
            "Running exposure analysis...",
            self._calculate_progress_percentage(current_step, total_steps),
        )
        reticulum_results = self._run_reticulum_scan(repo_path)

        # Step 4: Map security findings to services
        current_step += 1
        self._update_progress(
            "findings_mapping",
            "Mapping security findings to services...",
            self._calculate_progress_percentage(current_step, total_steps),
        )
        findings_mapper = FindingsMapper(reticulum_results, repo_path)
        trivy_mapping = findings_mapper.map_trivy_findings(trivy_results["sarif_data"])
        semgrep_mapping = findings_mapper.map_semgrep_findings(
            semgrep_results["sarif_data"]
        )

        # Step 5: Enhance prioritization
        current_step += 1
        self._update_progress(
            "prioritization",
            "Enhancing prioritization based on findings...",
            self._calculate_progress_percentage(current_step, total_steps),
        )
        enhanced_report = self.enhanced_prioritizer.enhance_prioritization(
            reticulum_results, trivy_mapping, semgrep_mapping
        )

        # Step 6: Generate SARIF report
        current_step += 1
        self._update_progress(
            "report_generation",
            "Generating SARIF report...",
            self._calculate_progress_percentage(current_step, total_steps),
        )
        sarif_report = self._generate_sarif_report(
            enhanced_report, trivy_mapping, semgrep_mapping
        )

        # Step 7: Save results
        current_step += 1
        self._update_progress(
            "saving_results",
            "Saving scan results...",
            self._calculate_progress_percentage(current_step, total_steps),
        )
        if output_file:
            with open(output_file, "w") as f:
                json.dump(sarif_report, f, indent=2)
            print(f"\n📄 SARIF report generated: {output_file}")

        # Step 8: Generate final summary
        current_step += 1
        self._update_progress(
            "final_summary",
            "Generating final summary...",
            self._calculate_progress_percentage(current_step, total_steps),
        )
        final_summary = self._generate_final_summary(
            trivy_results, semgrep_results, reticulum_results, enhanced_report
        )

        # Add performance metrics to final summary
        elapsed_time = self._get_elapsed_time()
        final_summary["performance_metrics"] = {
            "total_scan_time_seconds": round(elapsed_time, 2),
            "scan_start_time": datetime.fromtimestamp(self.scan_start_time).isoformat(),
            "scan_end_time": datetime.now().isoformat(),
            "parallel_execution": self.parallel_execution,
        }

        self._update_progress("completed", "Security scan completed successfully!", 100)
        self._cleanup()
        return final_summary

    def register_security_tool(self, tool):
        """
        Register a custom security tool plugin.

        Args:
            tool: SecurityToolPlugin instance
        """
        self.plugin_manager.register_security_tool(tool)

    def register_processor(self, processor):
        """
        Register a custom processing plugin.

        Args:
            processor: ProcessingPlugin instance
        """
        self.plugin_manager.register_processor(processor)

    def get_available_plugins(self) -> Dict[str, List[str]]:
        """
        Get list of available plugins.

        Returns:
            Dictionary with 'security_tools' and 'processors' keys
        """
        return {
            "security_tools": self.plugin_manager.get_available_tools(),
            "processors": self.plugin_manager.get_available_processors(),
        }

    def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of the security scanner.

        Returns:
            Dictionary with health status and component information
        """
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "components": {},
            "warnings": [],
            "errors": [],
        }

        # Check Docker availability
        docker_status = self._check_docker_health()
        health_status["components"]["docker"] = docker_status
        if not docker_status["available"]:
            health_status["overall_status"] = "unhealthy"
            health_status["errors"].append("Docker is not available")

        # Check configuration
        config_status = self._check_config_health()
        health_status["components"]["configuration"] = config_status
        if not config_status["valid"]:
            health_status["overall_status"] = "unhealthy"
            health_status["errors"].append("Configuration is invalid")

        # Check security tools availability
        tools_status = self._check_tools_health()
        health_status["components"]["security_tools"] = tools_status
        for tool, status in tools_status.items():
            if not status["available"]:
                health_status["warnings"].append(f"{tool} may not be available")

        # Check plugin system
        plugin_status = self._check_plugin_health()
        health_status["components"]["plugins"] = plugin_status

        return health_status

    def _check_docker_health(self) -> Dict[str, Any]:
        """Check Docker availability and configuration."""
        try:
            import subprocess

            result = subprocess.run(
                ["docker", "version"], capture_output=True, text=True, timeout=10
            )
            return {
                "available": result.returncode == 0,
                "version": self._extract_docker_version(result.stdout),
                "details": (
                    "Docker daemon is running"
                    if result.returncode == 0
                    else "Docker daemon not available"
                ),
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "details": "Failed to check Docker status",
            }

    def _check_config_health(self) -> Dict[str, Any]:
        """Check configuration health."""
        try:
            valid = self.config.validate()
            return {
                "valid": valid,
                "loaded_from": self.config.config_file or "defaults",
                "details": (
                    "Configuration loaded successfully"
                    if valid
                    else "Configuration validation failed"
                ),
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "details": "Configuration validation error",
            }

    def _check_tools_health(self) -> Dict[str, Any]:
        """Check security tools availability."""
        tools_status = {}

        # Check Trivy
        try:
            import subprocess

            result = subprocess.run(
                ["docker", "pull", self.docker_runner.trivy_image],
                capture_output=True,
                text=True,
                timeout=30,
            )
            tools_status["trivy"] = {
                "available": result.returncode == 0,
                "image": self.docker_runner.trivy_image,
                "details": (
                    "Trivy image available"
                    if result.returncode == 0
                    else "Failed to pull Trivy image"
                ),
            }
        except Exception as e:
            tools_status["trivy"] = {
                "available": False,
                "error": str(e),
                "details": "Error checking Trivy availability",
            }

        # Check Semgrep
        try:
            import subprocess

            result = subprocess.run(
                ["docker", "pull", self.docker_runner.semgrep_image],
                capture_output=True,
                text=True,
                timeout=30,
            )
            tools_status["semgrep"] = {
                "available": result.returncode == 0,
                "image": self.docker_runner.semgrep_image,
                "details": (
                    "Semgrep image available"
                    if result.returncode == 0
                    else "Failed to pull Semgrep image"
                ),
            }
        except Exception as e:
            tools_status["semgrep"] = {
                "available": False,
                "error": str(e),
                "details": "Error checking Semgrep availability",
            }

        return tools_status

    def _check_plugin_health(self) -> Dict[str, Any]:
        """Check plugin system health."""
        available_plugins = self.get_available_plugins()
        return {
            "available_tools": len(available_plugins["security_tools"]),
            "available_processors": len(available_plugins["processors"]),
            "details": "Plugin system initialized successfully",
        }

    def _extract_docker_version(self, version_output: str) -> str:
        """Extract Docker version from version command output."""
        try:
            for line in version_output.split("\n"):
                if "Version:" in line:
                    return line.split("Version:")[1].strip()
            return "unknown"
        except Exception:
            return "unknown"

    def _run_trivy_scan(self, repo_path: str) -> Dict[str, Any]:
        """Run Trivy SCA scan."""
        trivy_output = os.path.join(self.temp_dir, "trivy_results.sarif")
        return self.docker_runner.run_trivy_sca(repo_path, trivy_output)

    def _run_semgrep_scan(self, repo_path: str) -> Dict[str, Any]:
        """Run Semgrep SAST scan."""
        semgrep_output = os.path.join(self.temp_dir, "semgrep_results.sarif")
        return self.docker_runner.run_semgrep_sast(repo_path, semgrep_output)

    def _run_reticulum_scan(self, repo_path: str) -> Dict[str, Any]:
        """Run reticulum exposure analysis."""
        scanner = ExposureScanner()
        results = scanner.scan_repo(repo_path)

        # Extract prioritization report
        prioritization_report = results.get("prioritization_report", {})

        print(
            f"✅ Exposure analysis completed: {prioritization_report.get('summary', {}).get('total_services', 0)} services analyzed"
        )
        summary = prioritization_report.get("summary", {})
        print(f"   - High exposure: {summary.get('high_risk', 0)} services")
        print(f"   - Medium exposure: {summary.get('medium_risk', 0)} services")
        print(f"   - Low exposure: {summary.get('low_risk', 0)} services")

        return prioritization_report

    def _generate_sarif_report(
        self,
        enhanced_report: Dict[str, Any],
        trivy_mapping: Dict[str, Any],
        semgrep_mapping: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate enhanced SARIF report."""
        sarif_report = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemas/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [],
        }

        # Add enhanced prioritization as a custom run
        enhanced_run = {
            "tool": {
                "driver": {
                    "name": "Reticulum Enhanced Security Scanner",
                    "version": "1.0.0",
                    "informationUri": "https://github.com/plexicus/reticulum",
                    "rules": [],
                }
            },
            "results": [],
            "properties": {
                "reticulum": {
                    "enhanced_prioritization": enhanced_report,
                    "mapping_summary": {
                        "trivy": trivy_mapping["summary"],
                        "semgrep": semgrep_mapping["summary"],
                    },
                }
            },
        }

        # Add services with security findings as results
        for service_name, service_data in trivy_mapping["services"].items():
            service_info = service_data["service_info"]
            result = {
                "ruleId": f"exposed-service-{service_name}",
                "level": "warning",
                "message": {
                    "text": f"Service {service_name} has {len(service_data['trivy_findings'])} security findings and is {service_info.get('risk_level', 'LOW')} exposure"
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": service_info.get("dockerfile_path", "")
                                or service_info.get("source_code_paths", [""])[0]
                            }
                        }
                    }
                ],
                "properties": {
                    "service_name": service_name,
                    "exposure_level": service_info.get("risk_level", "LOW"),
                    "trivy_findings_count": len(service_data["trivy_findings"]),
                    "enhanced_priority": service_info.get("enhanced_risk_level", "LOW"),
                },
            }
            enhanced_run["results"].append(result)

        sarif_report["runs"].append(enhanced_run)
        return sarif_report

    def _generate_final_summary(
        self,
        trivy_results: Dict[str, Any],
        semgrep_results: Dict[str, Any],
        reticulum_results: Dict[str, Any],
        enhanced_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate comprehensive final summary."""
        summary = {
            "scan_timestamp": datetime.now().isoformat(),
            "security_tools": {
                "trivy": trivy_results["severity_counts"],
                "semgrep": semgrep_results["severity_counts"],
            },
            "exposure_analysis": reticulum_results.get("summary", {}),
            "enhanced_prioritization": enhanced_report.get("enhanced_summary", {}),
            "total_findings": {
                "trivy": trivy_results["severity_counts"]["total"],
                "semgrep": semgrep_results["severity_counts"]["total"],
                "combined": trivy_results["severity_counts"]["total"]
                + semgrep_results["severity_counts"]["total"],
            },
        }

        # Print final summary
        print("\n🎉 Security Scan Completed!")
        print("=" * 50)
        print("📊 Final Summary:")
        print(f"   - Total vulnerabilities: {summary['total_findings']['trivy']}")
        print(f"   - Total code issues: {summary['total_findings']['semgrep']}")
        print(f"   - Combined findings: {summary['total_findings']['combined']}")
        print(
            f"   - Services analyzed: {summary['exposure_analysis'].get('total_services', 0)}"
        )

        enhanced_summary = summary["enhanced_prioritization"]
        if enhanced_summary:
            print(
                f"   - Services upgraded: {enhanced_summary.get('security_impact', {}).get('services_upgraded', 0)}"
            )
            print(
                f"   - Services downgraded: {enhanced_summary.get('security_impact', {}).get('services_downgraded', 0)}"
            )

        return summary

    def _create_error_result(
        self, message: str, tool_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create error result when a tool fails."""
        return {
            "success": False,
            "error": message,
            "tool_error": tool_results.get("error", ""),
            "tool_stderr": tool_results.get("stderr", ""),
        }

    def _cleanup(self):
        """Clean up temporary files."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.docker_runner.cleanup()

    def _configure_tools(self):
        """Configure security tools with specific settings from configuration."""
        # Configure Trivy
        trivy_config = self.config.get_tool_config("trivy")
        if trivy_config:
            self.docker_runner.trivy_image = trivy_config.get(
                "image", "aquasec/trivy:latest"
            )
            self.docker_runner.trivy_severity_levels = trivy_config.get(
                "severity_levels", "CRITICAL,HIGH,MEDIUM,LOW"
            )
            print(f"✅ Trivy configured: {self.docker_runner.trivy_image}")

        # Configure Semgrep
        semgrep_config = self.config.get_tool_config("semgrep")
        if semgrep_config:
            self.docker_runner.semgrep_image = semgrep_config.get(
                "image", "returntocorp/semgrep:latest"
            )
            self.docker_runner.semgrep_config = semgrep_config.get("config", "auto")
            print(f"✅ Semgrep configured: {self.docker_runner.semgrep_image}")
