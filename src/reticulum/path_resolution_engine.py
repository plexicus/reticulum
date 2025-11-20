"""
Path Resolution Engine for Reticulum.

Handles multi-level path resolution for mapping security findings to services
with build context awareness.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional

from .reverse_ownership_index import ReverseOwnershipIndex
from .service_registry import ServiceRegistry


class PathResolutionEngine:
    """Multi-level path resolution engine for service-to-finding mapping."""

    def __init__(self, service_mapping_table: Dict[str, Any], repo_root: Path):
        self.service_mapping_table = service_mapping_table
        self.repo_root = repo_root

        # Unified Strategy components
        self.reverse_ownership_index = ReverseOwnershipIndex()
        self.service_registry = ServiceRegistry()

    def resolve_finding_to_services(
        self, finding_file_path: str
    ) -> List[Dict[str, Any]]:
        """
        Resolve a security finding file path to matching services.

        Args:
            finding_file_path: File path from security finding (relative to repo root)

        Returns:
            List of matching services with resolution details
        """
        matching_services = []
        resolution_details = []

        for service_name, service_info in self.service_mapping_table["services"].items():
            resolution = self._resolve_finding_for_service(
                finding_file_path, service_info
            )
            if resolution["matches"]:
                matching_services.append(service_info)
                resolution_details.append(resolution)

        # Sort by resolution confidence
        if matching_services and resolution_details:
            # Combine services with their resolution details
            combined = list(zip(matching_services, resolution_details))
            combined.sort(key=lambda x: self._get_resolution_confidence_score(x[1]))
            matching_services = [service for service, _ in combined]

        return matching_services

    def _resolve_finding_for_service(
        self, finding_file_path: str, service_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve finding path for a specific service.

        Returns:
            Resolution details including match type and confidence
        """
        resolution = {
            "matches": False,
            "match_type": "none",
            "confidence": "low",
            "details": {},
            "resolved_path": "",
        }

        # Level 1: Direct path matching (highest confidence)
        direct_match = self._check_direct_path_match(finding_file_path, service_info)
        if direct_match["matches"]:
            resolution.update(direct_match)
            return resolution

        # Level 2: Build context relative matching
        build_context_match = self._check_build_context_match(
            finding_file_path, service_info
        )
        if build_context_match["matches"]:
            resolution.update(build_context_match)
            return resolution

        # Level 3: Parent directory matching
        parent_match = self._check_parent_directory_match(finding_file_path, service_info)
        if parent_match["matches"]:
            resolution.update(parent_match)
            return resolution

        # Level 4: Chart directory matching (fallback)
        chart_match = self._check_chart_directory_match(finding_file_path, service_info)
        if chart_match["matches"]:
            resolution.update(chart_match)
            return resolution

        return resolution

    def _check_direct_path_match(
        self, finding_file_path: str, service_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check for direct path matches in source paths."""
        source_paths = service_info.get("source_paths", [])
        dockerfile_path = service_info.get("dockerfile_path", "")

        # Check exact match with source paths
        for source_path in source_paths:
            clean_source = source_path.rstrip("/")
            if finding_file_path == clean_source or finding_file_path.startswith(
                clean_source + "/"
            ):
                return {
                    "matches": True,
                    "match_type": "direct_source_path",
                    "confidence": "high",
                    "details": {"source_path": source_path},
                    "resolved_path": finding_file_path,
                }

        # Check Dockerfile path match
        if dockerfile_path and finding_file_path == dockerfile_path:
            return {
                "matches": True,
                "match_type": "dockerfile_path",
                "confidence": "high",
                "details": {"dockerfile_path": dockerfile_path},
                "resolved_path": finding_file_path,
            }

        return {"matches": False}

    def _check_build_context_match(
        self, finding_file_path: str, service_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check for matches relative to build context."""
        build_context = service_info.get("build_context", "")
        if not build_context:
            return {"matches": False}

        # Check if finding is within build context
        build_context_path = Path(build_context)
        finding_path = Path(finding_file_path)

        try:
            # Check if finding path is relative to build context
            if finding_path.is_relative_to(build_context_path):
                relative_path = str(finding_path.relative_to(build_context_path))

                # Check if this relative path matches any source paths
                source_paths = service_info.get("source_paths", [])
                for source_path in source_paths:
                    clean_source = source_path.rstrip("/")
                    if relative_path == clean_source or relative_path.startswith(
                        clean_source + "/"
                    ):
                        return {
                            "matches": True,
                            "match_type": "build_context_relative",
                            "confidence": "high",
                            "details": {
                                "build_context": build_context,
                                "relative_path": relative_path,
                                "source_path": source_path,
                            },
                            "resolved_path": relative_path,
                        }

                # Even without specific source path match, if it's in build context
                # and build context has high confidence, consider it a match
                build_context_analysis = service_info.get("build_context_analysis", {})
                if build_context_analysis.get("confidence") in ["high", "medium"]:
                    return {
                        "matches": True,
                        "match_type": "build_context_general",
                        "confidence": "medium",
                        "details": {
                            "build_context": build_context,
                            "relative_path": relative_path,
                        },
                        "resolved_path": relative_path,
                    }

        except ValueError:
            # Path is not relative to build context
            pass

        return {"matches": False}

    def _check_parent_directory_match(
        self, finding_file_path: str, service_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check for parent directory matches."""
        source_paths = service_info.get("source_paths", [])
        dockerfile_path = service_info.get("dockerfile_path", "")

        finding_path = Path(finding_file_path)

        # Check parent directories of finding
        for parent_level in range(len(finding_path.parts)):
            parent_path = "/".join(finding_path.parts[: parent_level + 1]) + "/"

            # Check against source paths
            for source_path in source_paths:
                if parent_path == source_path:
                    return {
                        "matches": True,
                        "match_type": "parent_directory",
                        "confidence": "medium",
                        "details": {
                            "parent_path": parent_path,
                            "source_path": source_path,
                        },
                        "resolved_path": parent_path,
                    }

            # Check against Dockerfile parent
            if dockerfile_path:
                dockerfile_parent = str(Path(dockerfile_path).parent) + "/"
                if parent_path == dockerfile_parent:
                    return {
                        "matches": True,
                        "match_type": "dockerfile_parent",
                        "confidence": "medium",
                        "details": {
                            "parent_path": parent_path,
                            "dockerfile_parent": dockerfile_parent,
                        },
                        "resolved_path": parent_path,
                    }

        return {"matches": False}

    def _check_chart_directory_match(
        self, finding_file_path: str, service_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check for chart directory matches (fallback)."""
        chart_name = service_info.get("chart_name", "")
        if not chart_name:
            return {"matches": False}

        chart_path = f"charts/{chart_name}/"
        finding_path = Path(finding_file_path)

        # Check if finding is in chart directory
        if str(finding_path).startswith(chart_path):
            return {
                "matches": True,
                "match_type": "chart_directory",
                "confidence": "low",
                "details": {"chart_path": chart_path},
                "resolved_path": str(finding_path),
            }

        # Check parent directories for chart match
        for parent_level in range(len(finding_path.parts)):
            parent_path = "/".join(finding_path.parts[: parent_level + 1]) + "/"
            if parent_path == chart_path:
                return {
                    "matches": True,
                    "match_type": "chart_parent",
                    "confidence": "low",
                    "details": {"chart_path": chart_path},
                    "resolved_path": parent_path,
                }

        return {"matches": False}

    def _get_resolution_confidence_score(self, resolution: Dict[str, Any]) -> int:
        """Get confidence score for resolution (lower is better)."""
        confidence_map = {
            "high": 1,
            "medium": 2,
            "low": 3,
        }

        match_type_map = {
            "direct_source_path": 1,
            "dockerfile_path": 1,
            "build_context_relative": 2,
            "build_context_general": 3,
            "parent_directory": 4,
            "dockerfile_parent": 4,
            "chart_directory": 5,
            "chart_parent": 5,
        }

        confidence_score = confidence_map.get(resolution.get("confidence", "low"), 3)
        match_score = match_type_map.get(resolution.get("match_type", "none"), 6)

        return confidence_score + match_score

    def generate_resolution_summary(
        self, findings_resolutions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate summary of path resolution results."""
        summary = {
            "total_findings": len(findings_resolutions),
            "resolved_findings": 0,
            "unresolved_findings": 0,
            "resolution_breakdown": {
                "direct_source_path": 0,
                "dockerfile_path": 0,
                "build_context_relative": 0,
                "build_context_general": 0,
                "parent_directory": 0,
                "dockerfile_parent": 0,
                "chart_directory": 0,
                "chart_parent": 0,
            },
            "confidence_breakdown": {
                "high": 0,
                "medium": 0,
                "low": 0,
            },
        }

        for resolution in findings_resolutions:
            if resolution["matches"]:
                summary["resolved_findings"] += 1
                match_type = resolution.get("match_type", "unknown")
                confidence = resolution.get("confidence", "low")

                if match_type in summary["resolution_breakdown"]:
                    summary["resolution_breakdown"][match_type] += 1
                if confidence in summary["confidence_breakdown"]:
                    summary["confidence_breakdown"][confidence] += 1
            else:
                summary["unresolved_findings"] += 1

        return summary

    # Unified Strategy Integration Methods

    def resolve_with_reverse_ownership(
        self, finding_file_path: str
    ) -> List[Dict[str, Any]]:
        """
        Resolve finding using reverse ownership index.

        Args:
            finding_file_path: File path from security finding

        Returns:
            List of matching services with ownership details
        """
        matching_services = []

        # Convert finding path to Path object
        finding_path = Path(finding_file_path)

        # Get service owners using reverse ownership index
        service_tokens = self.reverse_ownership_index.get_owners_for_path(finding_path)

        # Convert service tokens to service info
        for service_token in service_tokens:
            service_info = self._get_service_info_by_token(service_token)
            if service_info:
                matching_services.append(service_info)

        # Add ownership resolution details
        for service_info in matching_services:
            service_info["resolution_details"] = {
                "match_type": "reverse_ownership",
                "confidence": "high",
                "service_token": service_info.get("service_name", ""),
                "ownership_path": finding_file_path,
                "resolution_method": "reverse_ownership_index"
            }

        return matching_services

    def _get_service_info_by_token(self, service_token: str) -> Optional[Dict[str, Any]]:
        """Get service info by service token."""
        for service_name, service_info in self.service_mapping_table["services"].items():
            if service_name == service_token:
                return service_info
        return None

    def resolve_with_hybrid_approach(
        self, finding_file_path: str
    ) -> List[Dict[str, Any]]:
        """
        Resolve finding using hybrid approach (reverse ownership + traditional).

        Args:
            finding_file_path: File path from security finding

        Returns:
            List of matching services with hybrid resolution details
        """
        # Get results from both approaches
        ownership_results = self.resolve_with_reverse_ownership(finding_file_path)
        traditional_results = self.resolve_finding_to_services(finding_file_path)

        # Combine and deduplicate results
        all_results = ownership_results + traditional_results

        # Deduplicate by service name
        seen_services = set()
        unique_results = []

        for service_info in all_results:
            service_name = service_info.get("service_name", "")
            if service_name and service_name not in seen_services:
                seen_services.add(service_name)
                unique_results.append(service_info)

        # Sort by confidence (reverse ownership results first)
        unique_results.sort(
            key=lambda x: (
                0 if x.get("resolution_details", {}).get("resolution_method") == "reverse_ownership_index" else 1,
                x.get("resolution_details", {}).get("confidence", "low")
            )
        )

        return unique_results

    def initialize_unified_strategy(
        self, orchestrator
    ) -> None:
        """
        Initialize with Unified Strategy components.

        Args:
            orchestrator: UnifiedStrategyOrchestrator instance
        """
        self.reverse_ownership_index = orchestrator.reverse_ownership_index
        self.service_registry = orchestrator.service_registry

    def get_ownership_coverage_statistics(self) -> Dict[str, Any]:
        """Get statistics about ownership coverage."""
        ownership_stats = self.reverse_ownership_index.get_index_statistics()

        return {
            "ownership_index": ownership_stats,
            "service_registry": {
                "total_services": len(self.service_registry.get_all_services()),
                "service_tokens": [s.token for s in self.service_registry.get_all_services()]
            },
            "path_resolution_coverage": self._calculate_path_resolution_coverage()
        }

    def _calculate_path_resolution_coverage(self) -> Dict[str, Any]:
        """Calculate path resolution coverage statistics."""
        total_folders = len(self.reverse_ownership_index.ownership_index)
        total_services = len(self.service_registry.get_all_services())

        # Calculate coverage metrics
        coverage_metrics = {
            "total_folders_owned": total_folders,
            "total_services_registered": total_services,
            "avg_folders_per_service": total_folders / total_services if total_services > 0 else 0,
            "shared_folders": len(self.reverse_ownership_index.get_shared_folders()),
            "exclusive_folders": total_folders - len(self.reverse_ownership_index.get_shared_folders())
        }

        return coverage_metrics

    def analyze_resolution_confidence(
        self, finding_file_path: str
    ) -> Dict[str, Any]:
        """
        Analyze resolution confidence for a finding.

        Args:
            finding_file_path: File path from security finding

        Returns:
            Confidence analysis results
        """
        # Get results from both methods
        ownership_results = self.resolve_with_reverse_ownership(finding_file_path)
        traditional_results = self.resolve_finding_to_services(finding_file_path)

        # Analyze confidence factors
        confidence_factors = {
            "reverse_ownership_count": len(ownership_results),
            "traditional_resolution_count": len(traditional_results),
            "overlap_count": len(set(s.get("service_name", "") for s in ownership_results)
                               & set(s.get("service_name", "") for s in traditional_results)),
            "ownership_confidence": "high" if ownership_results else "low",
            "traditional_confidence": self._assess_traditional_confidence(traditional_results)
        }

        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(confidence_factors)

        return {
            "confidence_factors": confidence_factors,
            "overall_confidence": overall_confidence,
            "recommended_approach": "hybrid" if ownership_results else "traditional",
            "resolution_summary": {
                "total_services_found": len(ownership_results) + len(traditional_results),
                "unique_services": len(set(s.get("service_name", "") for s in ownership_results + traditional_results))
            }
        }

    def _assess_traditional_confidence(self, traditional_results: List[Dict[str, Any]]) -> str:
        """Assess confidence level for traditional resolution results."""
        if not traditional_results:
            return "low"

        # Count high confidence matches
        high_confidence_count = sum(
            1 for result in traditional_results
            if result.get("resolution_details", {}).get("confidence") == "high"
        )

        if high_confidence_count > 0:
            return "high"
        elif len(traditional_results) > 0:
            return "medium"
        else:
            return "low"

    def _calculate_overall_confidence(self, confidence_factors: Dict[str, Any]) -> str:
        """Calculate overall confidence based on multiple factors."""
        score = 0

        # Reverse ownership presence
        if confidence_factors["reverse_ownership_count"] > 0:
            score += 2

        # Traditional resolution presence
        if confidence_factors["traditional_resolution_count"] > 0:
            score += 1

        # Overlap between methods
        if confidence_factors["overlap_count"] > 0:
            score += 2

        # Confidence levels
        if confidence_factors["ownership_confidence"] == "high":
            score += 2
        if confidence_factors["traditional_confidence"] == "high":
            score += 1

        # Determine overall confidence
        if score >= 5:
            return "high"
        elif score >= 3:
            return "medium"
        else:
            return "low"