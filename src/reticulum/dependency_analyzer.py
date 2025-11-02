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
                # Check if key contains service name (more precise matching)
                if self._is_service_reference(key, chart_name):
                    return True
                # Check if value contains service name
                if isinstance(value, str) and self._is_service_reference(
                    value, chart_name
                ):
                    return True
                # Recursively check nested structures
                if self._check_recursive_dependency(value, chart_name):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if self._check_recursive_dependency(item, chart_name):
                    return True
        elif isinstance(obj, str):
            # Check for service references in various formats
            if self._is_service_reference(obj, chart_name):
                return True

        return False

    def _is_service_reference(self, text: str, chart_name: str) -> bool:
        """Check if text contains a meaningful service reference to chart_name."""
        if not text or not chart_name:
            return False

        text_lower = text.lower()
        chart_lower = chart_name.lower()

        # Skip common false positives
        false_positives = [
            "fastapi",  # Could match "fastapi" in unrelated contexts
            "worker",  # Common word
            "code",  # Common word
            "prov",  # Common abbreviation
        ]

        if chart_lower in false_positives:
            # Use more precise matching for common words
            patterns = [
                f"{chart_lower}://",  # URL scheme
                f"{chart_lower}:",  # Port specification
                f"{chart_lower}.svc",  # Kubernetes service
                f"{chart_lower}-service",  # Service name
                f"{chart_lower}_service",  # Service name
                f"{chart_lower}.cluster",  # Cluster reference
                f"{chart_lower}.namespace",  # Namespace reference
                f"{chart_lower}-container",  # Container name
                f"{chart_lower}_container",  # Container name
            ]
            return any(pattern in text_lower for pattern in patterns)

        # For other services, use more precise matching
        patterns = [
            f"{chart_lower}://",  # URL scheme
            f"{chart_lower}:",  # Port specification
            f"{chart_lower}.svc",  # Kubernetes service
            f"{chart_lower}-service",  # Service name
            f"{chart_lower}_service",  # Service name
            f"{chart_lower}.cluster",  # Cluster reference
            f"{chart_lower}.namespace",  # Namespace reference
            f"{chart_lower}-container",  # Container name
            f"{chart_lower}_container",  # Container name
            # Whole word match (with word boundaries)
            f" {chart_lower} ",  # Space delimited
            f" {chart_lower},",  # Comma delimited
            f" {chart_lower}.",  # Period delimited
            f" {chart_lower}:",  # Colon delimited
            f" {chart_lower}\n",  # Newline delimited
            f'"{chart_lower}"',  # Quoted
            f"'{chart_lower}'",  # Single quoted
        ]

        return any(pattern in text_lower for pattern in patterns)

    def _create_medium_container_info(
        self,
        chart_name: str,
        connected_services: List[str],
        chart_dir: Path,
        repo_path: Path,
    ) -> Dict[str, Any]:
        """Create MEDIUM exposure container info for dependency-connected services."""
        # Load values.yaml to analyze dependencies
        values_file = chart_dir / "values.yaml"
        values = {}
        if values_file.exists():
            try:
                import yaml

                with open(values_file, "r", encoding="utf-8") as f:
                    values = yaml.safe_load(f) or {}
            except Exception:
                values = {}

        # Analyze dependencies from values.yaml
        depends_on = self._analyze_service_dependencies(chart_name, values, chart_dir)

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
            "depends_on": depends_on,
        }

        return container_info

    def _analyze_service_dependencies(
        self, chart_name: str, values: Dict[str, Any], chart_dir: Path
    ) -> List[Dict[str, Any]]:
        """Analyze what other services this service depends on."""
        depends_on = []

        if not values:
            return depends_on

        # Check for explicit dependencies section
        if "dependencies" in values:
            deps = values["dependencies"]
            if isinstance(deps, dict):
                for dep_name, dep_config in deps.items():
                    if isinstance(dep_config, str):
                        # Simple string dependency
                        depends_on.append(
                            {
                                "service": dep_config,
                                "type": "service",
                                "required": True,
                                "description": f"Dependency on {dep_config}",
                            }
                        )
                    elif isinstance(dep_config, dict):
                        # Complex dependency configuration
                        required = dep_config.get("required", True)
                        description = dep_config.get(
                            "description", f"Dependency on {dep_name}"
                        )
                        depends_on.append(
                            {
                                "service": dep_name,
                                "type": "custom",
                                "required": required,
                                "description": description,
                            }
                        )

        # Check for database dependencies
        for db_type in ["postgresql", "mysql", "mongodb", "redis", "database"]:
            if db_type in values:
                db_config = values[db_type]
                if isinstance(db_config, dict):
                    # Check if database is enabled or has configuration
                    enabled = db_config.get(
                        "enabled", True
                    )  # Default to True if not specified
                    if enabled or any(
                        key in db_config for key in ["type", "host", "port", "url"]
                    ):
                        depends_on.append(
                            {
                                "service": f"{chart_name}-{db_type}",
                                "type": "database",
                                "required": True,
                                "description": f"{db_type.title()} database dependency",
                            }
                        )

        # Check for cache dependencies
        if "cache" in values:
            cache_config = values["cache"]
            if isinstance(cache_config, dict):
                # Check if cache is enabled or has configuration
                enabled = cache_config.get(
                    "enabled", True
                )  # Default to True if not specified
                if enabled or any(
                    key in cache_config for key in ["type", "host", "port", "url"]
                ):
                    depends_on.append(
                        {
                            "service": f"{chart_name}-cache",
                            "type": "cache",
                            "required": False,
                            "description": "Cache service dependency",
                        }
                    )

        # Check for message queue dependencies
        for queue_type in ["rabbitmq", "kafka", "redis", "queue"]:
            if queue_type in values:
                queue_config = values[queue_type]
                if isinstance(queue_config, dict):
                    # Check if queue is enabled or has configuration
                    enabled = queue_config.get(
                        "enabled", True
                    )  # Default to True if not specified
                    if enabled or any(
                        key in queue_config for key in ["type", "host", "port", "url"]
                    ):
                        depends_on.append(
                            {
                                "service": f"{chart_name}-{queue_type}",
                                "type": "message_queue",
                                "required": False,
                                "description": f"{queue_type.title()} message queue dependency",
                            }
                        )

        # Check for monitoring dependencies
        if "monitoring" in values:
            monitoring_config = values["monitoring"]
            if isinstance(monitoring_config, dict):
                # Check if monitoring is enabled or has configuration
                enabled = monitoring_config.get(
                    "enabled", True
                )  # Default to True if not specified
                if enabled or any(
                    key in monitoring_config for key in ["type", "host", "port", "url"]
                ):
                    depends_on.append(
                        {
                            "service": f"{chart_name}-monitoring",
                            "type": "monitoring",
                            "required": False,
                            "description": "Monitoring service dependency",
                        }
                    )

        # Check for storage dependencies
        if "storage" in values:
            storage_config = values["storage"]
            if isinstance(storage_config, dict):
                # Check if storage is enabled or has configuration
                enabled = storage_config.get(
                    "enabled", True
                )  # Default to True if not specified
                if enabled or any(
                    key in storage_config for key in ["type", "size", "storageClass"]
                ):
                    depends_on.append(
                        {
                            "service": f"{chart_name}-storage",
                            "type": "storage",
                            "required": False,
                            "description": "Persistent storage dependency",
                        }
                    )

        return depends_on

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
                # Load values.yaml to analyze dependencies
                chart_dir = repo_path / "charts" / chart_name
                values_file = chart_dir / "values.yaml"
                values = {}
                if values_file.exists():
                    try:
                        import yaml

                        with open(values_file, "r", encoding="utf-8") as f:
                            values = yaml.safe_load(f) or {}
                    except Exception:
                        values = {}

                # Analyze dependencies from values.yaml
                depends_on = self._analyze_service_dependencies(
                    chart_name, values, chart_dir
                )

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
                    "depends_on": depends_on,
                }

                # Add to results
                containers.append(container_info)

        return containers
