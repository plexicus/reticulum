"""
Path Consolidation Module for Reticulum.

Handles source code path consolidation and master path building.
"""

from typing import Dict, List, Any


class PathConsolidator:
    """Consolidates source code paths and builds master path information."""

    def build_master_paths(self, containers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build master paths with the most exposed container for each path."""
        # Collect all paths from all containers
        path_containers = {}  # path -> list of containers that use this path

        for container in containers:
            for path in container.get("source_code_path", []):
                if path not in path_containers:
                    path_containers[path] = []
                path_containers[path].append(container)

        # Consolidate paths to highest level only
        consolidated_paths = self._consolidate_master_paths(
            list(path_containers.keys())
        )

        # For each consolidated path, find all containers that use it
        master_paths = {}

        for master_path in consolidated_paths:
            # Find all containers that use this path or subpaths
            related_containers = []

            for path, containers_list in path_containers.items():
                # Check if this path is the master path or a subpath
                if path == master_path or path.startswith(master_path + "/"):
                    related_containers.extend(containers_list)

            if related_containers:
                # Remove duplicates by container name
                unique_containers = {c["name"]: c for c in related_containers}.values()
                containers_list = list(unique_containers)

                # Find highest exposure level and score
                highest_score = max(c["exposure_score"] for c in containers_list)
                highest_level = self._get_highest_exposure_level(containers_list)

                # Get representative container for other details (use the highest exposed one)
                most_exposed = self._find_most_exposed_container(containers_list)

                # Create list of all container names
                container_names = [c["name"] for c in containers_list]

                master_paths[master_path] = {
                    "path": master_path,
                    "exposure_level": highest_level,
                    "exposure_score": highest_score,
                    "container_names": container_names,  # All containers that use this path
                    "primary_container": most_exposed[
                        "name"
                    ],  # Primary container for reference
                    "chart": most_exposed["chart"],
                    "gateway_type": most_exposed["gateway_type"],
                    "host": most_exposed["host"],
                    "access_chain": most_exposed["access_chain"],
                    "dockerfile_path": most_exposed["dockerfile_path"],
                }

        return master_paths

    def _consolidate_master_paths(self, paths: List[str]) -> List[str]:
        """Consolidate paths to show only the highest level paths."""
        if not paths:
            return []

        # Sort paths to ensure parent paths come before children
        sorted_paths = sorted(set(paths))
        consolidated = []

        for path in sorted_paths:
            # Normalize path for comparison (remove trailing slash)
            norm_path = path.rstrip("/")

            # Check if this path is already covered by a parent path
            is_subpath = False
            for existing_path in consolidated:
                norm_existing = existing_path.rstrip("/")
                if (
                    norm_path.startswith(norm_existing + "/")
                    or norm_path == norm_existing
                ):
                    is_subpath = True
                    break

            if not is_subpath:
                # Remove any existing paths that are children of this path
                consolidated = [
                    p
                    for p in consolidated
                    if not p.rstrip("/").startswith(norm_path + "/")
                ]
                consolidated.append(path)

        return sorted(consolidated)

    def _get_highest_exposure_level(self, containers: List[Dict[str, Any]]) -> str:
        """Get the highest exposure level from a list of containers."""
        if not containers:
            return "LOW"

        # Priority: HIGH > MEDIUM > LOW
        levels = [c.get("exposure_level", "LOW") for c in containers]

        if "HIGH" in levels:
            return "HIGH"
        elif "MEDIUM" in levels:
            return "MEDIUM"
        else:
            return "LOW"

    def _find_most_exposed_container(
        self, containers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Find the container with the highest exposure level."""
        if not containers:
            return {}

        # Sort by exposure score (descending) and then by name for consistency
        sorted_containers = sorted(
            containers, key=lambda c: (-c.get("exposure_score", 0), c.get("name", ""))
        )

        return sorted_containers[0]
