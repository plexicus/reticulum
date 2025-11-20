"""
Dockerfile Parser for Unified Pareto Strategy

Advanced parsing of Dockerfile COPY and ADD commands to extract source paths
and build the reverse ownership index.
"""

import re
from pathlib import Path
from typing import List, Optional


class DockerfileParser:
    """
    Advanced Dockerfile parser for COPY and ADD command analysis.

    Implements Phase 2 of the Unified Pareto Strategy:
    - Parse COPY and ADD commands using regex
    - Normalize relative paths to absolute repository paths
    - Extract source paths for territory claiming
    """

    def __init__(self):
        # Regex pattern for COPY and ADD commands
        # Matches: COPY source dest, ADD source dest
        # Handles: COPY source1 source2 ... dest, ADD source1 source2 ... dest
        self.copy_add_pattern = re.compile(
            r"^\s*(?:COPY|ADD)\s+([^\n]+)", re.IGNORECASE | re.MULTILINE
        )

        # Pattern to extract individual source paths from the command
        self.source_paths_pattern = re.compile(r"([^\s\"]+|\"[^\"]+\")", re.IGNORECASE)

    def parse_dockerfile(
        self, dockerfile_path: Path, build_context: Path, repo_root: Path
    ) -> List[Path]:
        """
        Parse a Dockerfile and extract all source paths from COPY/ADD commands.

        Args:
            dockerfile_path: Path to the Dockerfile
            build_context: Build context directory (where Dockerfile is executed from)
            repo_root: Root of the repository

        Returns:
            List of normalized source paths relative to repo root
        """
        if not dockerfile_path.exists():
            return []

        try:
            content = dockerfile_path.read_text(encoding="utf-8")
        except Exception:
            return []

        source_paths = set()

        # Ensure repo_root is absolute for proper path resolution
        repo_root = repo_root.resolve()
        build_context = build_context.resolve()

        # Find all COPY and ADD commands
        for match in self.copy_add_pattern.finditer(content):
            command_args = match.group(1).strip()

            # Extract source paths from command arguments
            paths = self._extract_source_paths(command_args)

            # Normalize each path relative to repo root
            for path_str in paths:
                normalized_path = self._normalize_path(
                    path_str, build_context, repo_root
                )
                if normalized_path:
                    source_paths.add(normalized_path)

        return list(source_paths)

    def _extract_source_paths(self, command_args: str) -> List[str]:
        """
        Extract individual source paths from COPY/ADD command arguments.

        Args:
            command_args: The arguments portion of COPY/ADD command

        Returns:
            List of source path strings
        """
        # Remove quotes and split into individual paths
        paths = []

        # Handle quoted paths
        quoted_paths = re.findall(r'"([^"]+)"', command_args)
        paths.extend(quoted_paths)

        # Remove quoted sections from remaining string
        remaining = re.sub(r'"[^"]+"', "", command_args)

        # Extract unquoted paths
        unquoted_paths = self.source_paths_pattern.findall(remaining)
        paths.extend([p.strip('"') for p in unquoted_paths])

        # Filter out empty paths and destination paths (last one)
        if paths:
            # The last path is typically the destination
            paths = paths[:-1]

        return [p for p in paths if p and not p.startswith("--")]

    def _normalize_path(
        self, path_str: str, build_context: Path, repo_root: Path
    ) -> Optional[Path]:
        """
        Normalize a source path to absolute repository path.

        Args:
            path_str: Source path from Dockerfile
            build_context: Build context directory
            repo_root: Repository root

        Returns:
            Normalized Path relative to repo root, or None if invalid
        """
        # Handle relative paths
        if path_str.startswith("./") or path_str.startswith("../"):
            # Resolve relative to build context
            resolved_path = (build_context / path_str).resolve()
        else:
            # Assume path is relative to build context
            resolved_path = (build_context / path_str).resolve()

        # Convert to relative path from repo root
        try:
            relative_path = resolved_path.relative_to(repo_root)

            # Ensure path exists in repository
            if (repo_root / relative_path).exists():
                return relative_path
            else:
                return None

        except ValueError:
            # Path is outside repository
            return None

    def analyze_dockerfile_structure(
        self, dockerfile_path: Path, repo_root: Path
    ) -> dict:
        """
        Analyze Dockerfile structure and extract comprehensive information.

        Args:
            dockerfile_path: Path to Dockerfile
            repo_root: Repository root

        Returns:
            Dictionary with analysis results
        """
        build_context = dockerfile_path.parent

        source_paths = self.parse_dockerfile(dockerfile_path, build_context, repo_root)

        return {
            "dockerfile_path": dockerfile_path.relative_to(repo_root),
            "build_context": build_context.relative_to(repo_root),
            "source_paths": source_paths,
            "source_path_count": len(source_paths),
            "implicit_territory": [build_context.relative_to(repo_root)],
            "explicit_territory": source_paths,
        }

    def batch_parse_dockerfiles(self, dockerfiles: List[Path], repo_root: Path) -> dict:
        """
        Parse multiple Dockerfiles in batch.

        Args:
            dockerfiles: List of Dockerfile paths
            repo_root: Repository root

        Returns:
            Dictionary mapping Dockerfile paths to their analysis
        """
        results = {}

        for dockerfile_path in dockerfiles:
            analysis = self.analyze_dockerfile_structure(dockerfile_path, repo_root)
            results[dockerfile_path.relative_to(repo_root)] = analysis

        return results
