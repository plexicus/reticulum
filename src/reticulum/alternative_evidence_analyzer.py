"""
Alternative Evidence Analyzer for Service Discovery

Provides evidence-based service discovery using alternative sources when Dockerfiles
are not available. This ensures comprehensive service mapping without guessing.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import re
import yaml
import json


class AlternativeEvidenceAnalyzer:
    """
    Analyzes alternative evidence sources for service discovery.

    Evidence sources include:
    - Docker Compose files
    - Kubernetes manifests
    - Build scripts (Makefile, build.sh)
    - CI/CD pipeline definitions
    - Package files (requirements.txt, package.json)
    - Chart directory structure analysis
    - Configuration file analysis
    """

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.evidence_sources = []

    def discover_services_without_dockerfiles(
        self, chart_dirs: List[Path], existing_services: Set[str]
    ) -> List[Dict[str, Any]]:
        """
        Discover services that don't have Dockerfiles using alternative evidence.

        Args:
            chart_dirs: List of Helm chart directories
            existing_services: Set of services already discovered via Dockerfiles

        Returns:
            List of discovered services with evidence metadata
        """
        discovered_services = []

        for chart_dir in chart_dirs:
            chart_name = chart_dir.name

            # Skip if service already exists
            if chart_name in existing_services:
                continue

            # Collect evidence from multiple sources
            evidence = self._collect_evidence_for_chart(chart_dir, chart_name)

            # Only create service if we have concrete evidence
            if evidence["has_concrete_evidence"]:
                service = self._create_service_from_evidence(chart_dir, chart_name, evidence)
                discovered_services.append(service)

        return discovered_services

    def _collect_evidence_for_chart(self, chart_dir: Path, chart_name: str) -> Dict[str, Any]:
        """Collect evidence from multiple sources for a chart."""
        evidence = {
            "chart_name": chart_name,
            "chart_dir": str(chart_dir.relative_to(self.repo_root)),
            "has_concrete_evidence": False,
            "evidence_sources": [],
            "source_paths": [],
            "confidence": "low"
        }

        # 1. Docker Compose Analysis
        compose_evidence = self._analyze_docker_compose(chart_dir, chart_name)
        if compose_evidence:
            evidence["evidence_sources"].extend(compose_evidence)
            evidence["has_concrete_evidence"] = True
            evidence["confidence"] = "high"

        # 2. Kubernetes Manifest Analysis
        k8s_evidence = self._analyze_kubernetes_manifests(chart_dir, chart_name)
        if k8s_evidence:
            evidence["evidence_sources"].extend(k8s_evidence)
            evidence["has_concrete_evidence"] = True
            if evidence["confidence"] == "low":
                evidence["confidence"] = "medium"

        # 3. Build Script Analysis
        build_evidence = self._analyze_build_scripts(chart_dir, chart_name)
        if build_evidence:
            evidence["evidence_sources"].extend(build_evidence)
            evidence["has_concrete_evidence"] = True
            if evidence["confidence"] == "low":
                evidence["confidence"] = "medium"

        # 4. CI/CD Pipeline Analysis
        cicd_evidence = self._analyze_cicd_pipelines(chart_dir, chart_name)
        if cicd_evidence:
            evidence["evidence_sources"].extend(cicd_evidence)
            evidence["has_concrete_evidence"] = True
            if evidence["confidence"] == "low":
                evidence["confidence"] = "medium"

        # 5. Package Analysis
        package_evidence = self._analyze_package_files(chart_dir, chart_name)
        if package_evidence:
            evidence["evidence_sources"].extend(package_evidence.get("evidence", []))
            evidence["source_paths"].extend(package_evidence.get("source_paths", []))
            evidence["has_concrete_evidence"] = True
            if evidence["confidence"] == "low":
                evidence["confidence"] = "medium"

        # 6. Chart Directory Structure Analysis
        chart_evidence = self._analyze_chart_structure(chart_dir, chart_name)
        if chart_evidence:
            evidence["evidence_sources"].extend(chart_evidence.get("evidence", []))
            evidence["source_paths"].extend(chart_evidence.get("source_paths", []))
            # Chart structure alone is not concrete evidence

        # 7. Configuration File Analysis
        config_evidence = self._analyze_configuration_files(chart_dir, chart_name)
        if config_evidence:
            evidence["evidence_sources"].extend(config_evidence.get("evidence", []))
            evidence["source_paths"].extend(config_evidence.get("source_paths", []))
            evidence["has_concrete_evidence"] = True
            if evidence["confidence"] == "low":
                evidence["confidence"] = "medium"

        return evidence

    def _analyze_docker_compose(self, chart_dir: Path, chart_name: str) -> List[Dict[str, Any]]:
        """Analyze Docker Compose files for service definitions."""
        evidence = []

        # Look for docker-compose.yml files in various locations
        compose_paths = [
            self.repo_root / "docker-compose.yml",
            self.repo_root / "docker-compose.yaml",
            chart_dir / "docker-compose.yml",
            chart_dir / "docker-compose.yaml",
        ]

        for compose_path in compose_paths:
            if compose_path.exists():
                try:
                    with open(compose_path, 'r') as f:
                        compose_data = yaml.safe_load(f)

                    if compose_data and 'services' in compose_data:
                        for service_name, service_config in compose_data['services'].items():
                            if service_name == chart_name or service_name.replace('-', '_') == chart_name.replace('-', '_'):
                                evidence.append({
                                    "type": "docker_compose",
                                    "file": str(compose_path.relative_to(self.repo_root)),
                                    "service_name": service_name,
                                    "build_context": service_config.get('build', {}).get('context', ''),
                                    "image": service_config.get('image', ''),
                                    "confidence": "high"
                                })
                except (yaml.YAMLError, IOError):
                    continue

        return evidence

    def _analyze_kubernetes_manifests(self, chart_dir: Path, chart_name: str) -> List[Dict[str, Any]]:
        """Analyze Kubernetes manifests for service definitions."""
        evidence = []

        # Look for Kubernetes manifests in chart templates
        templates_dir = chart_dir / "templates"
        if templates_dir.exists():
            for manifest_path in templates_dir.rglob("*.yaml"):
                try:
                    with open(manifest_path, 'r') as f:
                        manifest_data = yaml.safe_load(f)

                    if manifest_data:
                        # Check for Deployment, StatefulSet, DaemonSet
                        kind = manifest_data.get('kind', '')
                        if kind in ['Deployment', 'StatefulSet', 'DaemonSet']:
                            metadata = manifest_data.get('metadata', {})
                            name = metadata.get('name', '')

                            if name == chart_name or name.replace('-', '_') == chart_name.replace('-', '_'):
                                evidence.append({
                                    "type": "kubernetes_manifest",
                                    "file": str(manifest_path.relative_to(self.repo_root)),
                                    "kind": kind,
                                    "name": name,
                                    "confidence": "high"
                                })
                except (yaml.YAMLError, IOError):
                    continue

        return evidence

    def _analyze_build_scripts(self, chart_dir: Path, chart_name: str) -> List[Dict[str, Any]]:
        """Analyze build scripts for service definitions."""
        evidence = []

        # Look for common build scripts
        build_scripts = [
            self.repo_root / "Makefile",
            self.repo_root / "build.sh",
            chart_dir / "Makefile",
            chart_dir / "build.sh",
            chart_dir / "Dockerfile",  # Check if Dockerfile exists but wasn't found by DockerfileAnalyzer
        ]

        for script_path in build_scripts:
            if script_path.exists():
                evidence.append({
                    "type": "build_script",
                    "file": str(script_path.relative_to(self.repo_root)),
                    "confidence": "medium"
                })

        return evidence

    def _analyze_cicd_pipelines(self, chart_dir: Path, chart_name: str) -> List[Dict[str, Any]]:
        """Analyze CI/CD pipeline definitions for service mappings."""
        evidence = []

        # Look for common CI/CD configuration files
        cicd_patterns = [
            ".github/workflows/*.yml",
            ".github/workflows/*.yaml",
            ".gitlab-ci.yml",
            "Jenkinsfile",
        ]

        for pattern in cicd_patterns:
            for cicd_path in self.repo_root.glob(pattern):
                if cicd_path.exists():
                    # Basic pattern matching for service references
                    try:
                        with open(cicd_path, 'r') as f:
                            content = f.read()

                        # Look for chart/service name references
                        if chart_name in content or chart_name.replace('-', '_') in content:
                            evidence.append({
                                "type": "cicd_pipeline",
                                "file": str(cicd_path.relative_to(self.repo_root)),
                                "confidence": "medium"
                            })
                    except IOError:
                        continue

        return evidence

    def _analyze_package_files(self, chart_dir: Path, chart_name: str) -> Dict[str, Any]:
        """Enhanced package file analysis with flexible name matching."""
        evidence = []
        source_paths = []

        # Generate potential source directory names
        potential_names = self._generate_source_directory_names(chart_name)

        # Look for package files in potential source directories
        for source_name in potential_names:
            source_dirs = [
                self.repo_root / "source-code" / source_name,
                self.repo_root / "src" / source_name,
                self.repo_root / "apps" / source_name,
                self.repo_root / "services" / source_name,
                self.repo_root / source_name,
            ]

            for source_dir in source_dirs:
                if source_dir.exists():
                    # Check for package files
                    package_files = [
                        source_dir / "requirements.txt",
                        source_dir / "package.json",
                        source_dir / "pyproject.toml",
                        source_dir / "Cargo.toml",
                        source_dir / "go.mod",
                    ]

                    # Check for configuration files
                    config_patterns = [
                        "*.py",
                        "*.js",
                        "*.json",
                        "*.yaml",
                        "*.yml",
                    ]

                    # Check package files
                    for package_file in package_files:
                        if package_file.exists():
                            evidence.append({
                                "type": "package_file",
                                "file": str(package_file.relative_to(self.repo_root)),
                                "source_directory": str(source_dir.relative_to(self.repo_root)),
                                "confidence": "high"
                            })
                            source_paths.append(str(source_dir.relative_to(self.repo_root)) + "/")

                    # Check configuration files
                    for pattern in config_patterns:
                        for config_file in source_dir.glob(pattern):
                            if config_file.exists():
                                evidence.append({
                                    "type": "source_code_file",
                                    "file": str(config_file.relative_to(self.repo_root)),
                                    "source_directory": str(source_dir.relative_to(self.repo_root)),
                                    "confidence": "medium"
                                })
                                source_paths.append(str(source_dir.relative_to(self.repo_root)) + "/")

        return {
            "evidence": evidence,
            "source_paths": source_paths
        }

    def _generate_source_directory_names(self, chart_name: str) -> List[str]:
        """Generate potential source directory names from chart name."""
        names = [chart_name]

        # Remove common suffixes
        if chart_name.endswith('-stack'):
            names.append(chart_name[:-6])  # Remove '-stack'
        if chart_name.endswith('-service'):
            names.append(chart_name[:-8])  # Remove '-service'
        if chart_name.endswith('-app'):
            names.append(chart_name[:-4])  # Remove '-app'

        # Handle common patterns
        if '-' in chart_name:
            # Try without dashes
            names.append(chart_name.replace('-', ''))
            # Try with underscores
            names.append(chart_name.replace('-', '_'))

        # Remove duplicates
        return list(set(names))

    def _analyze_chart_structure(self, chart_dir: Path, chart_name: str) -> Dict[str, Any]:
        """Enhanced chart structure analysis with flexible name matching."""
        evidence = []
        source_paths = []

        # Generate potential source directory names
        potential_names = self._generate_source_directory_names(chart_name)

        # Look for source directories near the chart
        for source_name in potential_names:
            potential_source_dirs = [
                self.repo_root / "source-code" / source_name,
                self.repo_root / "src" / source_name,
                self.repo_root / "apps" / source_name,
                self.repo_root / "services" / source_name,
                chart_dir.parent / "source-code" / source_name,
                chart_dir.parent / "src" / source_name,
            ]

            for source_dir in potential_source_dirs:
                if source_dir.exists():
                    evidence.append({
                        "type": "chart_structure",
                        "source_directory": str(source_dir.relative_to(self.repo_root)),
                        "confidence": "low"
                    })
                    source_paths.append(str(source_dir.relative_to(self.repo_root)) + "/")

        return {
            "evidence": evidence,
            "source_paths": source_paths
        }

    def _analyze_configuration_files(self, chart_dir: Path, chart_name: str) -> Dict[str, Any]:
        """Enhanced configuration file analysis with Helm values support."""
        evidence = []
        source_paths = []

        # Look for configuration files that reference the chart/service
        config_patterns = [
            "config/*.yaml",
            "config/*.yml",
            "config/*.json",
            str(chart_dir.relative_to(self.repo_root) / "*.yaml"),
            str(chart_dir.relative_to(self.repo_root) / "*.yml"),
            str(chart_dir.relative_to(self.repo_root) / "*.json"),
        ]

        for pattern in config_patterns:
            for config_path in self.repo_root.glob(pattern):
                if config_path.exists():
                    try:
                        with open(config_path, 'r') as f:
                            if config_path.suffix in ['.yaml', '.yml']:
                                config_data = yaml.safe_load(f)
                            elif config_path.suffix == '.json':
                                config_data = json.load(f)
                            else:
                                continue

                        # Check if config references this chart/service
                        config_str = str(config_data)
                        if chart_name in config_str or chart_name.replace('-', '_') in config_str:
                            evidence.append({
                                "type": "configuration_file",
                                "file": str(config_path.relative_to(self.repo_root)),
                                "confidence": "medium"
                            })

                            # Try to extract source paths from config
                            source_dirs = self._extract_source_paths_from_config(config_data)
                            source_paths.extend(source_dirs)

                    except (yaml.YAMLError, json.JSONDecodeError, IOError):
                        continue

        # Add Helm values analysis
        helm_evidence = self._analyze_helm_values(chart_dir, chart_name)
        if helm_evidence:
            evidence.extend(helm_evidence)

        return {
            "evidence": evidence,
            "source_paths": source_paths
        }

    def _analyze_helm_values(self, chart_dir: Path, chart_name: str) -> List[Dict[str, Any]]:
        """Analyze Helm values.yaml files for additional evidence."""
        evidence = []

        # Look for values.yaml in chart directory
        values_files = [
            chart_dir / "values.yaml",
            chart_dir / "values.yml",
        ]

        for values_file in values_files:
            if values_file.exists():
                try:
                    with open(values_file, 'r') as f:
                        values_data = yaml.safe_load(f)

                    if values_data:
                        # Extract service information
                        service_info = {}
                        if 'service' in values_data:
                            service_info['service_type'] = values_data['service'].get('type', '')
                            service_info['service_port'] = values_data['service'].get('port', '')

                        # Extract component information
                        if 'components' in values_data:
                            components = values_data['components']
                            enabled_components = [
                                name for name, config in components.items()
                                if config.get('enabled', False)
                            ]
                            service_info['components'] = enabled_components

                        evidence.append({
                            "type": "helm_values",
                            "file": str(values_file.relative_to(self.repo_root)),
                            "service_info": service_info,
                            "confidence": "medium"
                        })

                except (yaml.YAMLError, IOError):
                    continue

        return evidence

    def _extract_source_paths_from_config(self, config_data: Any) -> List[str]:
        """Extract source paths from configuration data."""
        source_paths = []

        if isinstance(config_data, dict):
            # Look for common source path keys
            for key, value in config_data.items():
                if isinstance(value, str) and any(path_indicator in key.lower() for path_indicator in ['path', 'dir', 'source', 'src']):
                    if '/' in value and not value.startswith(('http://', 'https://')):
                        source_paths.append(value)
                elif isinstance(value, (dict, list)):
                    source_paths.extend(self._extract_source_paths_from_config(value))
        elif isinstance(config_data, list):
            for item in config_data:
                source_paths.extend(self._extract_source_paths_from_config(item))

        return source_paths

    def _create_service_from_evidence(
        self, chart_dir: Path, chart_name: str, evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a service definition from collected evidence."""

        return {
            "service_name": chart_name,
            "chart_name": chart_name,
            "chart_directory": str(chart_dir.relative_to(self.repo_root)),
            "dockerfile_path": "",  # No Dockerfile
            "source_code_paths": evidence.get("source_paths", []),
            "evidence_sources": evidence.get("evidence_sources", []),
            "confidence": evidence.get("confidence", "low"),
            "has_concrete_evidence": evidence.get("has_concrete_evidence", False),
            "discovery_method": "alternative_evidence",
            "risk_level": "LOW",  # Default risk level for services without Dockerfiles
        }