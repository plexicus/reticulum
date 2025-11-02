"""
Dockerfile Analysis Module for Reticulum.

Handles Dockerfile parsing and source code path extraction.
"""

from pathlib import Path
from typing import List, Optional
import re


class DockerfileAnalyzer:
    """Analyzes Dockerfiles to extract source code paths and container information."""

    def find_dockerfile(
        self, chart_dir: Path, repo_path: Path, chart_name: str
    ) -> Optional[Path]:
        """Find Dockerfile for a chart in the repository."""
        # Strategy 1: Look for Dockerfile in chart directory
        dockerfile = chart_dir / "Dockerfile"
        if dockerfile.exists():
            return dockerfile

        # Strategy 2: Look in subdirectories of chart
        for subdir in chart_dir.iterdir():
            if subdir.is_dir():
                dockerfile = subdir / "Dockerfile"
                if dockerfile.exists():
                    return dockerfile

        # Strategy 3: Look for Dockerfile in repo root with same name as chart
        dockerfile = repo_path / chart_name / "Dockerfile"
        if dockerfile.exists():
            return dockerfile

        # Strategy 4: Look in repo root (for single-app repos)
        dockerfile = repo_path / "Dockerfile"
        if dockerfile.exists():
            return dockerfile

        # Strategy 5: Look in common locations
        common_paths = [
            repo_path / "src" / chart_name / "Dockerfile",
            repo_path / "apps" / chart_name / "Dockerfile",
            repo_path / "services" / chart_name / "Dockerfile",
        ]

        for path in common_paths:
            if path.exists():
                return path

        # Strategy 6: Look for Dockerfile variants (Dockerfile.*)
        for variant in ["Dockerfile.dev", "Dockerfile.prod", "Dockerfile.staging"]:
            dockerfile = chart_dir / variant
            if dockerfile.exists():
                return dockerfile

        # Strategy 7: Deep search in repository for any Dockerfile matching chart name patterns
        dockerfile = self._deep_search_dockerfile(repo_path, chart_name)
        if dockerfile:
            return dockerfile

        return None

    def parse_dockerfile_for_source_paths(
        self, dockerfile_path: Path, repo_root: Path
    ) -> List[str]:
        """Parse Dockerfile to extract source code paths."""
        raw_paths = []

        try:
            # Validate that the Dockerfile exists and is readable
            if not dockerfile_path.exists():
                return []

            if not dockerfile_path.is_file():
                return []

            with open(dockerfile_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Process line by line to avoid commented lines
            for line in lines:
                line = line.strip()

                # Skip commented lines and empty lines
                if line.startswith("#") or not line:
                    continue

                # Look for COPY and ADD instructions
                copy_match = re.match(
                    r"(?:COPY|ADD)\s+([^\s]+)\s+([^\s]+)", line, re.IGNORECASE
                )
                if copy_match:
                    source, dest = copy_match.groups()

                    # Clean up the source path
                    clean_source = source.strip("\"'")
                    clean_dest = dest.strip("\"'")

                    # Skip --from flags and other Docker-specific syntax
                    if clean_source.startswith("--"):
                        continue

                    # Handle special cases
                    if clean_source == "." and clean_dest.startswith("/app"):
                        # Current directory copied to app - means entire app
                        raw_paths.append(".")
                    elif (
                        clean_source
                        and clean_source != "."
                        and not clean_source.startswith(  # Don't capture '.' when it's not a full dir copy
                            ("--", "http://", "https://", "$")
                        )
                        and not clean_source.endswith(".tar")
                    ):
                        # Include any path that looks like source code
                        raw_paths.append(clean_source)

            # Consolidate paths to show only parent directories
            source_paths = self._consolidate_source_paths(raw_paths, repo_root)

            # Validate extracted paths against actual repository structure
            validated_paths = self._validate_source_paths(source_paths, repo_root)

            return validated_paths

        except (IOError, UnicodeDecodeError, PermissionError):
            # Log the error but continue processing
            return []
        except Exception:
            # Catch any other unexpected errors
            return []

    def _consolidate_source_paths(
        self, raw_paths: List[str], repo_root: Path
    ) -> List[str]:
        """Consolidate source paths to show only parent directories, relative to repo root."""
        if not raw_paths:
            return []

        # Special case: if "." is in raw_paths, it means entire app
        if "." in raw_paths:
            return ["./"]

        # Extract directory paths and normalize
        dir_paths = set()
        for path in raw_paths:
            if path:
                # Remove leading ./
                clean_path = path.lstrip("./")

                # Get the directory part
                if "/" in clean_path:
                    # Extract the first directory level
                    dir_part = clean_path.split("/")[0]
                    if dir_part and dir_part not in [
                        "app",
                        "usr",
                        "opt",
                    ]:  # Skip system dirs
                        dir_paths.add(dir_part)
                elif clean_path and "." in clean_path:
                    # If it's a file, extract the directory
                    if clean_path.count("/") == 0:
                        # File in current directory, extract base name
                        base = clean_path.split(".")[0]
                        if base and len(base) > 1:
                            dir_paths.add(base)
                elif clean_path and clean_path not in ["app", "usr", "opt"]:
                    # Single directory name
                    dir_paths.add(clean_path)

        # Convert to sorted list and consolidate parent/child relationships
        consolidated = []
        for path in sorted(dir_paths):
            # Don't add if a parent directory already exists
            if not any(path.startswith(existing + "/") for existing in consolidated):
                # Remove any existing child directories
                consolidated = [p for p in consolidated if not path.startswith(p + "/")]
                consolidated.append(path)

        # Add trailing slash to indicate directories and sort
        return sorted([f"{path}/" for path in consolidated])

    def _deep_search_dockerfile(
        self, repo_path: Path, chart_name: str
    ) -> Optional[Path]:
        """Deep search for Dockerfiles matching chart name patterns."""
        # Common naming patterns for Dockerfiles
        naming_patterns = [
            # Direct match
            chart_name,
            # Remove common suffixes
            chart_name.replace("-chart", "").replace("-helm", "").rstrip("-"),
            # Handle subdirectory patterns (like plexalyzer-prov -> plexalyzer/prov)
            chart_name.replace("-", "/"),
            # Handle provider patterns (like plexalyzer-prov -> plexalyzer/prov)
            chart_name.replace("-prov", "/prov").replace("-code", "/code"),
            # Handle tool-parser -> exporter mapping
            "tool-parser" if chart_name == "exporter" else None,
        ]

        # Filter out None patterns
        naming_patterns = [p for p in naming_patterns if p is not None]

        # Search for Dockerfiles in the entire repository
        for dockerfile_path in repo_path.rglob("Dockerfile"):
            # Skip Dockerfiles in node_modules, .git, etc.
            if any(
                segment.startswith(".") or segment in ["node_modules", "vendor"]
                for segment in dockerfile_path.parts
            ):
                continue

            # Check if Dockerfile path matches any of our naming patterns
            dockerfile_dir = dockerfile_path.parent
            relative_path = dockerfile_dir.relative_to(repo_path)

            for pattern in naming_patterns:
                # Check if the pattern matches the directory structure
                if self._matches_pattern(str(relative_path), pattern):
                    return dockerfile_path

                # Also check if the pattern matches the parent directory
                if dockerfile_dir.name == pattern:
                    return dockerfile_path

        return None

    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if a path matches a naming pattern."""
        # Direct match
        if path == pattern:
            return True

        # Pattern as subdirectory
        if path.endswith(f"/{pattern}"):
            return True

        # Pattern with dashes replaced by slashes
        if pattern.replace("-", "/") in path:
            return True

        # Handle complex patterns like "plexalyzer-prov" -> "plexalyzer/prov"
        if "-" in pattern:
            parts = pattern.split("-")
            if len(parts) == 2:
                expected_path = f"{parts[0]}/{parts[1]}"
                if path == expected_path or path.endswith(f"/{expected_path}"):
                    return True

        return False

    def _validate_source_paths(
        self, source_paths: List[str], repo_root: Path
    ) -> List[str]:
        """Validate extracted source paths against actual repository structure."""
        if not source_paths:
            return []

        validated_paths = []

        for path in source_paths:
            # Skip empty paths
            if not path or path == "./":
                continue

            # Remove trailing slash for validation
            clean_path = path.rstrip("/")

            # Check if the path exists in the repository
            full_path = repo_root / clean_path
            if full_path.exists():
                validated_paths.append(path)
            else:
                # Check if any parent directory exists
                parent_path = full_path
                while parent_path != repo_root and parent_path.parent != repo_root:
                    parent_path = parent_path.parent
                    if parent_path.exists():
                        # Use the existing parent directory
                        relative_parent = parent_path.relative_to(repo_root)
                        validated_paths.append(f"{relative_parent}/")
                        break

        # Remove duplicates and sort
        return sorted(list(set(validated_paths)))
