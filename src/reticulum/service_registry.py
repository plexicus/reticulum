"""
Service Registry for Unified Pareto Strategy

Manages service tokens and metadata for the reverse ownership index.
Each service is identified by a unique token derived from its Dockerfile location.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass


@dataclass
class ServiceInfo:
    """Metadata for a service identified by a unique token."""
    token: str
    dockerfile_path: Path
    parent_directory: Path
    chart_name: Optional[str] = None

    def __hash__(self):
        return hash(self.token)


class ServiceRegistry:
    """
    Registry for managing service tokens and their metadata.

    Implements Phase 1 of the Unified Pareto Strategy:
    - Service identification via Dockerfile discovery
    - Unique token generation using parent folder names
    - Service metadata management
    """

    def __init__(self):
        self.services: Dict[str, ServiceInfo] = {}
        self.dockerfile_to_service: Dict[Path, str] = {}

    def register_service_from_dockerfile(self, dockerfile_path: Path, repo_root: Path) -> str:
        """
        Register a service from a Dockerfile path.

        Args:
            dockerfile_path: Path to the Dockerfile
            repo_root: Root of the repository

        Returns:
            Service token (unique identifier)
        """
        # Generate service token from parent folder name
        token = self._generate_service_token(dockerfile_path, repo_root)

        # Get parent directory relative to repo root
        parent_dir = dockerfile_path.parent.relative_to(repo_root)

        # Create service info
        service_info = ServiceInfo(
            token=token,
            dockerfile_path=dockerfile_path.relative_to(repo_root),
            parent_directory=parent_dir
        )

        # Register service
        self.services[token] = service_info
        self.dockerfile_to_service[dockerfile_path.relative_to(repo_root)] = token

        return token

    def _generate_service_token(self, dockerfile_path: Path, repo_root: Path) -> str:
        """
        Generate a unique service token from Dockerfile path.

        Strategy: Use the parent folder name as the token.
        Examples:
          - apps/payment/Dockerfile → "payment"
          - apps/orders/build/Dockerfile.prod → "orders"
        """
        # Get relative path from repo root
        relative_path = dockerfile_path.parent.relative_to(repo_root)

        # Extract service name from Dockerfile name
        dockerfile_name = dockerfile_path.name
        if dockerfile_name.lower().startswith('dockerfile'):
            # Handle Dockerfile.backend → backend
            service_name = dockerfile_name.replace('dockerfile', '').strip('.-_')
            if not service_name:
                service_name = None
        else:
            # Handle frontend.Dockerfile → frontend
            service_name = dockerfile_name.replace('.dockerfile', '').replace('Dockerfile.', '').strip('.-_')

        # Clean up service name - remove Dockerfile prefix/suffix
        if service_name:
            service_name = service_name.replace('Dockerfile.', '').replace('.Dockerfile', '').strip('.-_')

        # Use service name as token if available
        if service_name:
            token = service_name
        else:
            # Fallback to parent directory name
            token = relative_path.name

        # Ensure uniqueness
        if token in self.services:
            # If there's a collision, add parent directory prefix
            token = f"{relative_path.name}-{token}"

            # Final uniqueness check - if still not unique, use full path
            if token in self.services:
                token = str(dockerfile_path.relative_to(repo_root)).replace('/', '-').replace('.', '-')

        return token

    def get_service_by_token(self, token: str) -> Optional[ServiceInfo]:
        """Get service info by token."""
        return self.services.get(token)

    def get_service_by_dockerfile(self, dockerfile_path: Path) -> Optional[ServiceInfo]:
        """Get service info by Dockerfile path."""
        token = self.dockerfile_to_service.get(dockerfile_path)
        return self.get_service_by_token(token) if token else None

    def get_all_services(self) -> List[ServiceInfo]:
        """Get all registered services."""
        return list(self.services.values())

    def get_service_tokens(self) -> List[str]:
        """Get all service tokens."""
        return list(self.services.keys())

    def set_chart_name(self, token: str, chart_name: str) -> None:
        """Set the Helm chart name for a service."""
        if token in self.services:
            self.services[token].chart_name = chart_name

    def get_services_by_chart(self, chart_name: str) -> List[ServiceInfo]:
        """Get all services associated with a Helm chart."""
        return [
            service for service in self.services.values()
            if service.chart_name == chart_name
        ]

    def clear(self) -> None:
        """Clear all registered services."""
        self.services.clear()
        self.dockerfile_to_service.clear()