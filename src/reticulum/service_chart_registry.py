"""
Service Chart Registry for Unified Pareto Strategy

Manages definitive mappings between services and Helm charts,
handling edge cases and naming variations.
"""

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass


@dataclass
class ServiceChartMapping:
    """Definitive mapping between service and chart."""
    service_token: str
    chart_name: str
    confidence: float  # 0.0 to 1.0
    mapping_type: str  # 'convention', 'heuristic', 'manual'
    source: str  # How this mapping was determined


class ServiceChartRegistry:
    """
    Registry for definitive service-to-chart mappings.

    Maintains the authoritative mapping between service tokens and Helm charts,
    handling edge cases and providing resolution services.
    """

    def __init__(self):
        # Primary mappings: service_token -> ServiceChartMapping
        self.service_to_chart: Dict[str, ServiceChartMapping] = {}

        # Reverse mappings: chart_name -> set of service_tokens
        self.chart_to_services: Dict[str, Set[str]] = defaultdict(set)

        # Alternative mappings for edge cases
        self.alternative_mappings: Dict[str, List[ServiceChartMapping]] = defaultdict(list)

    def register_mapping(
        self,
        service_token: str,
        chart_name: str,
        confidence: float = 1.0,
        mapping_type: str = "convention",
        source: str = "auto"
    ) -> None:
        """
        Register a service-to-chart mapping.

        Args:
            service_token: Service token
            chart_name: Helm chart name
            confidence: Confidence level (0.0 to 1.0)
            mapping_type: Type of mapping ('convention', 'heuristic', 'manual')
            source: Source of the mapping
        """
        mapping = ServiceChartMapping(
            service_token=service_token,
            chart_name=chart_name,
            confidence=confidence,
            mapping_type=mapping_type,
            source=source
        )

        # Check if we already have a mapping for this service
        existing = self.service_to_chart.get(service_token)

        if existing:
            # Keep the highest confidence mapping
            if confidence > existing.confidence:
                self.service_to_chart[service_token] = mapping
                # Update reverse mapping
                self.chart_to_services[existing.chart_name].discard(service_token)
                self.chart_to_services[chart_name].add(service_token)
            else:
                # Store as alternative mapping
                self.alternative_mappings[service_token].append(mapping)
        else:
            # New mapping
            self.service_to_chart[service_token] = mapping
            self.chart_to_services[chart_name].add(service_token)

    def get_chart_for_service(self, service_token: str) -> Optional[str]:
        """
        Get the primary chart name for a service.

        Args:
            service_token: Service token

        Returns:
            Chart name, or None if not found
        """
        mapping = self.service_to_chart.get(service_token)
        return mapping.chart_name if mapping else None

    def get_services_for_chart(self, chart_name: str) -> List[str]:
        """
        Get all services mapped to a chart.

        Args:
            chart_name: Chart name

        Returns:
            List of service tokens
        """
        return list(self.chart_to_services.get(chart_name, set()))

    def get_mapping_details(self, service_token: str) -> Optional[ServiceChartMapping]:
        """
        Get detailed mapping information for a service.

        Args:
            service_token: Service token

        Returns:
            ServiceChartMapping object, or None if not found
        """
        return self.service_to_chart.get(service_token)

    def get_alternative_mappings(self, service_token: str) -> List[ServiceChartMapping]:
        """
        Get alternative mappings for a service.

        Args:
            service_token: Service token

        Returns:
            List of alternative ServiceChartMapping objects
        """
        return self.alternative_mappings.get(service_token, [])

    def resolve_chart_for_service(
        self,
        service_token: str,
        min_confidence: float = 0.5
    ) -> Optional[str]:
        """
        Resolve chart for service with confidence threshold.

        Args:
            service_token: Service token
            min_confidence: Minimum confidence threshold

        Returns:
            Chart name if confidence >= threshold, None otherwise
        """
        mapping = self.service_to_chart.get(service_token)
        if mapping and mapping.confidence >= min_confidence:
            return mapping.chart_name

        # Check alternatives
        alternatives = self.alternative_mappings.get(service_token, [])
        for alt in alternatives:
            if alt.confidence >= min_confidence:
                return alt.chart_name

        return None

    def get_all_mappings(self) -> List[ServiceChartMapping]:
        """Get all registered mappings."""
        return list(self.service_to_chart.values())

    def get_registry_statistics(self) -> Dict[str, int]:
        """
        Get statistics for the registry.

        Returns:
            Dictionary with registry statistics
        """
        total_services = len(self.service_to_chart)
        total_charts = len(self.chart_to_services)

        # Count mapping types
        mapping_types = defaultdict(int)
        for mapping in self.service_to_chart.values():
            mapping_types[mapping.mapping_type] += 1

        # Count services per chart
        services_per_chart = [
            len(services) for services in self.chart_to_services.values()
        ]
        avg_services_per_chart = (
            sum(services_per_chart) / len(services_per_chart)
            if services_per_chart else 0
        )

        return {
            'total_services': total_services,
            'total_charts': total_charts,
            'mapping_types': dict(mapping_types),
            'avg_services_per_chart': avg_services_per_chart,
            'max_services_per_chart': max(services_per_chart) if services_per_chart else 0,
            'alternative_mappings': sum(len(alts) for alts in self.alternative_mappings.values())
        }

    def find_orphaned_services(self) -> List[str]:
        """
        Find services without chart mappings.

        Returns:
            List of service tokens without chart mappings
        """
        return [
            token for token in self.service_to_chart.keys()
            if not self.service_to_chart[token].chart_name
        ]

    def find_services_with_low_confidence(self, threshold: float = 0.7) -> List[str]:
        """
        Find services with low-confidence mappings.

        Args:
            threshold: Confidence threshold

        Returns:
            List of service tokens with confidence below threshold
        """
        return [
            token for token, mapping in self.service_to_chart.items()
            if mapping.confidence < threshold
        ]

    def clear(self) -> None:
        """Clear all mappings."""
        self.service_to_chart.clear()
        self.chart_to_services.clear()
        self.alternative_mappings.clear()

    def __str__(self) -> str:
        """String representation of the registry."""
        stats = self.get_registry_statistics()
        return (
            f"ServiceChartRegistry("
            f"services={stats['total_services']}, "
            f"charts={stats['total_charts']}, "
            f"types={stats['mapping_types']})"
        )