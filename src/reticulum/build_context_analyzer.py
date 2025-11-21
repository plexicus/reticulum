"""
Build Context Analyzer for Reticulum.

Analyzes Dockerfiles and repository structure to infer build contexts
and establish relationships between Dockerfiles, source code, and services.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import re

from .service_registry import ServiceRegistry
from .reverse_ownership_index import ReverseOwnershipIndex
from .dockerfile_parser import DockerfileParser


class BuildContextAnalyzer:
    """Analyzes build contexts for Dockerfiles and establishes source code relationships."""

    def __init__(self):
        self.common_source_patterns = [
            "source-code",
            "src",
            "app",
            "apps",
            "services",
            "microservices",
            "backend",
            "frontend",
        ]

        # Unified Strategy components
        self.service_registry = ServiceRegistry()
        self.reverse_ownership_index = ReverseOwnershipIndex()
        self.dockerfile_parser = DockerfileParser()

    def analyze_dockerfile_build_context(
        self, dockerfile_path: Path, repo_root: Path, chart_name: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze Dockerfile to determine build context and source code relationships.

        Args:
            dockerfile_path: Path to the Dockerfile
            repo_root: Root path of the repository
            chart_name: Name of the Helm chart (for context inference)

        Returns:
            Dictionary with build context analysis
        """
        analysis = {
            "dockerfile_path": str(dockerfile_path.relative_to(repo_root)),
            "build_context": "",
            "source_paths": [],
            "build_context_type": "unknown",
            "confidence": "low",
            "inference_methods": [],
        }

        discovery_log = []

        # Strategy 1: Check if Dockerfile is in a source code directory
        build_context = self._infer_build_context_from_location(
            dockerfile_path, repo_root, chart_name
        )
        if build_context:
            analysis["build_context"] = str(build_context.relative_to(repo_root))
            analysis["build_context_type"] = "source_directory"
            analysis["confidence"] = "high"
            analysis["inference_methods"].append("directory_location")
            discovery_log.append(f"✅ Strategy 1: Found build context via directory location: {analysis['build_context']}")
        else:
            discovery_log.append(f"❌ Strategy 1: No build context found via directory location")

        # Strategy 2: Analyze Dockerfile commands for build context hints
        if not analysis["build_context"]:
            build_context = self._infer_build_context_from_commands(
                dockerfile_path, repo_root
            )
            if build_context:
                analysis["build_context"] = str(build_context.relative_to(repo_root))
                analysis["build_context_type"] = "command_analysis"
                analysis["confidence"] = "medium"
                analysis["inference_methods"].append("dockerfile_commands")
                discovery_log.append(f"✅ Strategy 2: Found build context via command analysis: {analysis['build_context']}")
            else:
                discovery_log.append(f"❌ Strategy 2: No build context found via command analysis")

        # Strategy 3: Use chart name to find matching source directory
        if not analysis["build_context"] and chart_name:
            build_context = self._infer_build_context_from_chart_name(
                chart_name, repo_root
            )
            if build_context:
                analysis["build_context"] = str(build_context.relative_to(repo_root))
                analysis["build_context_type"] = "chart_name_matching"
                analysis["confidence"] = "medium"
                analysis["inference_methods"].append("chart_name_matching")
                discovery_log.append(f"✅ Strategy 3: Found build context via chart name matching: {analysis['build_context']}")
            else:
                discovery_log.append(f"❌ Strategy 3: No build context found via chart name matching for chart: {chart_name}")

        # Strategy 4: Fall back to Dockerfile directory
        if not analysis["build_context"]:
            analysis["build_context"] = str(
                dockerfile_path.parent.relative_to(repo_root)
            )
            analysis["build_context_type"] = "dockerfile_directory"
            analysis["confidence"] = "low"
            analysis["inference_methods"].append("fallback_dockerfile_dir")
            discovery_log.append(f"⚠️  Strategy 4: Falling back to Dockerfile directory: {analysis['build_context']}")

        # Extract source paths relative to build context
        analysis["source_paths"] = self._extract_source_paths_relative_to_context(
            dockerfile_path, Path(repo_root) / analysis["build_context"]
        )

        # Log the discovery process
        self._log_build_context_discovery(chart_name or "unknown", discovery_log, analysis)

        return analysis

    def _infer_build_context_from_location(
        self, dockerfile_path: Path, repo_root: Path, chart_name: str
    ) -> Optional[Path]:
        """Infer build context based on Dockerfile location and repository structure."""
        dockerfile_dir = dockerfile_path.parent

        # Case 1: Dockerfile is in a common source directory
        for pattern in self.common_source_patterns:
            if pattern in str(dockerfile_dir.relative_to(repo_root)):
                return dockerfile_dir

        # Case 2: Dockerfile is in dockerfiles/ directory - find matching source
        if "dockerfiles" in str(dockerfile_dir.relative_to(repo_root)):
            # Try to find matching source code directory
            dockerfile_name = (
                dockerfile_path.stem
            )  # e.g., "frontend" from "frontend.Dockerfile"

            # Priority 1: Chart name based matching
            if chart_name:
                source_dir = self._find_matching_source_directory(chart_name, repo_root)
                if source_dir:
                    return source_dir

            # Priority 2: Dockerfile name based matching
            source_dir = self._find_matching_source_directory(
                dockerfile_name, repo_root
            )
            if source_dir:
                return source_dir

            # Priority 3: Enhanced pattern matching for common structures
            source_dir = self._find_source_by_enhanced_patterns(
                dockerfile_name, chart_name, repo_root
            )
            if source_dir:
                return source_dir

        # Case 3: Dockerfile is in chart directory - check for source subdirectory
        if "charts" in str(dockerfile_dir.relative_to(repo_root)):
            # Look for source, src, or app subdirectory
            for subdir_name in ["src", "source", "app", "application"]:
                source_subdir = dockerfile_dir / subdir_name
                if source_subdir.exists() and source_subdir.is_dir():
                    return source_subdir

        return None

    def _find_source_by_enhanced_patterns(
        self, dockerfile_name: str, chart_name: str, repo_root: Path
    ) -> Optional[Path]:
        """
        Find source directory using enhanced pattern matching for common repository structures.
        """
        # Generate candidate names
        candidates = []

        # Use chart name if available
        if chart_name:
            candidates.append(chart_name)
            # Clean chart name
            clean_chart = (
                chart_name.replace("-chart", "")
                .replace("-helm", "")
                .replace("-service", "")
                .replace("-app", "")
                .rstrip("-")
            )
            candidates.append(clean_chart)

        # Use Dockerfile name
        candidates.append(dockerfile_name)
        clean_dockerfile = (
            dockerfile_name.replace("Dockerfile", "")
            .replace("dockerfile", "")
            .replace(".", "")
            .rstrip("-")
            .rstrip("_")
        )
        if clean_dockerfile:
            candidates.append(clean_dockerfile)

        # Generate variations
        all_candidates = []
        for candidate in candidates:
            if candidate:
                all_candidates.extend([
                    candidate,
                    candidate.replace("-", ""),
                    candidate.replace("-", "_"),
                    candidate.lower(),
                    candidate.upper(),
                ])

        # Remove duplicates and empty
        all_candidates = list(set([c for c in all_candidates if c]))

        # Search patterns
        search_patterns = []
        for candidate in all_candidates:
            search_patterns.extend([
                f"source-code/{candidate}",
                f"src/{candidate}",
                f"apps/{candidate}",
                f"services/{candidate}",
                f"microservices/{candidate}",
                f"backend/{candidate}",
                f"frontend/{candidate}",
                candidate,  # Direct match
            ])

        # Search for existing directories
        for pattern in search_patterns:
            potential_dir = repo_root / pattern
            if potential_dir.exists() and potential_dir.is_dir():
                return potential_dir

        return None

    def _infer_build_context_from_commands(
        self, dockerfile_path: Path, repo_root: Path
    ) -> Optional[Path]:
        """Infer build context by analyzing Dockerfile COPY/ADD commands."""
        try:
            with open(dockerfile_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Look for COPY/ADD commands that copy entire directories
            copy_patterns = [
                r"COPY\s+\.\s+\.",  # COPY . .
                r"ADD\s+\.\s+\.",  # ADD . .
                r"COPY\s+\.\s+/app",  # COPY . /app
                r"ADD\s+\.\s+/app",  # ADD . /app
            ]

            for pattern in copy_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    # If copying current directory, build context is Dockerfile directory
                    return dockerfile_path.parent

            # Look for COPY commands with specific source patterns
            specific_copy_pattern = r"(?:COPY|ADD)\s+([^\s]+)\s+([^\s]+)"
            matches = re.findall(specific_copy_pattern, content, re.IGNORECASE)

            for source, _ in matches:
                source = source.strip("'\"")
                if source != "." and not source.startswith(
                    ("--", "http://", "https://")
                ):
                    # Check if this source exists relative to Dockerfile directory
                    potential_path = dockerfile_path.parent / source
                    if potential_path.exists():
                        return dockerfile_path.parent

        except (IOError, UnicodeDecodeError):
            pass

        return None

    def _infer_build_context_from_chart_name(
        self, chart_name: str, repo_root: Path
    ) -> Optional[Path]:
        """Infer build context by matching chart name to source directories."""
        return self._find_matching_source_directory(chart_name, repo_root)

    def _find_matching_source_directory(
        self, name: str, repo_root: Path
    ) -> Optional[Path]:
        """Find a source directory that matches the given name."""
        # Remove common suffixes
        clean_name = (
            name.replace("-chart", "")
            .replace("-helm", "")
            .replace("-service", "")
            .replace("-app", "")
            .rstrip("-")
        )

        # Search patterns
        search_patterns = [
            f"source-code/{clean_name}",
            f"src/{clean_name}",
            f"apps/{clean_name}",
            f"services/{clean_name}",
            f"microservices/{clean_name}",
            f"backend/{clean_name}",
            f"frontend/{clean_name}",
            clean_name,  # Direct match
        ]

        for pattern in search_patterns:
            potential_dir = repo_root / pattern
            if potential_dir.exists() and potential_dir.is_dir():
                return potential_dir

        return None

    def _extract_source_paths_relative_to_context(
        self, dockerfile_path: Path, build_context: Path
    ) -> List[str]:
        """Extract source paths from Dockerfile relative to build context."""
        source_paths = []

        try:
            with open(dockerfile_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue

                # Look for COPY and ADD instructions
                copy_match = re.match(
                    r"(?:COPY|ADD)\s+([^\s]+)\s+([^\s]+)", line, re.IGNORECASE
                )
                if copy_match:
                    source, _ = copy_match.groups()
                    source = source.strip("'\"")

                    # Skip special cases
                    if source.startswith(("--", "http://", "https://", "$")):
                        continue

                    # Handle current directory copy
                    if source == ".":
                        source_paths.append("./")
                        continue

                    # Check if source exists relative to build context
                    if source != ".":
                        potential_path = build_context / source
                        if potential_path.exists():
                            # Make path relative to build context
                            if potential_path.is_dir():
                                source_paths.append(f"{source}/")
                            else:
                                # For files, use parent directory
                                parent_dir = potential_path.parent.relative_to(
                                    build_context
                                )
                                if str(parent_dir) != ".":
                                    source_paths.append(f"{parent_dir}/")

        except (IOError, UnicodeDecodeError):
            pass

        # Remove duplicates and consolidate
        unique_paths = list(set(source_paths))
        consolidated_paths = self._consolidate_paths(unique_paths)

        return sorted(consolidated_paths)

    def _consolidate_paths(self, paths: List[str]) -> List[str]:
        """Consolidate paths to remove redundant parent/child relationships."""
        if not paths:
            return []

        # Sort paths by length (shortest first)
        sorted_paths = sorted(paths, key=len)

        consolidated = []
        for path in sorted_paths:
            # Check if this path is already covered by a parent path
            is_covered = any(
                path.startswith(existing + "/") or path == existing
                for existing in consolidated
            )

            if not is_covered:
                # Remove any existing paths that are children of this one
                consolidated = [
                    p
                    for p in consolidated
                    if not (p.startswith(path + "/") or p == path)
                ]
                consolidated.append(path)

        return sorted(consolidated)

    def build_service_mapping_table(
        self, exposure_results: Dict[str, Any], repo_root: Path
    ) -> Dict[str, Any]:
        """
        Build comprehensive service-to-source mapping table.

        Args:
            exposure_results: Results from exposure scanner
            repo_root: Root path of the repository

        Returns:
            Service mapping table with build context relationships
        """
        mapping_table = {
            "services": {},
            "summary": {
                "total_services": 0,
                "services_with_build_context": 0,
                "services_with_source_paths": 0,
            },
        }

        for container in exposure_results.get("containers", []):
            service_name = container.get("name", "")
            chart_name = container.get("chart", "")
            dockerfile_path_str = container.get("dockerfile_path", "")

            if not service_name:
                continue

            service_mapping = {
                "service_name": service_name,
                "chart_name": chart_name,
                "dockerfile_path": dockerfile_path_str,
                "build_context": "",
                "source_paths": [],
                "build_context_analysis": {},
                "exposure_level": container.get("exposure_level", "LOW"),
            }

            # Analyze build context if Dockerfile is available
            if dockerfile_path_str:
                dockerfile_path = Path(repo_root) / dockerfile_path_str
                if dockerfile_path.exists():
                    build_context_analysis = self.analyze_dockerfile_build_context(
                        dockerfile_path, repo_root, chart_name
                    )

                    service_mapping["build_context"] = build_context_analysis[
                        "build_context"
                    ]
                    service_mapping["source_paths"] = build_context_analysis[
                        "source_paths"
                    ]
                    service_mapping["build_context_analysis"] = build_context_analysis

                    if build_context_analysis["build_context"]:
                        mapping_table["summary"]["services_with_build_context"] += 1
                    if build_context_analysis["source_paths"]:
                        mapping_table["summary"]["services_with_source_paths"] += 1

            mapping_table["services"][service_name] = service_mapping
            mapping_table["summary"]["total_services"] += 1

        return mapping_table

    # Enhanced Implicit Territory Claiming Methods

    def claim_implicit_territory_intelligent(
        self, service_token: str, dockerfile_path: Path, repo_root: Path
    ) -> None:
        """
        Claim implicit territory using intelligent heuristics beyond just the Dockerfile directory.

        Args:
            service_token: Service token
            dockerfile_path: Path to Dockerfile
            repo_root: Repository root path
        """
        # 1. Claim Dockerfile parent directory (standard implicit territory)
        dockerfile_dir = dockerfile_path.parent
        self.reverse_ownership_index.claim_implicit_territory(
            service_token, dockerfile_dir
        )

        # 2. Claim inferred build context directory
        build_context_analysis = self.analyze_dockerfile_build_context(
            dockerfile_path, repo_root
        )
        if build_context_analysis["build_context"]:
            build_context_path = (
                Path(repo_root) / build_context_analysis["build_context"]
            )
            if build_context_path != dockerfile_dir:
                self.reverse_ownership_index.claim_implicit_territory(
                    service_token, build_context_path
                )

        # 3. Claim common parent directories based on repository structure
        self._claim_common_parent_territories(service_token, dockerfile_path, repo_root)

    def _claim_common_parent_territories(
        self, service_token: str, dockerfile_path: Path, repo_root: Path
    ) -> None:
        """
        Claim common parent directories that might contain shared resources.

        Args:
            service_token: Service token
            dockerfile_path: Path to Dockerfile
            repo_root: Repository root path
        """
        dockerfile_dir = dockerfile_path.parent

        # Claim parent directories up to certain depth
        current_path = dockerfile_dir
        depth = 0
        max_depth = 3

        while current_path != repo_root and depth < max_depth:
            # Check if this directory contains common shared resources
            if self._contains_shared_resources(current_path):
                self.reverse_ownership_index.claim_implicit_territory(
                    service_token, current_path
                )

            current_path = current_path.parent
            depth += 1

    def _contains_shared_resources(self, directory: Path) -> bool:
        """
        Check if directory contains files/directories that indicate shared resources.

        Args:
            directory: Directory to check

        Returns:
            True if directory contains shared resources
        """
        shared_patterns = [
            "shared",
            "common",
            "lib",
            "library",
            "utils",
            "utilities",
            "config",
            "configuration",
            "assets",
            "resources",
        ]

        try:
            for item in directory.iterdir():
                if item.is_dir():
                    item_name = item.name.lower()
                    if any(pattern in item_name for pattern in shared_patterns):
                        return True
                elif item.is_file():
                    # Check for common configuration files
                    if item.name in [
                        "package.json",
                        "requirements.txt",
                        "pom.xml",
                        "build.gradle",
                        "Makefile",
                    ]:
                        return True
        except (OSError, PermissionError):
            pass

        return False

    # Unified Strategy Integration Methods

    def analyze_with_unified_strategy(self, repo_root: Path) -> Dict[str, Any]:
        """
        Analyze repository using Unified Pareto Strategy components.

        Args:
            repo_root: Root path of the repository

        Returns:
            Comprehensive analysis with service identification and territory claiming
        """
        # Discover all Dockerfiles
        dockerfiles = self._discover_dockerfiles(repo_root)

        # Register services from Dockerfiles
        for dockerfile_path in dockerfiles:
            self.service_registry.register_service_from_dockerfile(
                dockerfile_path, repo_root
            )

        # Claim implicit territory for all services
        for service in self.service_registry.get_all_services():
            self.reverse_ownership_index.claim_implicit_territory(
                service.token, service.parent_directory
            )

        # Claim explicit territory from Dockerfile COPY/ADD commands
        for dockerfile_path in dockerfiles:
            service_info = self.service_registry.get_service_by_dockerfile(
                dockerfile_path.relative_to(repo_root)
            )
            if service_info:
                source_paths = self.dockerfile_parser.parse_dockerfile(
                    dockerfile_path, dockerfile_path.parent, repo_root
                )
                self.reverse_ownership_index.claim_explicit_territory(
                    service_info.token, source_paths
                )

        # Generate comprehensive results
        results = {
            "service_identification": {
                "total_services": len(self.service_registry.get_all_services()),
                "services": [
                    {
                        "token": service.token,
                        "dockerfile": str(service.dockerfile_path),
                        "parent_directory": str(service.parent_directory),
                    }
                    for service in self.service_registry.get_all_services()
                ],
            },
            "territory_claiming": {
                "ownership_statistics": self.reverse_ownership_index.get_index_statistics(),
                "shared_folders": self.reverse_ownership_index.get_shared_folders(),
                "service_coverage": {
                    service.token: self.reverse_ownership_index.get_service_coverage(
                        service.token
                    )
                    for service in self.service_registry.get_all_services()
                },
            },
            "build_context_analysis": {
                "total_dockerfiles": len(dockerfiles),
                "dockerfiles": [
                    self.analyze_dockerfile_build_context(df, repo_root)
                    for df in dockerfiles
                ],
            },
        }

        return results

    def _discover_dockerfiles(self, repo_path: Path) -> List[Path]:
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

    def get_service_for_file(self, file_path: Path) -> Optional[str]:
        """
        Get the primary service token for a file using reverse ownership index.

        Args:
            file_path: File path

        Returns:
            Service token, or None if not found
        """
        owners = self.reverse_ownership_index.get_owners_for_path(file_path)
        return owners[0] if owners else None

    def get_build_context_for_service(self, service_token: str) -> Optional[Path]:
        """
        Get the build context directory for a service.

        Args:
            service_token: Service token

        Returns:
            Build context path, or None if not found
        """
        service_info = self.service_registry.get_service_by_token(service_token)
        if service_info:
            return service_info.parent_directory
        return None

    def get_affected_services_for_changes(
        self, changed_files: List[Path]
    ) -> Dict[str, List[str]]:
        """
        Get services affected by file changes using reverse ownership index.

        Args:
            changed_files: List of changed file paths

        Returns:
            Dictionary mapping service tokens to affected file paths
        """
        affected_services = {}

        for file_path in changed_files:
            owners = self.reverse_ownership_index.get_owners_for_path(file_path)
            for owner in owners:
                if owner not in affected_services:
                    affected_services[owner] = []
                affected_services[owner].append(str(file_path))

        return affected_services

    def _log_build_context_discovery(self, chart_name: str, discovery_log: List[str], analysis: Dict[str, Any]):
        """Log build context discovery strategies for debugging."""
        if len(discovery_log) > 1:  # Only log if we have multiple strategies
            print(f"\n🔍 Build Context Discovery Log for chart '{chart_name}':")
            for log_entry in discovery_log:
                print(f"   {log_entry}")
            print(f"   📊 Final Analysis:")
            print(f"     - Build Context: {analysis['build_context']}")
            print(f"     - Type: {analysis['build_context_type']}")
            print(f"     - Confidence: {analysis['confidence']}")
            print(f"     - Source Paths: {analysis['source_paths']}")
            print(f"     - Methods: {analysis['inference_methods']}")
