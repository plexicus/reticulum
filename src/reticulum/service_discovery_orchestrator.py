"""
Service Discovery Orchestrator

Orchestrates service discovery using multiple evidence sources:
- Dockerfile-based discovery (primary)
- Alternative evidence sources (fallback)
- Evidence-based mapping without guessing
"""

from pathlib import Path
from typing import List, Dict, Any, Set

from .dockerfile_analyzer import DockerfileAnalyzer
from .service_registry import ServiceRegistry
from .alternative_evidence_analyzer import AlternativeEvidenceAnalyzer


class ServiceDiscoveryOrchestrator:
    """
    Orchestrates comprehensive service discovery using multiple evidence sources.

    Combines:
    - Dockerfile-based service discovery (high confidence)
    - Alternative evidence sources for Dockerfile-less services (medium confidence)
    - Evidence-based mapping without directory name guessing
    """

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.dockerfile_analyzer = DockerfileAnalyzer()
        self.service_registry = ServiceRegistry()
        self.alternative_evidence_analyzer = AlternativeEvidenceAnalyzer(repo_root)

    def discover_all_services(self, chart_dirs: List[Path]) -> Dict[str, Any]:
        """
        Discover all services using multiple evidence sources.

        Args:
            chart_dirs: List of Helm chart directories

        Returns:
            Comprehensive service discovery results
        """
        discovery_results = {
            "dockerfile_services": [],
            "alternative_evidence_services": [],
            "unmapped_charts": [],
            "summary": {
                "total_charts": len(chart_dirs),
                "dockerfile_services": 0,
                "alternative_evidence_services": 0,
                "unmapped_charts": 0,
            },
        }

        # Phase 1: Dockerfile-based discovery
        dockerfile_services = self._discover_dockerfile_services(chart_dirs)
        discovery_results["dockerfile_services"] = dockerfile_services
        discovery_results["summary"]["dockerfile_services"] = len(dockerfile_services)

        # Get set of services already discovered via Dockerfiles
        existing_services = {service["service_name"] for service in dockerfile_services}

        # Phase 2: Alternative evidence discovery for remaining charts
        remaining_charts = [
            chart_dir
            for chart_dir in chart_dirs
            if chart_dir.name not in existing_services
        ]

        alternative_services = self._discover_alternative_evidence_services(
            remaining_charts, existing_services
        )
        discovery_results["alternative_evidence_services"] = alternative_services
        discovery_results["summary"]["alternative_evidence_services"] = len(
            alternative_services
        )

        # Phase 3: Identify unmapped charts
        all_discovered_services = existing_services.union(
            {service["service_name"] for service in alternative_services}
        )
        unmapped_charts = [
            chart_dir
            for chart_dir in chart_dirs
            if chart_dir.name not in all_discovered_services
        ]
        discovery_results["unmapped_charts"] = [
            {
                "chart_name": chart_dir.name,
                "chart_directory": str(chart_dir.relative_to(self.repo_root)),
                "reason": "No evidence found for service mapping",
            }
            for chart_dir in unmapped_charts
        ]
        discovery_results["summary"]["unmapped_charts"] = len(unmapped_charts)

        return discovery_results

    def _discover_dockerfile_services(
        self, chart_dirs: List[Path]
    ) -> List[Dict[str, Any]]:
        """Discover services using Dockerfile-based evidence."""
        services = []

        for chart_dir in chart_dirs:
            chart_name = chart_dir.name

            # Find Dockerfile using comprehensive discovery strategies
            dockerfile_path = self.dockerfile_analyzer.find_dockerfile(
                chart_dir, self.repo_root, chart_name
            )

            if dockerfile_path:
                # Register service in service registry
                service_token = self.service_registry.register_service_from_dockerfile(
                    dockerfile_path, self.repo_root
                )

                # Set chart name for the service
                self.service_registry.set_chart_name(service_token, chart_name)

                # Analyze Dockerfile for source paths
                dockerfile_analysis = (
                    self.dockerfile_analyzer.analyze_dockerfile_with_build_context(
                        dockerfile_path, self.repo_root, chart_name
                    )
                )

                # Create service definition
                service = {
                    "service_name": service_token,
                    "chart_name": chart_name,
                    "dockerfile_path": str(dockerfile_path.relative_to(self.repo_root)),
                    "source_code_paths": dockerfile_analysis.get(
                        "combined_source_paths", []
                    ),
                    "build_context_analysis": dockerfile_analysis.get(
                        "build_context_analysis", {}
                    ),
                    "discovery_method": "dockerfile",
                    "confidence": "high",
                    "risk_level": "MEDIUM",  # Default, will be refined by exposure analysis
                }

                services.append(service)

        return services

    def _discover_alternative_evidence_services(
        self, chart_dirs: List[Path], existing_services: Set[str]
    ) -> List[Dict[str, Any]]:
        """Discover services using alternative evidence sources."""

        return self.alternative_evidence_analyzer.discover_services_without_dockerfiles(
            chart_dirs, existing_services
        )

    def get_all_services(self) -> List[Dict[str, Any]]:
        """Get all discovered services (Dockerfile + alternative evidence)."""
        # This would combine services from both discovery methods
        # For now, return empty list - will be implemented when integrated with main flow
        return []

    def get_service_mapping_summary(self) -> Dict[str, Any]:
        """Get summary of service discovery results."""
        # This would provide detailed statistics on discovery success
        return {
            "total_services": len(self.service_registry.get_all_services()),
            "service_tokens": self.service_registry.get_service_tokens(),
        }

    def validate_service_mappings(self) -> Dict[str, Any]:
        """Validate service mappings and identify potential issues."""
        validation_results = {"warnings": [], "errors": [], "suggestions": []}

        # Check for service token mismatches
        for service in self.service_registry.get_all_services():
            if service.chart_name and service.token != service.chart_name:
                validation_results["warnings"].append(
                    {
                        "type": "service_token_mismatch",
                        "service_token": service.token,
                        "chart_name": service.chart_name,
                        "message": f"Service token '{service.token}' doesn't match chart name '{service.chart_name}'",
                    }
                )

        # Check for services with no source paths
        # This would require integration with the main service analysis

        return validation_results
