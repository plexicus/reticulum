"""
Reverse Ownership Index for Unified Pareto Strategy

Maintains mappings from source code folders to the services that consume them.
This is the "brain" of the territory claiming system.
"""

from pathlib import Path
from typing import Dict, List, Set, Optional
from collections import defaultdict


class ReverseOwnershipIndex:
    """
    Reverse ownership index mapping folders to service tokens.

    Implements Phase 2 of the Unified Pareto Strategy:
    - Maintains folder_path → [service_tokens] mappings
    - Handles shared ownership (one-to-many relationships)
    - Provides query interface for deployment targeting
    """

    def __init__(self):
        # Core index: folder_path -> set of service tokens
        self.ownership_index: Dict[Path, Set[str]] = defaultdict(set)

        # Reverse mapping for quick lookups
        self.service_to_folders: Dict[str, Set[Path]] = defaultdict(set)

    def claim_implicit_territory(self, service_token: str, folder_path: Path) -> None:
        """
        Claim implicit territory (Dockerfile parent directory).

        Args:
            service_token: Service token
            folder_path: Directory path to claim
        """
        self._add_ownership(folder_path, service_token)

    def claim_explicit_territory(self, service_token: str, source_paths: List[Path]) -> None:
        """
        Claim explicit territory from Dockerfile COPY/ADD commands.

        Args:
            service_token: Service token
            source_paths: List of source paths from Dockerfile
        """
        for source_path in source_paths:
            # Claim the directory containing the source file
            directory_path = source_path if source_path.is_dir() else source_path.parent

            # Claim the full directory hierarchy
            current_path = directory_path
            while current_path != current_path.parent:  # Stop at root
                self._add_ownership(current_path, service_token)
                current_path = current_path.parent

    def _add_ownership(self, folder_path: Path, service_token: str) -> None:
        """
        Add ownership relationship between folder and service.

        Args:
            folder_path: Folder path
            service_token: Service token
        """
        self.ownership_index[folder_path].add(service_token)
        self.service_to_folders[service_token].add(folder_path)

    def get_owners_for_path(self, file_path: Path) -> List[str]:
        """
        Get service tokens that own a given file path.

        Args:
            file_path: File or directory path

        Returns:
            List of service tokens that consume this path
        """
        # Strategy: Look at directory hierarchy
        owners = set()

        # Check the directory containing the file
        directory_path = file_path if file_path.is_dir() else file_path.parent

        # Check exact match first
        if directory_path in self.ownership_index:
            owners.update(self.ownership_index[directory_path])

        # Check parent directories (inheritance)
        current_path = directory_path
        while current_path != current_path.parent:  # Stop at root
            if current_path in self.ownership_index:
                owners.update(self.ownership_index[current_path])
            current_path = current_path.parent

        return list(owners)

    def get_folders_for_service(self, service_token: str) -> List[Path]:
        """
        Get all folders owned by a service.

        Args:
            service_token: Service token

        Returns:
            List of folder paths
        """
        return list(self.service_to_folders.get(service_token, set()))

    def get_shared_folders(self) -> Dict[str, List[str]]:
        """
        Get folders with multiple owners (shared libraries).

        Returns:
            Dictionary of shared folders and their owners
        """
        return {
            str(folder): list(owners)
            for folder, owners in self.ownership_index.items()
            if len(owners) > 1
        }

    def get_service_coverage(self, service_token: str) -> Dict[str, int]:
        """
        Get coverage statistics for a service.

        Args:
            service_token: Service token

        Returns:
            Dictionary with coverage statistics
        """
        folders = self.service_to_folders.get(service_token, set())

        return {
            'total_folders': len(folders),
            'shared_folders': len([f for f in folders if len(self.ownership_index[f]) > 1]),
            'exclusive_folders': len([f for f in folders if len(self.ownership_index[f]) == 1])
        }

    def get_index_statistics(self) -> Dict[str, int]:
        """
        Get overall statistics for the ownership index.

        Returns:
            Dictionary with index statistics
        """
        total_folders = len(self.ownership_index)
        total_services = len(self.service_to_folders)

        shared_folders = len(self.get_shared_folders())
        exclusive_folders = total_folders - shared_folders

        total_ownerships = sum(len(owners) for owners in self.ownership_index.values())

        return {
            'total_folders': total_folders,
            'total_services': total_services,
            'shared_folders': shared_folders,
            'exclusive_folders': exclusive_folders,
            'total_ownerships': total_ownerships,
            'avg_owners_per_folder': total_ownerships / total_folders if total_folders > 0 else 0
        }

    def find_services_by_file_change(self, changed_files: List[Path]) -> Dict[Path, List[str]]:
        """
        Find services affected by file changes.

        Args:
            changed_files: List of changed file paths

        Returns:
            Dictionary mapping changed files to affected services
        """
        affected_services = {}

        for file_path in changed_files:
            owners = self.get_owners_for_path(file_path)
            if owners:
                affected_services[file_path] = owners

        return affected_services

    def clear(self) -> None:
        """Clear the ownership index."""
        self.ownership_index.clear()
        self.service_to_folders.clear()

    def __str__(self) -> str:
        """String representation of the ownership index."""
        stats = self.get_index_statistics()
        return (
            f"ReverseOwnershipIndex("
            f"folders={stats['total_folders']}, "
            f"services={stats['total_services']}, "
            f"shared={stats['shared_folders']}, "
            f"ownerships={stats['total_ownerships']})"
        )