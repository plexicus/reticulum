"""
Exposure Analysis Module for Reticulum.

Handles the analysis of Helm charts and Kubernetes resources for exposure detection.
"""

from pathlib import Path
from typing import Dict, List, Any
import yaml

from .network_policy_analyzer import NetworkPolicyAnalyzer


class ExposureAnalyzer:
    """Analyzes Helm charts and Kubernetes resources for exposure patterns."""

    def __init__(self):
        self.chart_containers = {}
        self.network_policy_analyzer = NetworkPolicyAnalyzer()

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
        """Analyze a Helm chart directory for exposure information using environment-specific analysis."""
        chart_name = chart_dir.name
        chart_info = {
            "name": chart_name,
            "path": str(chart_dir.relative_to(repo_path)),
            "exposure_found": False,
            "containers": [],
        }

        # Check values.yaml and environment-specific files (like original scanner)
        value_files = [
            ("base", chart_dir / "values.yaml"),
            ("dev", chart_dir / "dev.yaml"),
            ("prod", chart_dir / "prod.yaml"),
            ("staging", chart_dir / "staging.yaml"),
            ("stg", chart_dir / "stg.yaml"),
        ]

        for env_name, values_file in value_files:
            if values_file.exists():
                try:
                    with open(values_file, "r", encoding="utf-8") as f:
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

                try:
                    with open(template_file, "r", encoding="utf-8") as f:
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

        # Filter redundant base containers when environment-specific ones exist
        if chart_info["containers"]:
            chart_info["containers"] = self._filter_redundant_base_containers(
                chart_info["containers"], chart_name
            )

        return chart_info

    def _filter_redundant_base_containers(
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

    def _analyze_exposure(
        self,
        values: Dict[str, Any],
        chart_name: str,
        chart_dir: Path,
        repo_path: Path,
        env_name: str = "base",
    ) -> List[Dict[str, Any]]:
        """Analyze values.yaml for exposure patterns (like original scanner)."""
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
                        values,
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
                                    values,
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
                    values,
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
                            values,
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
                    values,
                )
                containers.append(container_info)

        return containers

    def _analyze_egress_capabilities(
        self, chart_name: str, values: Dict[str, Any], chart_dir: Path
    ) -> Dict[str, Any]:
        """
        Analyze egress capabilities for the service.

        Args:
            chart_name: Name of the chart
            values: Values from values.yaml
            chart_dir: Path to chart directory

        Returns:
            Egress analysis results
        """
        egress_analysis = {
            "egress_risk_level": "LOW",
            "has_internet_egress": False,
            "network_policies_analyzed": 0,
            "egress_rules_count": 0,
            "internet_cidrs_found": [],
            "recommendations": [],
        }

        # Analyze NetworkPolicy resources for this chart
        repo_path = chart_dir.parent
        network_policy_analysis = self.network_policy_analyzer.analyze_network_policies(
            str(repo_path)
        )

        # Update analysis with network policy findings
        egress_analysis["network_policies_analyzed"] = network_policy_analysis[
            "total_policies"
        ]
        egress_analysis["has_internet_egress"] = (
            network_policy_analysis["policies_with_internet_egress"] > 0
        )

        # Find policies that might affect this specific chart
        chart_policies = []
        for policy in network_policy_analysis["policies_analyzed"]:
            # Check if this policy applies to the current chart
            policy_file = policy.get("policy_file", "")
            if chart_name.lower() in policy_file.lower() or "templates" in policy_file:
                chart_policies.append(policy)
                egress_analysis["egress_rules_count"] += len(
                    policy.get("egress_rules", [])
                )
                egress_analysis["internet_cidrs_found"].extend(
                    policy.get("internet_cidrs_found", [])
                )

        # Determine egress risk level based on findings
        if egress_analysis["has_internet_egress"]:
            egress_analysis["egress_risk_level"] = "HIGH"
            egress_analysis["recommendations"].append(
                "Internet egress detected. Consider restricting egress to specific CIDR blocks."
            )
        elif egress_analysis["egress_rules_count"] > 5:
            egress_analysis["egress_risk_level"] = "MEDIUM"
            egress_analysis["recommendations"].append(
                "Complex egress rules detected. Review for unnecessary external access."
            )
        else:
            egress_analysis["egress_risk_level"] = "LOW"

        # Add recommendation if no NetworkPolicies found
        if egress_analysis["network_policies_analyzed"] == 0:
            egress_analysis["recommendations"].append(
                "No NetworkPolicy resources found. Consider implementing network policies "
                "to restrict pod-to-pod and external communication."
            )

        return egress_analysis

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
        values: Dict[str, Any] = None,
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

        # Analyze what this service exposes
        exposes = self._analyze_service_exposure(
            chart_name, gateway_type, values, chart_dir
        )

        # Analyze what this service depends on
        depends_on = self._analyze_service_dependencies(chart_name, values, chart_dir)

        # Analyze security context
        security_context = {}
        if values:
            security_context = self._analyze_security_context(values)

        # Analyze service account
        service_account = {}
        if values:
            service_account = self._analyze_service_account(values)

        # Analyze egress capabilities
        egress_analysis = self._analyze_egress_capabilities(
            chart_name, values, chart_dir
        )

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
            "exposes": exposes,
            "exposed_by": [],
            "depends_on": depends_on,
            "security_context": security_context,
            "service_account": service_account,
            "egress_analysis": egress_analysis,
        }

    def _analyze_service_exposure(
        self,
        chart_name: str,
        gateway_type: str,
        values: Dict[str, Any],
        chart_dir: Path,
    ) -> List[Dict[str, Any]]:
        """Analyze what this service exposes to the outside world."""
        exposes = []

        if not values:
            return exposes

        # Analyze ports exposed
        if "service" in values:
            service = values["service"]
            if isinstance(service, dict):
                port = service.get("port")
                target_port = service.get("targetPort")
                if port:
                    exposes.append(
                        {
                            "type": "port",
                            "value": port,
                            "protocol": "TCP",
                            "description": f"Service port {port}",
                        }
                    )
                if target_port:
                    exposes.append(
                        {
                            "type": "target_port",
                            "value": target_port,
                            "protocol": "TCP",
                            "description": f"Container port {target_port}",
                        }
                    )

        # Analyze ingress endpoints
        if "ingress" in values:
            ingress = values["ingress"]
            if isinstance(ingress, dict) and ingress.get("enabled", False):
                hosts = ingress.get("hosts", [])
                for host_config in hosts:
                    if isinstance(host_config, dict):
                        host_name = host_config.get("host", "")
                        paths = host_config.get("paths", [])
                        for path_config in paths:
                            if isinstance(path_config, dict):
                                path = path_config.get("path", "/")
                                path_type = path_config.get("pathType", "Prefix")
                                exposes.append(
                                    {
                                        "type": "endpoint",
                                        "value": f"{host_name}{path}",
                                        "protocol": "HTTP/HTTPS",
                                        "description": f"Ingress endpoint ({path_type})",
                                    }
                                )

        # Analyze LoadBalancer specific exposures
        if "LoadBalancer" in gateway_type:
            if "service" in values:
                service = values["service"]
                if isinstance(service, dict) and service.get("type") == "LoadBalancer":
                    exposes.append(
                        {
                            "type": "load_balancer",
                            "value": "external",
                            "protocol": "TCP",
                            "description": "External LoadBalancer access",
                        }
                    )

        # Analyze NodePort specific exposures
        if "NodePort" in gateway_type:
            if "service" in values:
                service = values["service"]
                if isinstance(service, dict) and service.get("type") == "NodePort":
                    exposes.append(
                        {
                            "type": "node_port",
                            "value": "external",
                            "protocol": "TCP",
                            "description": "External NodePort access",
                        }
                    )

        # Analyze cloud-specific exposures
        for cloud in ["azure", "aws", "gcp"]:
            if cloud in values:
                cloud_config = values[cloud]
                if isinstance(cloud_config, dict) and cloud_config.get(
                    "enabled", False
                ):
                    exposes.append(
                        {
                            "type": "cloud_service",
                            "value": cloud.upper(),
                            "protocol": "Cloud",
                            "description": f"{cloud.upper()} cloud service integration",
                        }
                    )

        return exposes

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

    def _analyze_capabilities(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Linux capabilities for privilege escalation."""
        dangerous_caps = {
            "SYS_ADMIN": "critical",
            "NET_ADMIN": "critical",
            "SYS_PTRACE": "high",
            "NET_RAW": "high",
            "SYS_MODULE": "critical",
        }

        caps = {"added": [], "dropped": [], "risk_level": "low"}

        if "securityContext" in values:
            sec_ctx = values["securityContext"]
            if "capabilities" in sec_ctx:
                added = sec_ctx["capabilities"].get("add", [])
                for cap in added:
                    if cap in dangerous_caps:
                        caps["added"].append(
                            {"capability": cap, "risk": dangerous_caps[cap]}
                        )

        return caps

    def _analyze_service_account(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze service account for cloud permissions."""
        sa_info = {
            "has_custom_sa": False,
            "cloud_role": None,
            "cloud_provider": None,
            "risk_indicators": [],
            "automount_token": False,
        }

        # Check for service account configuration
        if "serviceAccount" in values:
            sa = values["serviceAccount"]
            if isinstance(sa, dict):
                # Check if custom service account is created or specified
                if sa.get("create") or sa.get("name"):
                    sa_info["has_custom_sa"] = True

                # Check for cloud IAM annotations across different providers
                annotations = sa.get("annotations", {})
                for key, value in annotations.items():
                    # AWS IAM Role for Service Account (IRSA)
                    if "eks.amazonaws.com/role-arn" in key:
                        sa_info["cloud_role"] = value
                        sa_info["cloud_provider"] = "aws"
                        sa_info["risk_indicators"].append("aws_iam_binding")
                    # GCP Workload Identity
                    elif "iam.gke.io/gcp-service-account" in key:
                        sa_info["cloud_role"] = value
                        sa_info["cloud_provider"] = "gcp"
                        sa_info["risk_indicators"].append("gcp_workload_identity")
                    # Azure Workload Identity
                    elif "azure.workload.identity/client-id" in key:
                        sa_info["cloud_role"] = value
                        sa_info["cloud_provider"] = "azure"
                        sa_info["risk_indicators"].append("azure_workload_identity")
                    # Generic cloud IAM bindings
                    elif "role-arn" in key or "workload-identity" in key:
                        sa_info["cloud_role"] = value
                        sa_info["risk_indicators"].append("cloud_iam_binding")

                # Check for automountServiceAccountToken
                sa_info["automount_token"] = sa.get(
                    "automountServiceAccountToken", True
                )

        return sa_info

    def _extract_public_endpoints(self, container: Dict[str, Any]) -> List[str]:
        """Extract list of public endpoints."""
        endpoints = []

        for exposure in container.get("exposes", []):
            if exposure["type"] == "endpoint":
                endpoints.append(exposure["value"])

        return endpoints

    def _analyze_security_context(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze security context for privilege escalation risks."""
        security_risks = {
            "is_privileged": False,
            "allows_privilege_escalation": False,
            "runs_as_root": False,
            "host_network": False,
            "read_only_root_filesystem": True,  # Default to True (secure)
        }

        # Check securityContext
        if "securityContext" in values:
            sec_ctx = values["securityContext"]
            security_risks["is_privileged"] = sec_ctx.get("privileged", False)
            security_risks["allows_privilege_escalation"] = sec_ctx.get(
                "allowPrivilegeEscalation", True
            )
            security_risks["runs_as_root"] = sec_ctx.get("runAsUser") == 0
            security_risks["read_only_root_filesystem"] = sec_ctx.get(
                "readOnlyRootFilesystem", True
            )

        # Check hostNetwork
        security_risks["host_network"] = values.get("hostNetwork", False)

        # Analyze Linux capabilities
        security_risks["capabilities"] = self._analyze_capabilities(values)

        return security_risks

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
                    "base",
                    None,  # No values context for templates
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
                    "base",
                    None,  # No values context for templates
                )
                containers.append(container_info)

        return containers

    def _analyze_egress_capabilities(
        self, chart_name: str, values: Dict[str, Any], chart_dir: Path
    ) -> Dict[str, Any]:
        """
        Analyze egress capabilities for the service.

        Args:
            chart_name: Name of the chart
            values: Values from values.yaml
            chart_dir: Path to chart directory

        Returns:
            Egress analysis results
        """
        egress_analysis = {
            "egress_risk_level": "LOW",
            "has_internet_egress": False,
            "network_policies_analyzed": 0,
            "egress_rules_count": 0,
            "internet_cidrs_found": [],
            "recommendations": [],
        }

        # Analyze NetworkPolicy resources for this chart
        repo_path = chart_dir.parent
        network_policy_analysis = self.network_policy_analyzer.analyze_network_policies(
            str(repo_path)
        )

        # Update analysis with network policy findings
        egress_analysis["network_policies_analyzed"] = network_policy_analysis[
            "total_policies"
        ]
        egress_analysis["has_internet_egress"] = (
            network_policy_analysis["policies_with_internet_egress"] > 0
        )

        # Find policies that might affect this specific chart
        chart_policies = []
        for policy in network_policy_analysis["policies_analyzed"]:
            # Check if this policy applies to the current chart
            policy_file = policy.get("policy_file", "")
            if chart_name.lower() in policy_file.lower() or "templates" in policy_file:
                chart_policies.append(policy)
                egress_analysis["egress_rules_count"] += len(
                    policy.get("egress_rules", [])
                )
                egress_analysis["internet_cidrs_found"].extend(
                    policy.get("internet_cidrs_found", [])
                )

        # Determine egress risk level based on findings
        if egress_analysis["has_internet_egress"]:
            egress_analysis["egress_risk_level"] = "HIGH"
            egress_analysis["recommendations"].append(
                "Internet egress detected. Consider restricting egress to specific CIDR blocks."
            )
        elif egress_analysis["egress_rules_count"] > 5:
            egress_analysis["egress_risk_level"] = "MEDIUM"
            egress_analysis["recommendations"].append(
                "Complex egress rules detected. Review for unnecessary external access."
            )
        else:
            egress_analysis["egress_risk_level"] = "LOW"

        # Add recommendation if no NetworkPolicies found
        if egress_analysis["network_policies_analyzed"] == 0:
            egress_analysis["recommendations"].append(
                "No NetworkPolicy resources found. Consider implementing network policies "
                "to restrict pod-to-pod and external communication."
            )

        return egress_analysis
