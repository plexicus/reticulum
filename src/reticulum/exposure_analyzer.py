"""
Exposure Analysis Module for Reticulum.

Handles the analysis of Helm charts and Kubernetes resources for exposure detection.
"""

from pathlib import Path
from typing import Dict, List, Any
import yaml


class ExposureAnalyzer:
    """Analyzes Helm charts and Kubernetes resources for exposure patterns."""

    def __init__(self):
        self.chart_containers = {}

    def analyze_chart(self, chart_dir: Path, repo_path: Path) -> Dict[str, Any]:
        """Analyze a Helm chart directory for exposure information."""
        chart_name = chart_dir.name
        chart_info = {
            "name": chart_name,
            "path": str(chart_dir.relative_to(repo_path)),
            "exposure_found": False,
            "containers": [],
        }

        # Check values.yaml and environment-specific files
        value_files = [
            ("base", chart_dir / "values.yaml"),
            ("dev", chart_dir / "dev.yaml"),
            ("prod", chart_dir / "prod.yaml"),
            ("staging", chart_dir / "staging.yaml"),
            ("stg", chart_dir / "stg.yaml"),
        ]

        for env_name, values_file in value_files:
            if values_file.exists():
                with open(values_file, "r") as f:
                    try:
                        values = yaml.safe_load(f)
                        if values:
                            exposure_info = self._analyze_exposure(
                                values, chart_name, chart_dir, repo_path, env_name
                            )
                            if exposure_info:
                                chart_info["exposure_found"] = True
                                chart_info["containers"].extend(exposure_info)
                    except yaml.YAMLError:
                        continue

        # Check templates directory for additional exposure patterns
        templates_dir = chart_dir / "templates"
        if templates_dir.exists():
            for template_file in templates_dir.glob("*.yaml"):
                if template_file.name == "ingress.yaml":
                    continue  # Already handled above

                with open(template_file, "r") as f:
                    try:
                        template = yaml.safe_load(f)
                        if template:
                            template_exposure = self._analyze_template_exposure(
                                template, chart_name, chart_dir, repo_path
                            )
                            if template_exposure:
                                chart_info["exposure_found"] = True
                                chart_info["containers"].extend(template_exposure)
                    except yaml.YAMLError:
                        continue

        return chart_info

    def _analyze_exposure(
        self,
        values: Dict[str, Any],
        chart_name: str,
        chart_dir: Path,
        repo_path: Path,
        env_name: str = "base",
    ) -> List[Dict[str, Any]]:
        """Analyze values.yaml for exposure patterns."""
        containers = []

        # Check for service exposure
        if "service" in values:
            service = values["service"]
            if isinstance(service, dict):
                if service.get("type") in ["LoadBalancer", "NodePort"]:
                    container_info = self._create_container_info(
                        chart_name,
                        "LoadBalancer/NodePort",
                        "Direct Internet Access",
                        chart_dir,
                        repo_path,
                        3,
                        "HIGH",
                        env_name,
                    )
                    containers.append(container_info)

        # Check for ingress (both enabled and configured)
        if "ingress" in values:
            ingress = values["ingress"]
            if isinstance(ingress, dict):
                hosts = ingress.get("hosts", [])

                # If ingress is explicitly enabled, it's HIGH exposure
                if ingress.get("enabled", False) and hosts:
                    for host in hosts:
                        if isinstance(host, dict) and host.get("host"):
                            host_name = host["host"]
                            if (
                                host_name != "chart-example.local"
                            ):  # Skip placeholder hosts
                                gateway_class = ingress.get("className", "Ingress")
                                container_info = self._create_container_info(
                                    chart_name,
                                    gateway_class,
                                    f"{host_name}",
                                    chart_dir,
                                    repo_path,
                                    3,
                                    "HIGH",
                                    env_name,
                                )
                                containers.append(container_info)

        # Check for external hosts
        if "external" in values:
            external = values["external"]
            if isinstance(external, dict) and external.get("host"):
                container_info = self._create_container_info(
                    chart_name,
                    "External",
                    f"External: {external['host']}",
                    chart_dir,
                    repo_path,
                    3,
                    "HIGH",
                    env_name,
                )
                containers.append(container_info)

        # Check for cloud-specific configurations
        for cloud in ["azure", "aws", "gcp"]:
            if cloud in values:
                cloud_config = values[cloud]
                if isinstance(cloud_config, dict):
                    if cloud_config.get("enabled", False) or cloud_config.get(
                        "expose", False
                    ):
                        container_info = self._create_container_info(
                            chart_name,
                            f"{cloud.upper()}",
                            f"{cloud.upper()} Cloud Exposure",
                            chart_dir,
                            repo_path,
                            3,
                            "HIGH",
                            env_name,
                        )
                        containers.append(container_info)

        # Check for direct port exposure
        if "ports" in values:
            ports = values["ports"]
            if isinstance(ports, list) and any(
                p.get("external", False) for p in ports if isinstance(p, dict)
            ):
                container_info = self._create_container_info(
                    chart_name,
                    "Direct Ports",
                    "External Port Exposure",
                    chart_dir,
                    repo_path,
                    3,
                    "HIGH",
                    env_name,
                )
                containers.append(container_info)

        return containers

    def _analyze_template_exposure(
        self,
        template: Dict[str, Any],
        chart_name: str,
        chart_dir: Path,
        repo_path: Path,
    ) -> List[Dict[str, Any]]:
        """Analyze template files for additional exposure patterns."""
        containers = []

        # Check for OpenShift Route
        if template.get("kind") == "Route":
            spec = template.get("spec", {})
            if spec.get("host"):
                container_info = self._create_container_info(
                    chart_name,
                    "OpenShift Route",
                    f"Route: {spec['host']}",
                    chart_dir,
                    repo_path,
                    3,
                    "HIGH",
                )
                containers.append(container_info)

        # Check for Istio Gateway
        if template.get("kind") == "Gateway":
            spec = template.get("spec", {})
            if spec.get("servers"):
                container_info = self._create_container_info(
                    chart_name,
                    "Istio Gateway",
                    "Istio Gateway Exposure",
                    chart_dir,
                    repo_path,
                    3,
                    "HIGH",
                )
                containers.append(container_info)

        return containers

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
        if "Ingress" in gateway_type and "Disabled" not in gateway_type:
            access_chain = f"Internet -> Ingress -> {chart_name} Service"
        elif "Ingress Template" in gateway_type or "Disabled" in gateway_type:
            access_chain = f"Internet -> Ingress (configurable) -> {chart_name} Service"
        elif "LoadBalancer" in gateway_type or "NodePort" in gateway_type:
            access_chain = f"Internet -> {gateway_type} -> {chart_name} Service"
        elif gateway_type == "Internal":
            access_chain = "Internal Only"
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
        """Filter out redundant base containers when environment-specific ones exist."""
        if not containers:
            return containers

        # Check if there are environment-specific containers (non-base)
        env_containers = [
            c for c in containers if c.get("environment", "base") != "base"
        ]
        base_containers = [
            c for c in containers if c.get("environment", "base") == "base"
        ]

        # If there are environment-specific containers, only keep base if they're different
        if env_containers:
            # Keep environment containers and any unique base containers
            return env_containers + base_containers

        # If no environment-specific containers, keep all base containers
        return containers
