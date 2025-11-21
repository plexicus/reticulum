"""
Security Findings Mapper

Maps security findings from Trivy and Semgrep to reticulum services
based on Dockerfile paths and source code paths.
"""

from pathlib import Path
from typing import Dict, Any, List

from .build_context_analyzer import BuildContextAnalyzer
from .path_resolution_engine import PathResolutionEngine


class FindingsMapper:
    """Maps security findings to services based on exposure analysis."""

    def __init__(self, prioritization_report: Dict[str, Any], repo_path: str):
        self.prioritization_report = prioritization_report
        self.repo_path = Path(repo_path)
        self.services_by_path = self._build_service_path_mapping()

        # Build enhanced service mapping table
        self.service_mapping_table = self._build_service_mapping_table()

        # Initialize path resolution engine
        self.path_resolution_engine = PathResolutionEngine(
            self.service_mapping_table, self.repo_path
        )

    def _build_service_path_mapping(self) -> Dict[str, List[Dict[str, Any]]]:
        """Build mapping of source paths to services."""
        path_mapping = {}
        mapping_log = []

        for service in self.prioritization_report.get("prioritized_services", []):
            service_name = service.get("service_name", "unknown")

            # Map Dockerfile path
            dockerfile_path = service.get("dockerfile_path", "")
            if dockerfile_path:
                if dockerfile_path not in path_mapping:
                    path_mapping[dockerfile_path] = []
                path_mapping[dockerfile_path].append(service)
                mapping_log.append(f"✅ Service '{service_name}': Mapped Dockerfile path: {dockerfile_path}")
            else:
                mapping_log.append(f"❌ Service '{service_name}': No Dockerfile path")

            # Map source code paths
            source_paths = service.get("source_code_paths", [])
            if source_paths:
                for source_path in source_paths:
                    if source_path not in path_mapping:
                        path_mapping[source_path] = []
                    path_mapping[source_path].append(service)
                    mapping_log.append(f"✅ Service '{service_name}': Mapped source path: {source_path}")
            else:
                mapping_log.append(f"❌ Service '{service_name}': No source code paths")

            # Map chart directory (fallback)
            chart_name = service.get("chart_name", "")
            if chart_name:
                chart_path = f"charts/{chart_name}/"
                if chart_path not in path_mapping:
                    path_mapping[chart_path] = []
                path_mapping[chart_path].append(service)
                mapping_log.append(f"✅ Service '{service_name}': Mapped chart path: {chart_path}")
            else:
                mapping_log.append(f"❌ Service '{service_name}': No chart name")

            # Map repository root as fallback for all services
            # This ensures that findings in root-level files get mapped to services
            if "./" not in path_mapping:
                path_mapping["./"] = []
            path_mapping["./"].append(service)

        # Log the mapping summary
        self._log_service_mapping_summary(mapping_log, path_mapping)

        return path_mapping

    def _build_service_mapping_table(self) -> Dict[str, Any]:
        """Build comprehensive service mapping table with build context analysis."""
        build_context_analyzer = BuildContextAnalyzer()

        # Convert prioritized services to container structure expected by build context analyzer
        containers = []
        for service in self.prioritization_report.get("prioritized_services", []):
            container = {
                "name": service.get("service_name", ""),
                "chart": service.get("chart_name", ""),
                "dockerfile_path": service.get("dockerfile_path", ""),
                "exposure_level": service.get("risk_level", "LOW"),
                "source_code_paths": service.get("source_code_paths", []),
            }
            containers.append(container)

        exposure_results = {"containers": containers}

        return build_context_analyzer.build_service_mapping_table(
            exposure_results, self.repo_path
        )

    def map_trivy_findings(self, trivy_results: Dict[str, Any]) -> Dict[str, Any]:
        """Map Trivy SCA findings to services."""
        mapped_findings = {
            "services": {},
            "unmapped_findings": [],
            "summary": {
                "total_findings": 0,
                "mapped_findings": 0,
                "unmapped_findings": 0,
            },
        }

        for run in trivy_results.get("runs", []):
            for result in run.get("results", []):
                mapped_findings["summary"]["total_findings"] += 1

                # Extract file path from location
                file_path = self._extract_file_path(result)
                if not file_path:
                    mapped_findings["unmapped_findings"].append(result)
                    mapped_findings["summary"]["unmapped_findings"] += 1
                    continue

                # Find services that match this file path using enhanced resolution
                matching_services = (
                    self.path_resolution_engine.resolve_finding_to_services(file_path)
                )
                if not matching_services:
                    mapped_findings["unmapped_findings"].append(result)
                    mapped_findings["summary"]["unmapped_findings"] += 1
                    continue

                # Add finding to each matching service
                for service in matching_services:
                    service_name = service["service_name"]
                    if service_name not in mapped_findings["services"]:
                        mapped_findings["services"][service_name] = {
                            "service_info": service,
                            "trivy_findings": [],
                        }

                    mapped_findings["services"][service_name]["trivy_findings"].append(
                        result
                    )
                    mapped_findings["summary"]["mapped_findings"] += 1

        return mapped_findings

    def map_semgrep_findings(self, semgrep_results: Dict[str, Any]) -> Dict[str, Any]:
        """Map Semgrep SAST findings to services."""
        mapped_findings = {
            "services": {},
            "unmapped_findings": [],
            "summary": {
                "total_findings": 0,
                "mapped_findings": 0,
                "unmapped_findings": 0,
            },
        }

        for run in semgrep_results.get("runs", []):
            for result in run.get("results", []):
                mapped_findings["summary"]["total_findings"] += 1

                # Extract file path from location
                file_path = self._extract_file_path(result)
                if not file_path:
                    mapped_findings["unmapped_findings"].append(result)
                    mapped_findings["summary"]["unmapped_findings"] += 1
                    continue

                # Find services that match this file path using enhanced resolution
                matching_services = (
                    self.path_resolution_engine.resolve_finding_to_services(file_path)
                )
                if not matching_services:
                    mapped_findings["unmapped_findings"].append(result)
                    mapped_findings["summary"]["unmapped_findings"] += 1
                    continue

                # Add finding to each matching service
                for service in matching_services:
                    service_name = service["service_name"]
                    if service_name not in mapped_findings["services"]:
                        mapped_findings["services"][service_name] = {
                            "service_info": service,
                            "semgrep_findings": [],
                        }

                    mapped_findings["services"][service_name][
                        "semgrep_findings"
                    ].append(result)
                    mapped_findings["summary"]["mapped_findings"] += 1

        return mapped_findings

    def _extract_file_path(self, result: Dict[str, Any]) -> str:
        """Extract file path from SARIF result."""
        locations = result.get("locations", [])
        if not locations:
            return ""

        physical_location = locations[0].get("physicalLocation", {})
        artifact_location = physical_location.get("artifactLocation", {})
        file_path = artifact_location.get("uri", "")

        # Remove file:// prefix if present
        if file_path.startswith("file://"):
            file_path = file_path[7:]

        # Handle Docker container paths (e.g., /repo/...)
        if file_path.startswith("/repo/"):
            file_path = file_path[5:]  # Remove /repo/ prefix

        # Remove leading slash if present
        if file_path.startswith("/"):
            file_path = file_path[1:]

        # Make path relative to repository
        if file_path.startswith(str(self.repo_path)):
            file_path = str(Path(file_path).relative_to(self.repo_path))

        return file_path

    def _find_matching_services(self, file_path: str) -> List[Dict[str, Any]]:
        """Find services that match the given file path."""
        matching_services = []

        # Try exact path match first
        if file_path in self.services_by_path:
            matching_services.extend(self.services_by_path[file_path])

        # Try parent directory matches
        path_parts = file_path.split("/")
        for i in range(len(path_parts)):
            parent_path = "/".join(path_parts[: i + 1]) + "/"
            if parent_path in self.services_by_path:
                matching_services.extend(self.services_by_path[parent_path])

        # Special case: root-level files (no directory)
        # If file is in root directory and no specific mapping found, use repository root
        if (
            "/" not in file_path
            and not matching_services
            and "./" in self.services_by_path
        ):
            matching_services.extend(self.services_by_path["./"])

        # Remove duplicates
        seen = set()
        unique_services = []
        for service in matching_services:
            service_id = service["service_name"]
            if service_id not in seen:
                seen.add(service_id)
                unique_services.append(service)

        return unique_services

    def get_mapping_summary(
        self, trivy_mapping: Dict[str, Any], semgrep_mapping: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate summary of mapping results."""
        summary = {
            "trivy": trivy_mapping["summary"],
            "semgrep": semgrep_mapping["summary"],
            "services_with_findings": set(),
        }

        # Count services with findings
        for service_name in trivy_mapping["services"]:
            summary["services_with_findings"].add(service_name)
        for service_name in semgrep_mapping["services"]:
            summary["services_with_findings"].add(service_name)

        summary["total_services_with_findings"] = len(summary["services_with_findings"])

        return summary

    def _log_service_mapping_summary(self, mapping_log: List[str], path_mapping: Dict[str, List[Dict[str, Any]]]):
        """Log service mapping summary for debugging."""
        if mapping_log:
            print(f"\n🔍 Service Path Mapping Summary:")

            # Count successful vs failed mappings
            successful_mappings = [log for log in mapping_log if "✅" in log]
            failed_mappings = [log for log in mapping_log if "❌" in log]

            print(f"   📊 Mapping Statistics:")
            print(f"     - Total services: {len(set([log.split("'")[1] for log in mapping_log if "Service '" in log]))}")
            print(f"     - Successful mappings: {len(successful_mappings)}")
            print(f"     - Failed mappings: {len(failed_mappings)}")

            # Show failed mappings
            if failed_mappings:
                print(f"\n   ❌ Failed Mappings:")
                for failed_log in failed_mappings[:10]:  # Show first 10 failures
                    print(f"     {failed_log}")
                if len(failed_mappings) > 10:
                    print(f"     ... and {len(failed_mappings) - 10} more failures")

            # Show path mapping summary
            print(f"\n   📁 Path Mapping Coverage:")
            print(f"     - Total mapped paths: {len(path_mapping)}")

            # Count paths by type
            dockerfile_paths = [p for p in path_mapping.keys() if "Dockerfile" in p]
            source_paths = [p for p in path_mapping.keys() if p.endswith("/") and "Dockerfile" not in p and p != "./"]
            chart_paths = [p for p in path_mapping.keys() if p.startswith("charts/")]

            print(f"     - Dockerfile paths: {len(dockerfile_paths)}")
            print(f"     - Source code paths: {len(source_paths)}")
            print(f"     - Chart paths: {len(chart_paths)}")
            print(f"     - Root fallback: {'Yes' if './' in path_mapping else 'No'}")
