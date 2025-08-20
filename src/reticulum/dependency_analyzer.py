"""
Dependency Analysis Module for Reticulum.

Handles dependency analysis between containers and exposure level reconstruction.
"""

from pathlib import Path
from typing import Dict, List, Any
import yaml


class DependencyAnalyzer:
    """Analyzes dependencies between containers to determine exposure levels."""

    def reconstruct_containers_from_dependencies(
        self,
        chart_containers: Dict[str, Any],
        containers: List[Dict[str, Any]],
        repo_path: Path,
    ) -> List[Dict[str, Any]]:
        """Analyze dependencies to find MEDIUM exposure containers (connected to HIGH)."""
        # Get all HIGH exposure containers first
        high_containers = [c for c in containers if c["exposure_level"] == "HIGH"]
        high_service_names = [c["chart"] for c in high_containers]

        # For each chart that's not already HIGH, check if it connects to HIGH containers
        for chart_name, chart_info in chart_containers.items():
            if not chart_info["exposure_found"]:  # Not already HIGH
                # Check all environment files for dependencies
                chart_dir = Path(repo_path) / chart_info["path"]
                value_files = [
                    ("base", chart_dir / "values.yaml"),
                    ("dev", chart_dir / "dev.yaml"),
                    ("prod", chart_dir / "prod.yaml"),
                    ("staging", chart_dir / "staging.yaml"),
                    ("stg", chart_dir / "stg.yaml"),
                ]

                connected_to_high = False
                connected_services = []

                for env_name, values_file in value_files:
                    if values_file.exists():
                        with open(values_file, "r") as f:
                            try:
                                values = yaml.safe_load(f)
                                if values:
                                    # Check dependencies on HIGH exposure services
                                    for high_service in high_service_names:
                                        if self._has_dependency_on(
                                            values, high_service
                                        ):
                                            connected_to_high = True
                                            connected_services.append(high_service)
                            except yaml.YAMLError:
                                continue

                # If connected to HIGH containers, create MEDIUM container
                if connected_to_high:
                    # Remove duplicates from connected services
                    unique_services = list(set(connected_services))

                    container_info = self._create_medium_container_info(
                        chart_name, unique_services, chart_dir, repo_path
                    )

                    containers.append(container_info)
                    chart_info["exposure_found"] = True

        return containers

    def _has_dependency_on(self, values: Dict[str, Any], chart_name: str) -> bool:
        """Check if configuration has dependency on another service/chart."""
        return self._check_recursive_dependency(values, chart_name)

    def _check_recursive_dependency(self, obj: Any, chart_name: str) -> bool:
        """Recursively check for service name references in any configuration."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Check if key contains service name
                if chart_name.lower() in key.lower():
                    return True
                # Check if value contains service name
                if isinstance(value, str) and chart_name.lower() in value.lower():
                    return True
                # Recursively check nested structures
                if self._check_recursive_dependency(value, chart_name):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if self._check_recursive_dependency(item, chart_name):
                    return True
        elif isinstance(obj, str):
            # Check for service references in various formats:
            # - Direct name: "fastapi"
            # - Service URL: "http://fastapi:8000"
            # - Kubernetes service: "fastapi.namespace.svc.cluster.local"
            # - Environment variable value: "fastapi-service"
            if chart_name.lower() in obj.lower():
                return True

        return False

    def _create_medium_container_info(
        self,
        chart_name: str,
        connected_services: List[str],
        chart_dir: Path,
        repo_path: Path,
    ) -> Dict[str, Any]:
        """Create MEDIUM exposure container info for dependency-connected services."""
        container_info = {
            "name": f"{chart_name}-container",
            "chart": chart_name,
            "environment": "base",
            "gateway_type": "Service Dependency",
            "host": f"Connected to: {', '.join(connected_services)}",
            "exposure_score": 2,
            "exposure_level": "MEDIUM",
            "access_chain": f"Connected to HIGH exposure services: {', '.join(connected_services)}",
            "dockerfile_path": "",
            "source_code_path": [],
            "exposes": [],
            "exposed_by": [f"{srv}-container" for srv in connected_services],
            "depends_on": [],
        }

        return container_info

    def detect_internal_containers(
        self,
        chart_containers: Dict[str, Any],
        containers: List[Dict[str, Any]],
        repo_path: Path,
    ) -> List[Dict[str, Any]]:
        """Detect containers that are LOW exposure (no internet access, no connection to HIGH)."""
        # Find charts that didn't yield any HIGH or MEDIUM containers
        for chart_name, chart_info in chart_containers.items():
            if not chart_info["exposure_found"]:
                # Create LOW exposure container
                container_info = {
                    "name": f"{chart_name}-container",
                    "chart": chart_name,
                    "environment": "base",
                    "gateway_type": "Internal",
                    "host": "No external access",
                    "exposure_score": 1,
                    "exposure_level": "LOW",
                    "access_chain": "Internal Only - No internet access or HIGH container connections",
                    "dockerfile_path": "",
                    "source_code_path": [],
                    "exposes": [],
                    "exposed_by": [],
                    "depends_on": [],
                }

                # Add to results
                containers.append(container_info)

        return containers
