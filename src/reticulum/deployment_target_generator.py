"""
Deployment Target Generator for Unified Pareto Strategy

Generates deployment targets based on file changes and the reverse ownership index.
This is the final phase of the strategy - the execution logic.
"""

from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class DeploymentTarget:
    """Represents a deployment target with metadata."""

    chart_name: str
    affected_services: List[str]
    changed_files: List[Path]
    confidence: float


class DeploymentTargetGenerator:
    """
    Generates deployment targets based on file changes.

    Implements Phase 4 of the Unified Pareto Strategy:
    - Input: File path (e.g., `libs/shared/math.py`)
    - Resolution: Directory lookup (`libs/shared/`)
    - Output: Service tokens `[payment, orders]`
    - Final: Resolve to charts `[charts/payment, charts/orders]`
    """

    def __init__(self, reverse_ownership_index, chart_resolver):
        """
        Initialize DeploymentTargetGenerator.

        Args:
            reverse_ownership_index: ReverseOwnershipIndex instance
            chart_resolver: ChartResolver instance
        """
        self.reverse_ownership_index = reverse_ownership_index
        self.chart_resolver = chart_resolver

    def generate_deployment_targets(
        self, changed_files: List[Path]
    ) -> List[DeploymentTarget]:
        """
        Generate deployment targets for changed files.

        Args:
            changed_files: List of changed file paths

        Returns:
            List of DeploymentTarget objects
        """
        # Step 1: Find affected services for each changed file
        affected_services = self.reverse_ownership_index.find_services_by_file_change(
            changed_files
        )

        # Step 2: Group changed files by service
        service_to_files = self._group_files_by_service(affected_services)

        # Step 3: Resolve services to charts
        chart_targets = self._resolve_services_to_charts(service_to_files)

        # Step 4: Create deployment targets
        deployment_targets = self._create_deployment_targets(chart_targets)

        return deployment_targets

    def _group_files_by_service(
        self, affected_services: Dict[Path, List[str]]
    ) -> Dict[str, List[Path]]:
        """
        Group changed files by service token.

        Args:
            affected_services: Dictionary of file -> service tokens

        Returns:
            Dictionary of service token -> list of files
        """
        service_to_files = {}

        for file_path, services in affected_services.items():
            for service in services:
                if service not in service_to_files:
                    service_to_files[service] = []
                service_to_files[service].append(file_path)

        return service_to_files

    def _resolve_services_to_charts(
        self, service_to_files: Dict[str, List[Path]]
    ) -> Dict[str, dict]:
        """
        Resolve services to charts with metadata.

        Args:
            service_to_files: Dictionary of service -> files

        Returns:
            Dictionary of chart -> metadata
        """
        chart_targets = {}

        for service_token, files in service_to_files.items():
            chart_name = self.chart_resolver.resolve_service_to_chart(service_token)

            if chart_name:
                if chart_name not in chart_targets:
                    chart_targets[chart_name] = {
                        "services": set(),
                        "files": set(),
                        "confidence": 0.0,
                    }

                chart_targets[chart_name]["services"].add(service_token)
                chart_targets[chart_name]["files"].update(files)

                # Calculate confidence based on mapping quality
                mapping = (
                    self.chart_resolver.service_chart_registry.get_mapping_details(
                        service_token
                    )
                )
                if mapping:
                    chart_targets[chart_name]["confidence"] = max(
                        chart_targets[chart_name]["confidence"], mapping.confidence
                    )

        return chart_targets

    def _create_deployment_targets(
        self, chart_targets: Dict[str, dict]
    ) -> List[DeploymentTarget]:
        """
        Create DeploymentTarget objects from chart targets.

        Args:
            chart_targets: Dictionary of chart -> metadata

        Returns:
            List of DeploymentTarget objects
        """
        deployment_targets = []

        for chart_name, target_data in chart_targets.items():
            target = DeploymentTarget(
                chart_name=chart_name,
                affected_services=list(target_data["services"]),
                changed_files=list(target_data["files"]),
                confidence=target_data["confidence"],
            )
            deployment_targets.append(target)

        return deployment_targets

    def get_deployment_summary(
        self, deployment_targets: List[DeploymentTarget]
    ) -> Dict[str, any]:
        """
        Get summary of deployment targets.

        Args:
            deployment_targets: List of DeploymentTarget objects

        Returns:
            Dictionary with deployment summary
        """
        total_charts = len(deployment_targets)
        total_services = sum(
            len(target.affected_services) for target in deployment_targets
        )
        total_files = sum(len(target.changed_files) for target in deployment_targets)

        # Calculate average confidence
        avg_confidence = (
            sum(target.confidence for target in deployment_targets) / total_charts
            if total_charts > 0
            else 0
        )

        # Get unique services and files
        all_services = set()
        all_files = set()
        for target in deployment_targets:
            all_services.update(target.affected_services)
            all_files.update(target.changed_files)

        return {
            "total_charts": total_charts,
            "total_services": total_services,
            "total_files": total_files,
            "unique_services": len(all_services),
            "unique_files": len(all_files),
            "avg_confidence": avg_confidence,
            "charts": [target.chart_name for target in deployment_targets],
            "services": list(all_services),
        }

    def generate_deployment_plan(
        self, changed_files: List[Path], min_confidence: float = 0.5
    ) -> Dict[str, any]:
        """
        Generate a complete deployment plan.

        Args:
            changed_files: List of changed file paths
            min_confidence: Minimum confidence threshold

        Returns:
            Dictionary with complete deployment plan
        """
        # Generate deployment targets
        deployment_targets = self.generate_deployment_targets(changed_files)

        # Filter by confidence
        filtered_targets = [
            target
            for target in deployment_targets
            if target.confidence >= min_confidence
        ]

        # Generate summary
        summary = self.get_deployment_summary(filtered_targets)

        return {
            "deployment_targets": filtered_targets,
            "summary": summary,
            "filtered_out": len(deployment_targets) - len(filtered_targets),
            "min_confidence": min_confidence,
        }

    def analyze_impact(self, changed_files: List[Path]) -> Dict[str, any]:
        """
        Analyze the impact of file changes.

        Args:
            changed_files: List of changed file paths

        Returns:
            Dictionary with impact analysis
        """
        # Find affected services
        affected_services = self.reverse_ownership_index.find_services_by_file_change(
            changed_files
        )

        # Calculate impact metrics
        total_files = len(changed_files)
        files_with_owners = len(affected_services)
        orphaned_files = total_files - files_with_owners

        # Get unique services affected
        all_services = set()
        for services in affected_services.values():
            all_services.update(services)

        # Resolve services to charts
        unique_charts = self.chart_resolver.get_unique_charts(list(all_services))

        return {
            "total_changed_files": total_files,
            "files_with_owners": files_with_owners,
            "orphaned_files": orphaned_files,
            "affected_services": list(all_services),
            "affected_charts": list(unique_charts),
            "file_impact_ratio": (
                files_with_owners / total_files if total_files > 0 else 0
            ),
            "service_impact_ratio": (
                len(all_services)
                / len(self.chart_resolver.service_chart_registry.service_to_chart)
                if self.chart_resolver.service_chart_registry.service_to_chart
                else 0
            ),
        }
