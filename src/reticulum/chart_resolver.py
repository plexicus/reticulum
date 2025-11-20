"""
Chart Resolver for Unified Pareto Strategy

Resolves service tokens to Helm charts for deployment targeting.
"""

from collections import defaultdict
from typing import Dict, List, Optional, Set


class ChartResolver:
    """
    Resolves service tokens to Helm charts.

    Implements Phase 4 of the Unified Pareto Strategy:
    - Resolves service tokens to Helm charts
    - Handles service-to-chart resolution
    - Provides deployment target generation
    """

    def __init__(self, service_chart_registry):
        """
        Initialize ChartResolver.

        Args:
            service_chart_registry: ServiceChartRegistry instance
        """
        self.service_chart_registry = service_chart_registry

    def resolve_service_to_chart(self, service_token: str) -> Optional[str]:
        """
        Resolve a service token to a Helm chart.

        Args:
            service_token: Service token

        Returns:
            Chart name, or None if not found
        """
        return self.service_chart_registry.get_chart_for_service(service_token)

    def resolve_services_to_charts(
        self, service_tokens: List[str]
    ) -> Dict[str, Optional[str]]:
        """
        Resolve multiple service tokens to charts.

        Args:
            service_tokens: List of service tokens

        Returns:
            Dictionary mapping service tokens to chart names
        """
        results = {}

        for token in service_tokens:
            chart_name = self.resolve_service_to_chart(token)
            results[token] = chart_name

        return results

    def resolve_chart_to_services(self, chart_name: str) -> List[str]:
        """
        Resolve a chart name to service tokens.

        Args:
            chart_name: Chart name

        Returns:
            List of service tokens
        """
        return self.service_chart_registry.get_services_for_chart(chart_name)

    def get_unique_charts(self, service_tokens: List[str]) -> Set[str]:
        """
        Get unique charts from a list of service tokens.

        Args:
            service_tokens: List of service tokens

        Returns:
            Set of unique chart names
        """
        charts = set()

        for token in service_tokens:
            chart_name = self.resolve_service_to_chart(token)
            if chart_name:
                charts.add(chart_name)

        return charts

    def get_chart_coverage(self, chart_name: str) -> Dict[str, int]:
        """
        Get coverage statistics for a chart.

        Args:
            chart_name: Chart name

        Returns:
            Dictionary with coverage statistics
        """
        services = self.resolve_chart_to_services(chart_name)

        return {
            "chart_name": chart_name,
            "service_count": len(services),
            "services": services,
        }

    def validate_service_chart_mappings(
        self, service_tokens: List[str]
    ) -> Dict[str, dict]:
        """
        Validate service-to-chart mappings.

        Args:
            service_tokens: List of service tokens

        Returns:
            Dictionary with validation results
        """
        validation_results = {}

        for token in service_tokens:
            mapping = self.service_chart_registry.get_mapping_details(token)

            if mapping:
                validation_results[token] = {
                    "status": "mapped",
                    "chart_name": mapping.chart_name,
                    "confidence": mapping.confidence,
                    "mapping_type": mapping.mapping_type,
                    "source": mapping.source,
                }
            else:
                validation_results[token] = {
                    "status": "unmapped",
                    "chart_name": None,
                    "confidence": 0.0,
                    "mapping_type": None,
                    "source": None,
                }

        return validation_results

    def get_mapping_statistics(self, service_tokens: List[str]) -> Dict[str, int]:
        """
        Get mapping statistics for a set of service tokens.

        Args:
            service_tokens: List of service tokens

        Returns:
            Dictionary with mapping statistics
        """
        total_services = len(service_tokens)
        mapped_services = 0
        high_confidence_mappings = 0
        mapping_types = defaultdict(int)

        for token in service_tokens:
            mapping = self.service_chart_registry.get_mapping_details(token)
            if mapping:
                mapped_services += 1
                if mapping.confidence >= 0.8:
                    high_confidence_mappings += 1
                mapping_types[mapping.mapping_type] += 1

        return {
            "total_services": total_services,
            "mapped_services": mapped_services,
            "unmapped_services": total_services - mapped_services,
            "mapping_rate": (
                mapped_services / total_services if total_services > 0 else 0
            ),
            "high_confidence_mappings": high_confidence_mappings,
            "mapping_types": dict(mapping_types),
        }
