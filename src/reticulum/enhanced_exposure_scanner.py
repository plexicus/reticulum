"""
Enhanced Exposure Scanner with Smart Dockerfile Analysis

Extends the main ExposureScanner with intelligent Dockerfile-to-image mapping
using semantic analysis rather than just path-based discovery.
"""

from pathlib import Path
from typing import Dict, Any

from .main import ExposureScanner
from .smart_dockerfile_analyzer import SmartDockerfileAnalyzer


class EnhancedExposureScanner(ExposureScanner):
    """Enhanced scanner with smart Dockerfile-to-image mapping."""

    def __init__(self):
        super().__init__()
        self.smart_dockerfile_analyzer = SmartDockerfileAnalyzer()
        self.smart_mapping_results = {}

    def scan_repo(self, repo_path: str) -> Dict[str, Any]:
        """
        Enhanced scan with smart Dockerfile analysis.

        Args:
            repo_path: Path to repository to scan

        Returns:
            Enhanced scan results with smart mapping
        """
        # First run the standard scan
        results = super().scan_repo(repo_path)

        # Then run smart Dockerfile analysis
        repo_path_obj = Path(repo_path).resolve()
        smart_analysis = self.smart_dockerfile_analyzer.analyze_repository(
            repo_path_obj
        )

        # Enhance results with smart mapping
        results["smart_dockerfile_analysis"] = smart_analysis
        results["enhanced_containers"] = self._enhance_containers_with_smart_mapping(
            results["containers"], smart_analysis
        )

        # Update prioritization report with smart mapping
        if "prioritization_report" in results:
            results["prioritization_report"]["smart_mapping"] = smart_analysis

        return results

    def _enhance_containers_with_smart_mapping(
        self, containers: list, smart_analysis: Dict[str, Any]
    ) -> list:
        """Enhance containers with smart Dockerfile mapping information."""
        enhanced_containers = []

        for container in containers:
            chart_name = container.get("chart", "")
            container_name = container.get("name", "")

            # Find smart mapping for this container
            smart_info = self._find_smart_mapping_for_container(
                chart_name, container_name, smart_analysis
            )

            # Create enhanced container
            enhanced_container = container.copy()
            enhanced_container["smart_mapping"] = smart_info

            # If we found a smart mapping, update Dockerfile path
            if smart_info.get("dockerfile_path") and not container.get(
                "dockerfile_path"
            ):
                enhanced_container["dockerfile_path"] = smart_info["dockerfile_path"]

            enhanced_containers.append(enhanced_container)

        return enhanced_containers

    def _find_smart_mapping_for_container(
        self, chart_name: str, container_name: str, smart_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Find smart mapping information for a container."""
        mapping = smart_analysis.get("mapping", {})
        dockerfiles = mapping.get("dockerfiles", {})

        # Look for Dockerfile mapped to this chart
        for dockerfile_path, dockerfile_info in dockerfiles.items():
            if dockerfile_info.get("chart") == chart_name:
                return {
                    "dockerfile_path": dockerfile_path,
                    "mapped_chart": chart_name,
                    "image_info": dockerfile_info.get("image", {}),
                    "confidence": dockerfile_info.get("confidence", "low"),
                    "match_type": dockerfile_info.get("match_type", "semantic"),
                    "is_custom_image": self._is_custom_image(
                        dockerfile_info.get("image", {})
                    ),
                }

        # Check if this chart uses standard images (no custom Dockerfile)
        chart_images = smart_analysis.get("chart_images", {})
        if chart_name in chart_images:
            primary_image = chart_images[chart_name].get("primary", {})
            return {
                "dockerfile_path": "",
                "mapped_chart": chart_name,
                "image_info": primary_image,
                "confidence": "low",
                "match_type": "standard_image",
                "is_custom_image": False,
                "standard_image_source": primary_image.get("repository", ""),
            }

        return {
            "dockerfile_path": "",
            "mapped_chart": chart_name,
            "image_info": {},
            "confidence": "unknown",
            "match_type": "unknown",
            "is_custom_image": False,
        }

    def _is_custom_image(self, image_info: Dict[str, Any]) -> bool:
        """Determine if an image is custom-built or from public registry."""
        repository = image_info.get("repository", "").lower()

        # Common public registry patterns
        public_registries = [
            "nginx",
            "python",
            "postgres",
            "redis",
            "kong",
            "haproxy",
            "traefik",
            "grafana",
            "prometheus",
            "mysql",
            "mongo",
            "elasticsearch",
            "kibana",
            "logstash",
            "jenkins",
            "gitlab",
            "docker.io/",
            "gcr.io/",
            "registry.k8s.io/",
            "quay.io/",
        ]

        # If repository contains a registry domain or is a common public image
        # and doesn't look like a custom registry, consider it public
        for registry in public_registries:
            if registry in repository:
                return False

        # Check for custom registry patterns
        custom_patterns = [
            "localhost",
            "127.0.0.1",
            "192.168.",
            "10.",
            "172.",
            "mycompany",
            "internal",
            "private",
            "custom",
        ]

        for pattern in custom_patterns:
            if pattern in repository:
                return True

        # If it's a short name (no slashes), it's likely from Docker Hub
        if "/" not in repository:
            return False

        # Default to custom if we're not sure
        return True

    def get_smart_mapping_summary(self) -> Dict[str, Any]:
        """Get summary of smart Dockerfile mapping."""
        if not self.smart_mapping_results:
            return {"error": "No smart mapping results available"}

        smart_analysis = self.smart_mapping_results
        mapping = smart_analysis.get("mapping", {})

        summary = {
            "total_charts": smart_analysis.get("summary", {}).get("total_charts", 0),
            "total_dockerfiles": smart_analysis.get("summary", {}).get(
                "total_dockerfiles", 0
            ),
            "mapped_dockerfiles": len(mapping.get("dockerfiles", {})),
            "unmapped_dockerfiles": len(mapping.get("unmapped_dockerfiles", [])),
            "unmapped_charts": len(mapping.get("unmapped_charts", [])),
            "mapping_confidence": smart_analysis.get("summary", {}).get(
                "mapping_confidence", "unknown"
            ),
            "custom_images_count": self._count_custom_images(smart_analysis),
            "standard_images_count": self._count_standard_images(smart_analysis),
        }

        return summary

    def _count_custom_images(self, smart_analysis: Dict[str, Any]) -> int:
        """Count custom images in the analysis."""
        count = 0
        mapping = smart_analysis.get("mapping", {})

        for dockerfile_info in mapping.get("dockerfiles", {}).values():
            image_info = dockerfile_info.get("image", {})
            if self._is_custom_image(image_info):
                count += 1

        return count

    def _count_standard_images(self, smart_analysis: Dict[str, Any]) -> int:
        """Count standard images in the analysis."""
        count = 0
        chart_images = smart_analysis.get("chart_images", {})

        for chart_name, images in chart_images.items():
            primary_image = images.get("primary", {})
            if not self._is_custom_image(primary_image):
                count += 1

        return count
