"""
Exposure Analysis Module for Reticulum.

Handles the analysis of Helm charts and Kubernetes resources for exposure detection.
"""

import re
from pathlib import Path
from typing import Dict, List, Any
import yaml


class ExposureAnalyzer:
    """Analyzes Helm charts and Kubernetes resources for exposure patterns."""

    def __init__(self):
        self.chart_containers = {}

        # Define exposure patterns using regex for flexibility
        self.exposure_patterns = {
            # Service exposure patterns
            "loadbalancer_service": {
                "pattern": r"type:\s*(?:LoadBalancer|NodePort)",
                "score": 3,
                "level": "HIGH",
                "description": "LoadBalancer/NodePort Service",
            },
            "clusterip_service": {
                "pattern": r"type:\s*ClusterIP",
                "score": 1,
                "level": "LOW",
                "description": "ClusterIP Service",
            },
            # Ingress patterns
            "ingress_enabled": {
                "pattern": r"ingress:\s*\n\s*enabled:\s*true",
                "score": 2,
                "level": "MEDIUM",
                "description": "Ingress Enabled",
            },
            "ingress_host": {
                "pattern": r'host:\s*[\'"]([^\'"]+)[\'"]',
                "score": 2,
                "level": "MEDIUM",
                "description": "Ingress Host Configured",
            },
            # Istio patterns
            "istio_gateway": {
                "pattern": r"kind:\s*Gateway",
                "score": 3,
                "level": "HIGH",
                "description": "Istio Gateway",
            },
            "istio_virtualservice": {
                "pattern": r"kind:\s*VirtualService",
                "score": 2,
                "level": "MEDIUM",
                "description": "Istio VirtualService",
            },
            # Cloud exposure patterns
            "aws_loadbalancer": {
                "pattern": r"service\.beta\.kubernetes\.io/aws-load-balancer-type",
                "score": 3,
                "level": "HIGH",
                "description": "AWS Load Balancer",
            },
            "gcp_loadbalancer": {
                "pattern": r"cloud\.google\.com/load-balancer-type",
                "score": 3,
                "level": "HIGH",
                "description": "GCP Load Balancer",
            },
            # Port exposure patterns
            "external_ports": {
                "pattern": r"ports:\s*\n\s*-\s*port:\s*\d+\s*\n\s*external:\s*true",
                "score": 2,
                "level": "MEDIUM",
                "description": "External Ports",
            },
            # Security context patterns
            "privileged_container": {
                "pattern": r"privileged:\s*true",
                "score": 2,
                "level": "MEDIUM",
                "description": "Privileged Container",
            },
            "host_network": {
                "pattern": r"hostNetwork:\s*true",
                "score": 3,
                "level": "HIGH",
                "description": "Host Network Access",
            },
        }

    def analyze_chart(self, chart_dir: Path, repo_path: Path) -> Dict[str, Any]:
        """Analyze a Helm chart directory for exposure information using intelligent pattern matching."""
        chart_name = chart_dir.name
        chart_info = {
            "name": chart_name,
            "path": str(chart_dir.relative_to(repo_path)),
            "exposure_found": False,
            "containers": [],
        }

        # Collect all YAML/JSON files in the chart
        all_files = self._collect_chart_files(chart_dir)

        # Analyze each file for exposure patterns
        for file_path, file_type in all_files:
            exposure_info = self._analyze_file_for_exposure(
                file_path, chart_name, chart_dir, repo_path, file_type
            )
            if exposure_info:
                chart_info["exposure_found"] = True
                chart_info["containers"].extend(exposure_info)

        # Consolidate duplicate exposures
        if chart_info["containers"]:
            chart_info["containers"] = self._consolidate_exposures(
                chart_info["containers"]
            )

        return chart_info

    def _collect_chart_files(self, chart_dir: Path) -> List[tuple]:
        """Intelligently collect all relevant files in a chart directory."""
        files = []

        # Look for values files (any YAML file that might contain configuration)
        values_patterns = ["*.yaml", "*.yml"]

        # Search in the chart directory itself for values files
        for pattern in values_patterns:
            for file_path in chart_dir.glob(pattern):
                if file_path.is_file() and not self._is_ignored_file(file_path):
                    files.append((file_path, "values"))

        # Look for template files (Kubernetes manifests)
        template_patterns = ["*.yaml", "*.yml", "*.json"]

        templates_dir = chart_dir / "templates"
        if templates_dir.exists():
            for pattern in template_patterns:
                for file_path in templates_dir.glob(pattern):
                    if file_path.is_file() and not self._is_ignored_file(file_path):
                        files.append((file_path, "template"))

        # Also check if this is a Helm chart by looking for Chart.yaml
        chart_yaml = chart_dir / "Chart.yaml"
        if chart_yaml.exists():
            files.append((chart_yaml, "chart"))

        return files

    def _is_ignored_file(self, file_path: Path) -> bool:
        """Check if a file should be ignored based on intelligent patterns."""
        ignored_patterns = [
            r"\.git",
            r"\.DS_Store",
            r"\.swp$",
            r"\.tmp$",
            r"\.bak$",
            r"\.orig$",
            r"\.rej$",
            r"\.log$",
            r"\.md$",  # Documentation files
            r"\.txt$",
            r"\.example$",
            r"\.sample$",
            r"\.template$",
            r"\.values$",
            r"\.test$",
            r"\.spec$",
        ]

        file_str = str(file_path)
        return any(re.search(pattern, file_str) for pattern in ignored_patterns)

    def _analyze_file_for_exposure(
        self,
        file_path: Path,
        chart_name: str,
        chart_dir: Path,
        repo_path: Path,
        file_type: str,
    ) -> List[Dict[str, Any]]:
        """Analyze a single file for exposure patterns using intelligent regex matching."""
        containers = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse YAML/JSON content
            try:
                parsed_content = yaml.safe_load(content)
            except yaml.YAMLError:
                # If YAML parsing fails, analyze as raw text
                parsed_content = None

            # Analyze using regex patterns
            regex_exposures = self._analyze_with_regex_patterns(
                content, chart_name, chart_dir, repo_path, file_type
            )
            containers.extend(regex_exposures)

            # Analyze parsed content for additional patterns
            if parsed_content:
                parsed_exposures = self._analyze_parsed_content(
                    parsed_content, chart_name, chart_dir, repo_path, file_type
                )
                containers.extend(parsed_exposures)

        except Exception:
            # Log error but continue with other files
            pass

        return containers

    def _analyze_with_regex_patterns(
        self,
        content: str,
        chart_name: str,
        chart_dir: Path,
        repo_path: Path,
        file_type: str,
    ) -> List[Dict[str, Any]]:
        """Analyze content using regex patterns for exposure detection."""
        containers = []
        found_patterns = set()  # Track found patterns to avoid duplicates

        for pattern_name, pattern_info in self.exposure_patterns.items():
            matches = re.finditer(
                pattern_info["pattern"], content, re.MULTILINE | re.IGNORECASE
            )

            for match in matches:
                # Create a unique key for this pattern to avoid duplicates
                pattern_key = f"{pattern_name}:{match.group()}"

                if pattern_key not in found_patterns:
                    found_patterns.add(pattern_key)

                    # Extract additional context if available
                    context = self._extract_context(content, match.start(), match.end())

                    container_info = self._create_container_info(
                        chart_name,
                        pattern_info["description"],
                        context,
                        chart_dir,
                        repo_path,
                        pattern_info["score"],
                        pattern_info["level"],
                        file_type,
                    )
                    containers.append(container_info)

        return containers

    def _extract_context(
        self, content: str, start: int, end: int, context_lines: int = 3
    ) -> str:
        """Extract context around a regex match for better description."""
        lines = content.split("\n")
        match_line = content[:start].count("\n")

        start_line = max(0, match_line - context_lines)
        end_line = min(len(lines), match_line + context_lines + 1)

        context_lines = lines[start_line:end_line]
        return f"Lines {start_line + 1}-{end_line}: {' '.join(context_lines).strip()}"

    def _analyze_parsed_content(
        self,
        content: Any,
        chart_name: str,
        chart_dir: Path,
        repo_path: Path,
        file_type: str,
    ) -> List[Dict[str, Any]]:
        """Analyze parsed YAML/JSON content for additional exposure patterns."""
        containers = []

        # Recursively search for exposure patterns in nested structures
        self._search_recursive(
            content, chart_name, chart_dir, repo_path, file_type, containers
        )

        return containers

    def _search_recursive(
        self,
        obj: Any,
        chart_name: str,
        chart_dir: Path,
        repo_path: Path,
        file_type: str,
        containers: List[Dict[str, Any]],
        path: str = "",
    ):
        """Recursively search through parsed content for exposure patterns."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key

                # Check for specific exposure patterns
                if self._is_exposure_key(key, value):
                    container_info = self._create_container_info(
                        chart_name,
                        f"Config: {current_path}",
                        str(value),
                        chart_dir,
                        repo_path,
                        self._calculate_exposure_score(key, value),
                        self._determine_exposure_level(key, value),
                        file_type,
                    )
                    containers.append(container_info)

                # Continue recursion
                self._search_recursive(
                    value,
                    chart_name,
                    chart_dir,
                    repo_path,
                    file_type,
                    containers,
                    current_path,
                )

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]"
                self._search_recursive(
                    item,
                    chart_name,
                    chart_dir,
                    repo_path,
                    file_type,
                    containers,
                    current_path,
                )

    def _is_exposure_key(self, key: str, value: Any) -> bool:
        """Intelligently determine if a key-value pair indicates exposure."""
        exposure_indicators = {
            "type": ["LoadBalancer", "NodePort", "ClusterIP"],
            "enabled": [True, "true"],
            "host": lambda v: isinstance(v, str) and v != "localhost" and "." in v,
            "external": [True, "true"],
            "public": [True, "true"],
            "internet": [True, "true"],
            "expose": [True, "true"],
        }

        if key in exposure_indicators:
            expected_values = exposure_indicators[key]
            if callable(expected_values):
                return expected_values(value)
            return value in expected_values

        return False

    def _calculate_exposure_score(self, key: str, value: Any) -> int:
        """Calculate exposure score based on key and value."""
        if key == "type" and value in ["LoadBalancer", "NodePort"]:
            return 3
        elif key in ["enabled", "external", "public"] and value in [True, "true"]:
            return 2
        elif key == "host" and isinstance(value, str) and "." in value:
            return 2
        return 1

    def _determine_exposure_level(self, key: str, value: Any) -> str:
        """Determine exposure level based on key and value."""
        score = self._calculate_exposure_score(key, value)
        if score >= 3:
            return "HIGH"
        elif score >= 2:
            return "MEDIUM"
        return "LOW"

    def _create_container_info(
        self,
        chart_name: str,
        gateway_type: str,
        host: str,
        chart_dir: Path,
        repo_path: Path,
        score: int,
        level: str,
        env_name: str = "base",
    ) -> Dict[str, Any]:
        """Create container information structure."""
        # Create appropriate access chain based on gateway type
        if "LoadBalancer" in gateway_type or "NodePort" in gateway_type:
            access_chain = f"Internet -> {gateway_type} -> {chart_name} Service"
        elif "Ingress" in gateway_type and "Disabled" not in gateway_type:
            access_chain = f"Internet -> Ingress -> {chart_name} Service"
        elif "Gateway" in gateway_type:
            access_chain = f"Internet -> {gateway_type} -> {chart_name} Service"
        elif level == "LOW":
            access_chain = (
                "Internal Only - No internet access or HIGH container connections"
            )
        else:
            access_chain = f"Internet -> {gateway_type} -> {chart_name} Service"

        # Create unique container name for different environments
        container_name = f"{chart_name}-container"
        if env_name != "base":
            container_name = f"{chart_name}-{env_name}-container"

        return {
            "name": container_name,
            "chart": chart_name,
            "environment": env_name,
            "gateway_type": gateway_type,
            "host": host,
            "exposure_score": score,
            "exposure_level": level,
            "access_chain": access_chain,
            "dockerfile_path": "",
            "source_code_path": [],
            "exposes": [],
            "exposed_by": [],
            "depends_on": [],
        }

    def filter_redundant_base_containers(
        self, containers: List[Dict[str, Any]], chart_name: str
    ) -> List[Dict[str, Any]]:
        """Filter out redundant base containers when specific environment containers exist."""
        if not containers:
            return containers

        # Group containers by environment
        env_containers = {}
        for container in containers:
            env = container.get("environment", "base")
            if env not in env_containers:
                env_containers[env] = []
            env_containers[env].append(container)

        # If we have specific environment containers, filter out base
        if len(env_containers) > 1 and "base" in env_containers:
            # Keep only non-base containers
            filtered = []
            for env, containers_list in env_containers.items():
                if env != "base":
                    filtered.extend(containers_list)
            return filtered

        return containers

    def _consolidate_exposures(
        self, containers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Consolidate duplicate exposures into unique containers with comprehensive information."""
        if not containers:
            return containers

        # Group containers by chart name only
        consolidated = {}

        for container in containers:
            chart_name = container["chart"]

            if chart_name not in consolidated:
                consolidated[chart_name] = container.copy()
                consolidated[chart_name]["gateway_types"] = [container["gateway_type"]]
                consolidated[chart_name]["hosts"] = [container["host"]]
            else:
                # Merge information from duplicate
                existing = consolidated[chart_name]

                # Add new gateway type if not already present
                if container["gateway_type"] not in existing["gateway_types"]:
                    existing["gateway_types"].append(container["gateway_type"])

                # Add new host if not already present
                if container["host"] not in existing["hosts"]:
                    existing["hosts"].append(container["host"])

                # Take the highest exposure score
                existing["exposure_score"] = max(
                    existing["exposure_score"], container["exposure_score"]
                )

                # Update exposure level if needed
                if existing["exposure_score"] >= 3:
                    existing["exposure_level"] = "HIGH"
                elif existing["exposure_score"] >= 2:
                    existing["exposure_level"] = "MEDIUM"
                else:
                    existing["exposure_level"] = "LOW"

        # Convert consolidated data back to container format
        result = []
        for chart_name, consolidated_data in consolidated.items():
            container = consolidated_data.copy()

            # Create comprehensive gateway type description
            if len(consolidated_data["gateway_types"]) > 1:
                container[
                    "gateway_type"
                ] = f"Multiple: {', '.join(consolidated_data['gateway_types'])}"
            else:
                container["gateway_type"] = consolidated_data["gateway_types"][0]

            # Create comprehensive host description
            if len(consolidated_data["hosts"]) > 1:
                container[
                    "host"
                ] = f"Multiple configurations: {' | '.join(consolidated_data['hosts'])}"
            else:
                container["host"] = consolidated_data["hosts"][0]

            # Remove internal tracking fields
            del container["gateway_types"]
            del container["hosts"]

            result.append(container)

        return result
