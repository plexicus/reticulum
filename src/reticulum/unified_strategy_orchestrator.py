"""
Unified Strategy Orchestrator for Reticulum

Orchestrates all components of the Unified Pareto Strategy to provide
comprehensive service identification, territory claiming, and deployment targeting.
"""

from pathlib import Path
from typing import Dict, List, Any

from .service_registry import ServiceRegistry
from .dockerfile_parser import DockerfileParser
from .reverse_ownership_index import ReverseOwnershipIndex
from .helm_chart_finder import HelmChartFinder
from .service_chart_registry import ServiceChartRegistry
from .chart_resolver import ChartResolver
from .deployment_target_generator import DeploymentTargetGenerator


class UnifiedStrategyOrchestrator:
    """
    Orchestrator for the Unified Pareto Strategy.

    Coordinates all phases of the strategy:
    - Phase 1: Service Identification
    - Phase 2: Territory Claiming
    - Phase 3: Infrastructure Bridging
    - Phase 4: Execution Logic
    """

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

        # Initialize all components
        self.service_registry = ServiceRegistry()
        self.dockerfile_parser = DockerfileParser()
        self.reverse_ownership_index = ReverseOwnershipIndex()
        self.helm_chart_finder = HelmChartFinder(repo_root)
        self.service_chart_registry = ServiceChartRegistry()
        self.chart_resolver = ChartResolver(self.service_chart_registry)
        self.deployment_target_generator = DeploymentTargetGenerator(
            self.reverse_ownership_index, self.chart_resolver
        )

    def execute_full_strategy(self) -> Dict[str, Any]:
        """
        Execute the complete Unified Pareto Strategy.

        Returns:
            Comprehensive analysis results
        """
        results = {}

        # Phase 1: Service Identification
        results["phase_1_service_identification"] = self._execute_phase_1()

        # Phase 2: Territory Claiming
        results["phase_2_territory_claiming"] = self._execute_phase_2()

        # Phase 3: Infrastructure Bridging
        results["phase_3_infrastructure_bridging"] = self._execute_phase_3()

        # Phase 4: Execution Logic (ready for queries)
        results["phase_4_execution_logic"] = self._execute_phase_4()

        # Overall strategy summary
        results["strategy_summary"] = self._generate_strategy_summary(results)

        return results

    def _execute_phase_1(self) -> Dict[str, Any]:
        """Execute Phase 1: Service Identification."""
        # Discover all Dockerfiles
        dockerfiles = self._discover_dockerfiles()

        # Register services
        for dockerfile_path in dockerfiles:
            self.service_registry.register_service_from_dockerfile(
                dockerfile_path, self.repo_root
            )

        return {
            "total_dockerfiles": len(dockerfiles),
            "total_services": len(self.service_registry.get_all_services()),
            "services": [
                {
                    "token": service.token,
                    "dockerfile": str(service.dockerfile_path),
                    "parent_directory": str(service.parent_directory),
                }
                for service in self.service_registry.get_all_services()
            ],
        }

    def _execute_phase_2(self) -> Dict[str, Any]:
        """Execute Phase 2: Territory Claiming."""
        dockerfiles = self._discover_dockerfiles()

        for dockerfile_path in dockerfiles:
            # Convert to relative path for service registry lookup
            relative_dockerfile_path = dockerfile_path.relative_to(self.repo_root)
            service_info = self.service_registry.get_service_by_dockerfile(
                relative_dockerfile_path
            )
            if service_info:
                service_token = service_info.token

                # Claim implicit territory
                self.reverse_ownership_index.claim_implicit_territory(
                    service_token, service_info.parent_directory
                )

                # Claim explicit territory
                source_paths = self.dockerfile_parser.parse_dockerfile(
                    dockerfile_path, dockerfile_path.parent, self.repo_root
                )
                self.reverse_ownership_index.claim_explicit_territory(
                    service_token, source_paths
                )

        return {
            "ownership_statistics": self.reverse_ownership_index.get_index_statistics(),
            "shared_folders": self.reverse_ownership_index.get_shared_folders(),
            "service_coverage": {
                service.token: self.reverse_ownership_index.get_service_coverage(
                    service.token
                )
                for service in self.service_registry.get_all_services()
            },
        }

    def _execute_phase_3(self) -> Dict[str, Any]:
        """Execute Phase 3: Infrastructure Bridging."""
        service_tokens = self.service_registry.get_service_tokens()

        # Find charts for all services
        chart_mappings = self.helm_chart_finder.batch_find_charts(service_tokens)

        # Register mappings
        for service_token, chart_name in chart_mappings.items():
            if chart_name:
                # Determine mapping type and confidence
                mapping_type = "convention"
                confidence = 1.0

                # Check if it's a heuristic match
                if not self._is_convention_match(service_token, chart_name):
                    mapping_type = "heuristic"
                    confidence = 0.8

                self.service_chart_registry.register_mapping(
                    service_token, chart_name, confidence, mapping_type, "auto"
                )

        return {
            "chart_mappings": chart_mappings,
            "registry_statistics": self.service_chart_registry.get_registry_statistics(),
            "mapping_validation": self.chart_resolver.validate_service_chart_mappings(
                service_tokens
            ),
        }

    def _execute_phase_4(self) -> Dict[str, Any]:
        """Execute Phase 4: Execution Logic."""
        # Phase 4 is ready for queries - return readiness status
        service_tokens = self.service_registry.get_service_tokens()

        return {
            "readiness": "complete",
            "total_services": len(service_tokens),
            "mapped_services": len(
                [
                    t
                    for t in service_tokens
                    if self.service_chart_registry.get_chart_for_service(t)
                ]
            ),
            "reverse_ownership_ready": True,
            "chart_resolution_ready": True,
            "deployment_targeting_ready": True,
        }

    def _discover_dockerfiles(self) -> List[Path]:
        """Discover all Dockerfiles in repository."""
        patterns = ["**/*Dockerfile*", "**/Dockerfile", "**/dockerfile*"]
        dockerfiles = []

        for pattern in patterns:
            for dockerfile_path in self.repo_root.glob(pattern):
                if dockerfile_path.is_file():
                    dockerfiles.append(dockerfile_path)

        return list(set(dockerfiles))

    def _is_convention_match(self, service_token: str, chart_name: str) -> bool:
        """Check if service-chart mapping is a convention match."""
        return service_token.lower() == chart_name.lower()

    def _generate_strategy_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall strategy summary."""
        phase_1 = results["phase_1_service_identification"]
        phase_2 = results["phase_2_territory_claiming"]
        phase_3 = results["phase_3_infrastructure_bridging"]

        total_services = phase_1["total_services"]
        ownership_stats = phase_2["ownership_statistics"]
        registry_stats = phase_3["registry_statistics"]

        # Calculate mapping rate
        mapping_rate = (
            registry_stats["total_services"] / total_services
            if total_services > 0
            else 0
        )

        return {
            "total_services": total_services,
            "total_dockerfiles": phase_1["total_dockerfiles"],
            "total_folders_claimed": ownership_stats["total_folders"],
            "shared_folders": ownership_stats["shared_folders"],
            "mapped_services": registry_stats["total_services"],
            "mapping_rate": mapping_rate,
            "strategy_status": "complete",
        }

    def query_deployment_targets(self, changed_files: List[Path]) -> Dict[str, Any]:
        """
        Query deployment targets for changed files.

        Args:
            changed_files: List of changed file paths

        Returns:
            Deployment targets and analysis
        """
        # Convert all paths to be relative to repo root
        relative_changed_files = []
        for file_path in changed_files:
            if file_path.is_absolute():
                # Convert absolute path to relative
                relative_changed_files.append(file_path.relative_to(self.repo_root))
            else:
                # Path is relative, but we need to make it relative to repo root
                # Try to resolve it relative to repo root
                absolute_path = self.repo_root / file_path
                if absolute_path.exists():
                    relative_changed_files.append(file_path)
                else:
                    # If the path doesn't exist when resolved, try to find the correct relative path
                    # by removing any leading parts that match repo root structure
                    file_parts = list(file_path.parts)
                    repo_parts = list(self.repo_root.parts)

                    # Remove matching leading parts
                    while file_parts and repo_parts and file_parts[0] == repo_parts[0]:
                        file_parts.pop(0)
                        repo_parts.pop(0)

                    if file_parts:
                        relative_changed_files.append(Path(*file_parts))
                    else:
                        relative_changed_files.append(file_path)

        # Generate deployment plan
        deployment_plan = self.deployment_target_generator.generate_deployment_plan(
            relative_changed_files
        )

        # Analyze impact
        impact_analysis = self.deployment_target_generator.analyze_impact(
            relative_changed_files
        )

        return {"deployment_plan": deployment_plan, "impact_analysis": impact_analysis}

    def get_owners_for_file(self, file_path: Path) -> List[str]:
        """
        Get service owners for a file.

        Args:
            file_path: File path

        Returns:
            List of service tokens
        """
        # Convert path to be relative to repo root
        if file_path.is_absolute():
            file_path = file_path.relative_to(self.repo_root)
        else:
            # Path is relative, but we need to make it relative to repo root
            # Try to resolve it relative to repo root
            absolute_path = self.repo_root / file_path
            if not absolute_path.exists():
                # If the path doesn't exist when resolved, try to find the correct relative path
                # by removing any leading parts that match repo root structure
                file_parts = list(file_path.parts)
                repo_parts = list(self.repo_root.parts)

                # Remove matching leading parts
                while file_parts and repo_parts and file_parts[0] == repo_parts[0]:
                    file_parts.pop(0)
                    repo_parts.pop(0)

                if file_parts:
                    file_path = Path(*file_parts)

        return self.reverse_ownership_index.get_owners_for_path(file_path)

    def get_charts_for_file(self, file_path: Path) -> List[str]:
        """
        Get charts for a file.

        Args:
            file_path: File path

        Returns:
            List of chart names
        """
        service_tokens = self.get_owners_for_file(file_path)
        return list(self.chart_resolver.get_unique_charts(service_tokens))

    def get_strategy_statistics(self) -> Dict[str, Any]:
        """Get comprehensive strategy statistics."""
        return {
            "service_registry": {
                "total_services": len(self.service_registry.get_all_services()),
                "services": [
                    {
                        "token": service.token,
                        "dockerfile": str(service.dockerfile_path),
                        "chart": self.service_chart_registry.get_chart_for_service(
                            service.token
                        ),
                    }
                    for service in self.service_registry.get_all_services()
                ],
            },
            "ownership_index": self.reverse_ownership_index.get_index_statistics(),
            "chart_registry": self.service_chart_registry.get_registry_statistics(),
            "deployment_readiness": {
                "can_generate_targets": True,
                "total_charts": len(self.helm_chart_finder.find_all_charts()),
                "mapping_coverage": len(
                    [
                        s
                        for s in self.service_registry.get_all_services()
                        if self.service_chart_registry.get_chart_for_service(s.token)
                    ]
                ),
            },
        }
