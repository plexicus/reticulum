"""
Smart Dockerfile Analyzer for Reticulum.

Enhanced analyzer that uses semantic matching to connect Dockerfiles to Docker images
from Helm charts, rather than just path-based discovery.

Now integrated with Unified Pareto Strategy for service identification and territory claiming.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import re
import yaml

from .service_registry import ServiceRegistry
from .dockerfile_parser import DockerfileParser
from .reverse_ownership_index import ReverseOwnershipIndex


class SmartDockerfileAnalyzer:
    """Smart analyzer that connects Dockerfiles to Docker images from Helm charts."""

    def __init__(self):
        self.dockerfile_cache = {}
        self.image_cache = {}

        # Unified Pareto Strategy components
        self.service_registry = ServiceRegistry()
        self.dockerfile_parser = DockerfileParser()
        self.reverse_ownership_index = ReverseOwnershipIndex()

    def discover_all_dockerfiles(self, repo_path: Path) -> List[Path]:
        """
        Discover all Dockerfiles in repository using pattern matching.

        Args:
            repo_path: Root path of the repository

        Returns:
            List of all Dockerfile paths found
        """
        dockerfiles = []

        # Find all files matching Dockerfile patterns
        patterns = [
            "**/*Dockerfile*",
            "**/Dockerfile",
            "**/dockerfile*",
        ]

        for pattern in patterns:
            for dockerfile_path in repo_path.glob(pattern):
                if dockerfile_path.is_file():
                    # Skip files in common ignore directories
                    if self._should_ignore_path(dockerfile_path):
                        continue
                    dockerfiles.append(dockerfile_path)

        # Remove duplicates and sort
        unique_dockerfiles = list(set(dockerfiles))
        return sorted(unique_dockerfiles)

    def extract_images_from_helm_chart(self, chart_dir: Path) -> Dict[str, Any]:
        """
        Extract Docker image information from Helm chart.

        Args:
            chart_dir: Path to Helm chart directory

        Returns:
            Dictionary with image information
        """
        images = {}

        # Read values.yaml
        values_file = chart_dir / "values.yaml"
        if values_file.exists():
            try:
                with open(values_file, 'r') as f:
                    values = yaml.safe_load(f)

                # Extract image information from common patterns
                image_info = self._extract_image_from_values(values)
                if image_info:
                    images["primary"] = image_info

                # Look for multiple images (common in complex charts)
                additional_images = self._find_additional_images(values)
                images.update(additional_images)

            except Exception as e:
                print(f"⚠️  Failed to parse values.yaml in {chart_dir}: {e}")

        return images

    def map_dockerfiles_to_images(
        self, repo_path: Path, chart_images: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Map Dockerfiles to Docker images using semantic matching.

        Args:
            repo_path: Root path of the repository
            chart_images: Dictionary mapping chart names to image information

        Returns:
            Mapping of Dockerfiles to charts and images
        """
        mapping = {
            "dockerfiles": {},
            "charts": {},
            "unmapped_dockerfiles": [],
            "unmapped_charts": [],
        }

        # Discover all Dockerfiles
        dockerfiles = self.discover_all_dockerfiles(repo_path)

        # Create mapping for each Dockerfile
        for dockerfile_path in dockerfiles:
            dockerfile_name = dockerfile_path.stem.lower()
            relative_path = str(dockerfile_path.relative_to(repo_path))

            # Try to find matching chart
            matched_chart = self._find_matching_chart(dockerfile_name, chart_images)

            if matched_chart:
                mapping["dockerfiles"][relative_path] = {
                    "path": relative_path,
                    "chart": matched_chart,
                    "image": chart_images[matched_chart].get("primary", {}),
                    "confidence": "high",
                    "match_type": "semantic",
                }
            else:
                mapping["unmapped_dockerfiles"].append(relative_path)

        # Track charts without Dockerfiles
        for chart_name in chart_images:
            has_dockerfile = any(
                mapping["dockerfiles"][df].get("chart") == chart_name
                for df in mapping["dockerfiles"]
            )
            if not has_dockerfile:
                mapping["unmapped_charts"].append(chart_name)

        return mapping

    def _should_ignore_path(self, path: Path) -> bool:
        """Check if path should be ignored."""
        ignore_patterns = [
            ".git",
            "node_modules",
            "vendor",
            "__pycache__",
            ".pytest_cache",
            "target",
            "build",
            "dist",
        ]

        path_str = str(path)
        return any(pattern in path_str for pattern in ignore_patterns)

    def _extract_image_from_values(self, values: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract image information from values.yaml."""
        # Common image patterns in Helm charts
        image_patterns = [
            ["image"],
            ["image", "repository"],
            ["app", "image"],
            ["service", "image"],
            ["container", "image"],
        ]

        for pattern in image_patterns:
            current = values
            for key in pattern:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    break
            else:
                # Found a match
                if isinstance(current, str):
                    return {"repository": current, "tag": "latest"}
                elif isinstance(current, dict):
                    return {
                        "repository": current.get("repository", ""),
                        "tag": current.get("tag", "latest"),
                        "pullPolicy": current.get("pullPolicy", ""),
                    }

        return None

    def _find_additional_images(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """Find additional images in complex charts."""
        additional_images = {}

        def search_for_images(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key

                    # Check if this looks like an image definition
                    if key == "image" and isinstance(value, (str, dict)):
                        image_name = path.split(".")[-1] if path else "secondary"
                        if isinstance(value, str):
                            additional_images[image_name] = {"repository": value, "tag": "latest"}
                        elif isinstance(value, dict):
                            additional_images[image_name] = value

                    # Recursively search
                    search_for_images(value, current_path)

        search_for_images(values)
        return additional_images

    def _find_matching_chart(self, dockerfile_name: str, chart_images: Dict[str, Any]) -> Optional[str]:
        """Find chart that matches Dockerfile name using semantic matching."""
        # Clean up dockerfile name
        clean_dockerfile = (
            dockerfile_name
            .replace("dockerfile", "")
            .replace("-", "")
            .replace("_", "")
            .strip(".")
        )

        # Try exact match first
        for chart_name in chart_images:
            clean_chart = (
                chart_name
                .replace("-", "")
                .replace("_", "")
                .replace("chart", "")
                .replace("service", "")
                .replace("app", "")
            )

            # Exact match
            if clean_dockerfile == clean_chart:
                return chart_name

            # Contains match
            if clean_dockerfile in clean_chart or clean_chart in clean_dockerfile:
                return chart_name

            # Check if dockerfile name matches image repository
            primary_image = chart_images[chart_name].get("primary", {})
            image_repo = primary_image.get("repository", "").lower()
            if clean_dockerfile in image_repo or image_repo in clean_dockerfile:
                return chart_name

        return None

    def analyze_repository(self, repo_path: Path) -> Dict[str, Any]:
        """
        Perform comprehensive Dockerfile-to-image analysis for entire repository.

        Args:
            repo_path: Root path of the repository

        Returns:
            Comprehensive analysis results
        """
        # Find all Helm charts
        charts = list(repo_path.glob("**/Chart.yaml"))
        chart_images = {}

        for chart_file in charts:
            chart_dir = chart_file.parent
            chart_name = chart_dir.name

            # Extract images from this chart
            images = self.extract_images_from_helm_chart(chart_dir)
            if images:
                chart_images[chart_name] = images

        # Map Dockerfiles to images
        mapping = self.map_dockerfiles_to_images(repo_path, chart_images)

        # Generate summary
        summary = {
            "total_dockerfiles": len(mapping["dockerfiles"]),
            "total_charts": len(chart_images),
            "mapped_dockerfiles": len(mapping["dockerfiles"]),
            "unmapped_dockerfiles": len(mapping["unmapped_dockerfiles"]),
            "unmapped_charts": len(mapping["unmapped_charts"]),
            "mapping_confidence": self._calculate_mapping_confidence(mapping),
        }

        return {
            "summary": summary,
            "mapping": mapping,
            "chart_images": chart_images,
        }

    def _calculate_mapping_confidence(self, mapping: Dict[str, Any]) -> str:
        """Calculate overall confidence in mapping."""
        total_dockerfiles = len(mapping["dockerfiles"]) + len(mapping["unmapped_dockerfiles"])
        if total_dockerfiles == 0:
            return "unknown"

        mapped_ratio = len(mapping["dockerfiles"]) / total_dockerfiles

        if mapped_ratio >= 0.8:
            return "high"
        elif mapped_ratio >= 0.5:
            return "medium"
        else:
            return "low"

    def analyze_with_unified_strategy(self, repo_path: Path) -> Dict[str, Any]:
        """
        Analyze repository using Unified Pareto Strategy.

        Args:
            repo_path: Root path of the repository

        Returns:
            Comprehensive analysis with service identification and territory claiming
        """
        # Phase 1: Service Identification
        dockerfiles = self.discover_all_dockerfiles(repo_path)

        # Register services from Dockerfiles
        for dockerfile_path in dockerfiles:
            service_token = self.service_registry.register_service_from_dockerfile(
                dockerfile_path, repo_path
            )

        # Phase 2: Territory Claiming
        for dockerfile_path in dockerfiles:
            service_token = self.service_registry.get_service_by_dockerfile(dockerfile_path)
            if service_token:
                service_info = self.service_registry.get_service_by_token(service_token)

                # Claim implicit territory (Dockerfile parent directory)
                self.reverse_ownership_index.claim_implicit_territory(
                    service_token, service_info.parent_directory
                )

                # Claim explicit territory from COPY/ADD commands
                source_paths = self.dockerfile_parser.parse_dockerfile(
                    dockerfile_path, dockerfile_path.parent, repo_path
                )
                self.reverse_ownership_index.claim_explicit_territory(
                    service_token, source_paths
                )

        # Generate comprehensive results
        results = {
            "service_identification": {
                "total_services": len(self.service_registry.get_all_services()),
                "services": [
                    {
                        "token": service.token,
                        "dockerfile": str(service.dockerfile_path),
                        "parent_directory": str(service.parent_directory)
                    }
                    for service in self.service_registry.get_all_services()
                ]
            },
            "territory_claiming": {
                "ownership_statistics": self.reverse_ownership_index.get_index_statistics(),
                "shared_folders": self.reverse_ownership_index.get_shared_folders(),
                "service_coverage": {
                    service.token: self.reverse_ownership_index.get_service_coverage(service.token)
                    for service in self.service_registry.get_all_services()
                }
            },
            "dockerfile_analysis": {
                "total_dockerfiles": len(dockerfiles),
                "dockerfiles": [
                    self.dockerfile_parser.analyze_dockerfile_structure(df, repo_path)
                    for df in dockerfiles
                ]
            }
        }

        return results