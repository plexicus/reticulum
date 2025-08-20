#!/usr/bin/env python3
"""
Reticulum - Exposure Scanner for Cloud Infrastructure Security Analysis

Main module containing the ExposureScanner class and CLI entry point.
Analyzes Helm charts to identify internet exposure and map source code paths.
"""

from pathlib import Path
from typing import Dict, Any

from .exposure_analyzer import ExposureAnalyzer
from .dockerfile_analyzer import DockerfileAnalyzer
from .dependency_analyzer import DependencyAnalyzer
from .path_consolidator import PathConsolidator
from .mermaid_builder import MermaidBuilder


class ExposureScanner:
    """Main scanner class that orchestrates the analysis process."""

    def __init__(self):
        self.results = {
            "repo_path": "",
            "scan_summary": {},
            "containers": [],
            "master_paths": {},
            "network_topology": {},
            "mermaid_diagram": "",
        }
        self.chart_containers = {}

        # Initialize specialized analyzers
        self.exposure_analyzer = ExposureAnalyzer()
        self.dockerfile_analyzer = DockerfileAnalyzer()
        self.dependency_analyzer = DependencyAnalyzer()
        self.path_consolidator = PathConsolidator()
        self.mermaid_builder = MermaidBuilder()

    def scan_repo(self, repo_path: str) -> Dict[str, Any]:
        """Scan a repository and return exposure analysis as JSON."""
        repo_path = Path(repo_path).resolve()

        if not repo_path.exists():
            raise FileNotFoundError(f"Repository path not found: {repo_path}")

        self.results["repo_path"] = str(repo_path)

        # Find Helm charts
        charts = list(repo_path.glob("**/Chart.yaml"))
        if not charts:
            self.results["scan_summary"] = {
                "error": "No Helm charts found in repository"
            }
            return self.results

        # Analyze each chart
        self.chart_containers = {}
        for chart_file in charts:
            chart_dir = chart_file.parent
            self.chart_containers[
                chart_dir.name
            ] = self.exposure_analyzer.analyze_chart(chart_dir, repo_path)

        # Add all found containers to results and filter out redundant base configurations
        for chart_name, chart_info in self.chart_containers.items():
            if chart_info["containers"]:
                # Filter out base containers with placeholder hosts if specific env containers exist
                filtered_containers = (
                    self.exposure_analyzer.filter_redundant_base_containers(
                        chart_info["containers"], chart_name
                    )
                )
                self.results["containers"].extend(filtered_containers)

        # Reconstruct containers from dependencies
        self.results[
            "containers"
        ] = self.dependency_analyzer.reconstruct_containers_from_dependencies(
            self.chart_containers, self.results["containers"], repo_path
        )

        # Detect internal containers
        self.results[
            "containers"
        ] = self.dependency_analyzer.detect_internal_containers(
            self.chart_containers, self.results["containers"], repo_path
        )

        # Enrich containers with Dockerfile information
        self._enrich_containers_with_dockerfile_info(repo_path)

        # Build summary
        self._build_summary()

        # Build master paths
        self.results["master_paths"] = self.path_consolidator.build_master_paths(
            self.results["containers"]
        )

        # Build network topology
        self._build_network_topology()

        # Build Mermaid diagram
        self.results["mermaid_diagram"] = self.mermaid_builder.build_diagram(
            self.results["containers"]
        )

        return self.results

    def _enrich_containers_with_dockerfile_info(self, repo_path: Path):
        """Enrich containers with Dockerfile and source path information."""
        for container in self.results["containers"]:
            chart_name = container["chart"]
            chart_dir = Path(repo_path) / self.chart_containers[chart_name]["path"]

            # Find Dockerfile
            dockerfile_path = self.dockerfile_analyzer.find_dockerfile(
                chart_dir, repo_path, chart_name
            )
            if dockerfile_path:
                container["dockerfile_path"] = str(
                    dockerfile_path.relative_to(repo_path)
                )
                container[
                    "source_code_path"
                ] = self.dockerfile_analyzer.parse_dockerfile_for_source_paths(
                    dockerfile_path, repo_path
                )

    def _build_summary(self):
        """Build scan summary."""
        containers = self.results["containers"]

        summary = {
            "total_containers": len(containers),
            "high_exposure": len(
                [c for c in containers if c["exposure_level"] == "HIGH"]
            ),
            "medium_exposure": len(
                [c for c in containers if c["exposure_level"] == "MEDIUM"]
            ),
            "low_exposure": len(
                [c for c in containers if c["exposure_level"] == "LOW"]
            ),
            "charts_analyzed": len(set(c["chart"] for c in containers)),
        }

        self.results["scan_summary"] = summary

    def _build_network_topology(self):
        """Build network topology information."""
        containers = self.results["containers"]

        topology = {
            "internet_gateways": [],
            "exposed_containers": [],
            "linked_containers": [],
            "internal_containers": [],
        }

        for container in containers:
            if container["exposure_level"] == "HIGH":
                topology["exposed_containers"].append(container["name"])
            elif container["exposure_level"] == "MEDIUM":
                topology["linked_containers"].append(container["name"])
            else:
                topology["internal_containers"].append(container["name"])

        self.results["network_topology"] = topology


def main():
    """Legacy main function for backward compatibility."""
    # Import here to avoid circular imports
    from .cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
