"""
Helm Chart Finder for Unified Pareto Strategy

Discovers Helm charts associated with services using convention-based
and heuristic search strategies.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml


class HelmChartFinder:
    """
    Finds Helm charts associated with services.

    Implements Phase 3 of the Unified Pareto Strategy:
    - Convention-based matching: charts/<Service_Token>/
    - Heuristic search: grep for <Service_Token> in charts/*/values.yaml
    - Fuzzy matching for service names
    """

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.charts_dir = repo_root / "charts"

    def find_chart_for_service(self, service_token: str) -> Optional[str]:
        """
        Find Helm chart for a service token.

        Args:
            service_token: Service token

        Returns:
            Chart name if found, None otherwise
        """
        # Strategy 1: Convention-based matching
        chart_name = self._convention_match(service_token)
        if chart_name:
            return chart_name

        # Strategy 2: Heuristic search in values.yaml files
        chart_name = self._heuristic_search(service_token)
        if chart_name:
            return chart_name

        return None

    def _convention_match(self, service_token: str) -> Optional[str]:
        """
        Convention-based matching: charts/<Service_Token>/

        Args:
            service_token: Service token

        Returns:
            Chart name if convention match found
        """
        chart_path = self.charts_dir / service_token

        # Check if chart directory exists
        if chart_path.exists() and chart_path.is_dir():
            # Verify it has Chart.yaml
            chart_yaml = chart_path / "Chart.yaml"
            if chart_yaml.exists():
                return service_token

        return None

    def _heuristic_search(self, service_token: str) -> Optional[str]:
        """
        Heuristic search for service token in values.yaml files.

        Args:
            service_token: Service token

        Returns:
            Chart name if heuristic match found
        """
        if not self.charts_dir.exists():
            return None

        # Try different variations of the service token
        search_terms = [
            service_token,
            service_token.replace('-', '_'),
            service_token.replace('_', '-'),
            service_token.lower(),
            service_token.upper(),
        ]

        # Search in all chart directories
        for chart_dir in self.charts_dir.iterdir():
            if not chart_dir.is_dir():
                continue

            # Check values.yaml
            values_path = chart_dir / "values.yaml"
            if values_path.exists():
                if self._contains_search_terms(values_path, search_terms):
                    return chart_dir.name

            # Check Chart.yaml
            chart_yaml_path = chart_dir / "Chart.yaml"
            if chart_yaml_path.exists():
                if self._contains_search_terms(chart_yaml_path, search_terms):
                    return chart_dir.name

        return None

    def _contains_search_terms(self, file_path: Path, search_terms: List[str]) -> bool:
        """
        Check if file contains any of the search terms.

        Args:
            file_path: Path to YAML file
            search_terms: List of terms to search for

        Returns:
            True if any term is found
        """
        try:
            content = file_path.read_text(encoding='utf-8')

            # Simple string search first (faster)
            for term in search_terms:
                if term in content:
                    return True

            # Parse YAML for more accurate matching
            try:
                data = yaml.safe_load(content)
                if self._search_yaml_structure(data, search_terms):
                    return True
            except yaml.YAMLError:
                pass

        except Exception:
            pass

        return False

    def _search_yaml_structure(self, data, search_terms: List[str]) -> bool:
        """
        Recursively search YAML structure for search terms.

        Args:
            data: YAML data structure
            search_terms: List of terms to search for

        Returns:
            True if any term is found
        """
        if isinstance(data, dict):
            for key, value in data.items():
                # Check key
                if any(term in str(key) for term in search_terms):
                    return True
                # Check value
                if self._search_yaml_structure(value, search_terms):
                    return True
        elif isinstance(data, list):
            for item in data:
                if self._search_yaml_structure(item, search_terms):
                    return True
        elif isinstance(data, str):
            if any(term in data for term in search_terms):
                return True

        return False

    def find_all_charts(self) -> List[str]:
        """
        Find all Helm charts in the repository.

        Returns:
            List of chart names
        """
        if not self.charts_dir.exists():
            return []

        charts = []
        for chart_dir in self.charts_dir.iterdir():
            if chart_dir.is_dir():
                chart_yaml = chart_dir / "Chart.yaml"
                if chart_yaml.exists():
                    charts.append(chart_dir.name)

        return charts

    def get_chart_info(self, chart_name: str) -> Optional[dict]:
        """
        Get information about a Helm chart.

        Args:
            chart_name: Chart name

        Returns:
            Dictionary with chart information, or None if not found
        """
        chart_path = self.charts_dir / chart_name
        chart_yaml_path = chart_path / "Chart.yaml"
        values_path = chart_path / "values.yaml"

        if not chart_yaml_path.exists():
            return None

        info = {
            'name': chart_name,
            'path': chart_path.relative_to(self.repo_root),
            'has_values': values_path.exists()
        }

        # Parse Chart.yaml
        try:
            chart_data = yaml.safe_load(chart_yaml_path.read_text(encoding='utf-8'))
            info.update({
                'api_version': chart_data.get('apiVersion'),
                'description': chart_data.get('description'),
                'version': chart_data.get('version'),
                'app_version': chart_data.get('appVersion')
            })
        except Exception:
            pass

        return info

    def batch_find_charts(self, service_tokens: List[str]) -> Dict[str, Optional[str]]:
        """
        Find charts for multiple services in batch.

        Args:
            service_tokens: List of service tokens

        Returns:
            Dictionary mapping service tokens to chart names
        """
        results = {}

        for token in service_tokens:
            chart_name = self.find_chart_for_service(token)
            results[token] = chart_name

        return results