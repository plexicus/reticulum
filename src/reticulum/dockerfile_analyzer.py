"""
Dockerfile Analysis Module for Reticulum.

Handles Dockerfile parsing and source code path extraction.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import re

from .build_context_analyzer import BuildContextAnalyzer


class DockerfileAnalyzer:
    """Analyzes Dockerfiles to extract source code paths and container information."""

    def find_dockerfile(
        self, chart_dir: Path, repo_path: Path, chart_name: str
    ) -> Optional[Path]:
        """Find Dockerfile for a chart in the repository."""
        discovery_log = []

        # Strategy 1: Look for Dockerfile in chart directory
        dockerfile = chart_dir / "Dockerfile"
        if dockerfile.exists():
            discovery_log.append(f"✅ Strategy 1: Found Dockerfile in chart directory: {dockerfile}")
            self._log_discovery_strategies(chart_name, discovery_log)
            return dockerfile
        else:
            discovery_log.append(f"❌ Strategy 1: No Dockerfile in chart directory: {dockerfile}")

        # Strategy 2: Look in subdirectories of chart
        for subdir in chart_dir.iterdir():
            if subdir.is_dir():
                dockerfile = subdir / "Dockerfile"
                if dockerfile.exists():
                    discovery_log.append(f"✅ Strategy 2: Found Dockerfile in chart subdirectory: {dockerfile}")
                    self._log_discovery_strategies(chart_name, discovery_log)
                    return dockerfile
        discovery_log.append(f"❌ Strategy 2: No Dockerfile in chart subdirectories")

        # Strategy 3: Look for Dockerfile in repo root with same name as chart
        dockerfile = repo_path / chart_name / "Dockerfile"
        if dockerfile.exists():
            discovery_log.append(f"✅ Strategy 3: Found Dockerfile in repo root: {dockerfile}")
            self._log_discovery_strategies(chart_name, discovery_log)
            return dockerfile
        else:
            discovery_log.append(f"❌ Strategy 3: No Dockerfile in repo root: {dockerfile}")

        # Strategy 4: Look in repo root (for single-app repos)
        dockerfile = repo_path / "Dockerfile"
        if dockerfile.exists():
            discovery_log.append(f"✅ Strategy 4: Found Dockerfile in repo root: {dockerfile}")
            self._log_discovery_strategies(chart_name, discovery_log)
            return dockerfile
        else:
            discovery_log.append(f"❌ Strategy 4: No Dockerfile in repo root: {dockerfile}")

        # Strategy 5: Look in common locations
        common_paths = [
            repo_path / "src" / chart_name / "Dockerfile",
            repo_path / "apps" / chart_name / "Dockerfile",
            repo_path / "services" / chart_name / "Dockerfile",
        ]

        for path in common_paths:
            if path.exists():
                discovery_log.append(f"✅ Strategy 5: Found Dockerfile in common location: {path}")
                self._log_discovery_strategies(chart_name, discovery_log)
                return path
        discovery_log.append(f"❌ Strategy 5: No Dockerfile in common locations")

        # Strategy 6: Look for Dockerfile variants (Dockerfile.*)
        for variant in ["Dockerfile.dev", "Dockerfile.prod", "Dockerfile.staging"]:
            dockerfile = chart_dir / variant
            if dockerfile.exists():
                discovery_log.append(f"✅ Strategy 6: Found Dockerfile variant: {dockerfile}")
                self._log_discovery_strategies(chart_name, discovery_log)
                return dockerfile
        discovery_log.append(f"❌ Strategy 6: No Dockerfile variants found")

        # Strategy 7: Deep search in repository for any Dockerfile matching chart name patterns
        dockerfile = self._deep_search_dockerfile(repo_path, chart_name)
        if dockerfile:
            discovery_log.append(f"✅ Strategy 7: Found Dockerfile via deep search: {dockerfile}")
            self._log_discovery_strategies(chart_name, discovery_log)
            return dockerfile
        else:
            discovery_log.append(f"❌ Strategy 7: Deep search failed for chart: {chart_name}")

        # Strategy 8: Look for Dockerfiles in common dockerfiles directory
        dockerfile_patterns = [
            f"{chart_name}.Dockerfile",
            f"{chart_name.replace('-service', '')}.Dockerfile",
            f"{chart_name.replace('-web', '')}.Dockerfile",
            f"{chart_name.replace('-gateway', '')}.Dockerfile",
            f"{chart_name.replace('-stack', '')}.Dockerfile",
            f"Dockerfile.{chart_name}",
            f"Dockerfile.{chart_name.replace('-service', '')}",
            f"Dockerfile.{chart_name.replace('-web', '')}",
            f"Dockerfile.{chart_name.replace('-gateway', '')}",
            f"Dockerfile.{chart_name.replace('-stack', '')}",
        ]

        # Remove duplicate patterns
        dockerfile_patterns = list(set(dockerfile_patterns))

        dockerfiles_dir = repo_path / "dockerfiles"
        if dockerfiles_dir.exists():
            for pattern in dockerfile_patterns:
                dockerfile = dockerfiles_dir / pattern
                if dockerfile.exists():
                    discovery_log.append(f"✅ Strategy 8: Found Dockerfile in dockerfiles directory: {dockerfile}")
                    self._log_discovery_strategies(chart_name, discovery_log)
                    return dockerfile
            discovery_log.append(f"❌ Strategy 8: No matching Dockerfile in dockerfiles directory for patterns: {dockerfile_patterns}")
        else:
            discovery_log.append(f"❌ Strategy 8: dockerfiles directory does not exist: {dockerfiles_dir}")

        # Strategy 9: Look for any Dockerfile in the repository that might match
        dockerfile = self._find_any_dockerfile_for_chart(repo_path, chart_name)
        if dockerfile:
            discovery_log.append(f"✅ Strategy 9: Found potential Dockerfile: {dockerfile}")
            self._log_discovery_strategies(chart_name, discovery_log)
            return dockerfile

        discovery_log.append(f"❌ All Dockerfile discovery strategies failed for chart: {chart_name}")
        self._log_discovery_strategies(chart_name, discovery_log)
        return None

    def _find_any_dockerfile_for_chart(
        self, repo_path: Path, chart_name: str
    ) -> Optional[Path]:
        """
        Find any Dockerfile in the repository that might be related to the chart.

        This is a fallback strategy that searches for any Dockerfile with flexible
        pattern matching when other strategies fail.
        """
        # Generate flexible patterns for the chart name
        patterns = self._generate_flexible_patterns(chart_name)

        # Search for Dockerfiles in the entire repository
        for dockerfile_path in repo_path.rglob("*Dockerfile*"):
            # Skip files in ignore directories
            if self._should_ignore_dockerfile(dockerfile_path):
                continue

            # Check if this Dockerfile matches any of our patterns
            if self._matches_flexible_pattern(dockerfile_path, patterns, chart_name):
                return dockerfile_path

        return None

    def _generate_flexible_patterns(self, chart_name: str) -> List[str]:
        """Generate flexible patterns for chart name matching."""
        patterns = []

        # Clean the chart name
        clean_name = (
            chart_name.replace("-chart", "")
            .replace("-helm", "")
            .replace("-service", "")
            .replace("-app", "")
            .replace("-gateway", "")
            .replace("-api", "")
            .replace("-web", "")
            .rstrip("-")
        )

        # Generate various pattern combinations
        patterns.extend([
            clean_name,
            clean_name.replace("-", ""),
            clean_name.replace("-", "_"),
            clean_name.lower(),
            clean_name.upper(),
        ])

        # Add common variations for microservices
        if "-" in clean_name:
            parts = clean_name.split("-")
            if len(parts) >= 2:
                patterns.extend([
                    parts[0],  # First part only
                    parts[-1],  # Last part only
                    f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else "",
                ])

        # Remove empty patterns and duplicates
        patterns = [p for p in patterns if p]
        patterns = list(set(patterns))

        return patterns

    def _should_ignore_dockerfile(self, dockerfile_path: Path) -> bool:
        """Check if Dockerfile path should be ignored."""
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

        path_str = str(dockerfile_path)
        return any(pattern in path_str for pattern in ignore_patterns)

    def _matches_flexible_pattern(
        self, dockerfile_path: Path, patterns: List[str], chart_name: str
    ) -> bool:
        """Check if Dockerfile matches any flexible pattern."""
        dockerfile_name = dockerfile_path.name
        dockerfile_parent = dockerfile_path.parent.name

        # Check Dockerfile name patterns
        for pattern in patterns:
            if pattern and (
                pattern in dockerfile_name or
                pattern in dockerfile_parent or
                pattern in str(dockerfile_path.relative_to(dockerfile_path.parent.parent))
            ):
                return True

        # Check for exact chart name in path
        if chart_name in str(dockerfile_path):
            return True

        return False

    def analyze_dockerfile_with_build_context(
        self, dockerfile_path: Path, repo_root: Path, chart_name: str = ""
    ) -> Dict[str, Any]:
        """
        Enhanced Dockerfile analysis with build context awareness.

        Args:
            dockerfile_path: Path to the Dockerfile
            repo_root: Root path of the repository
            chart_name: Name of the Helm chart (for context inference)

        Returns:
            Comprehensive Dockerfile analysis with build context
        """
        build_context_analyzer = BuildContextAnalyzer()

        # Get basic source paths (legacy method)
        basic_source_paths = self.parse_dockerfile_for_source_paths(
            dockerfile_path, repo_root
        )

        # Get enhanced build context analysis
        build_context_analysis = (
            build_context_analyzer.analyze_dockerfile_build_context(
                dockerfile_path, repo_root, chart_name
            )
        )

        # Combine results
        analysis = {
            "dockerfile_path": str(dockerfile_path.relative_to(repo_root)),
            "basic_source_paths": basic_source_paths,
            "build_context_analysis": build_context_analysis,
            "combined_source_paths": self._combine_source_paths(
                basic_source_paths, build_context_analysis["source_paths"]
            ),
        }

        return analysis

    def _combine_source_paths(
        self, basic_paths: List[str], context_paths: List[str]
    ) -> List[str]:
        """Combine source paths from basic analysis and build context analysis."""
        combined = set(basic_paths + context_paths)

        # Consolidate paths
        consolidated = []
        for path in sorted(combined):
            # Don't add if a parent directory already exists
            if not any(path.startswith(existing + "/") for existing in consolidated):
                # Remove any existing child directories
                consolidated = [p for p in consolidated if not path.startswith(p + "/")]
                consolidated.append(path)

        return sorted(consolidated)

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

    def _log_discovery_strategies(self, chart_name: str, discovery_log: List[str]):
        """Log Dockerfile discovery strategies for debugging."""
        if len(discovery_log) > 1:  # Only log if we have multiple strategies
            print(f"\n🔍 Dockerfile Discovery Log for chart '{chart_name}':")
            for log_entry in discovery_log:
                print(f"   {log_entry}")
