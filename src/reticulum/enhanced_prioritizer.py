"""
Enhanced Prioritizer

Modifies service priorities based on security findings and exposure levels.
"""

from typing import Dict, Any
from .network_policy_analyzer import NetworkPolicyAnalyzer


class EnhancedPrioritizer:
    """Enhances service prioritization based on security findings."""

    def __init__(self):
        self.exposure_weights = {
            "HIGH": 3.0,  # High exposure - increase priority significantly
            "MEDIUM": 1.0,  # Medium exposure - keep priority
            "LOW": 0.3,  # Low exposure - decrease priority
        }

        self.severity_weights = {
            "critical": 4.0,
            "error": 3.0,
            "high": 2.0,
            "warning": 1.5,
            "medium": 1.0,
            "low": 0.5,
            "info": 0.3,
        }

        # Egress risk multipliers
        self.egress_risk_multipliers = {
            "HIGH": 1.5,  # Internet egress detected
            "MEDIUM": 1.2,  # Complex egress rules
            "LOW": 1.0,  # Minimal egress risk
        }

        self.network_policy_analyzer = NetworkPolicyAnalyzer()

    def enhance_prioritization(
        self,
        prioritization_report: Dict[str, Any],
        trivy_mapping: Dict[str, Any],
        semgrep_mapping: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enhance prioritization based on security findings.

        Args:
            prioritization_report: Original reticulum prioritization
            trivy_mapping: Trivy findings mapped to services
            semgrep_mapping: Semgrep findings mapped to services

        Returns:
            Enhanced prioritization report
        """
        print("🎯 Enhancing prioritization based on security findings...")

        enhanced_services = []
        original_counts = self._count_original_priorities(prioritization_report)
        enhanced_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

        for service in prioritization_report.get("prioritized_services", []):
            service_name = service["service_name"]
            original_risk = service["risk_level"]

            # Calculate security risk score
            security_score = self._calculate_security_score(
                service_name, trivy_mapping, semgrep_mapping
            )

            # Calculate egress risk score
            egress_score = self._calculate_egress_risk_score(service)

            # Calculate enhanced priority
            enhanced_risk = self._calculate_enhanced_priority(
                original_risk, security_score, egress_score
            )

            # Create enhanced service entry
            enhanced_service = service.copy()
            enhanced_service.update(
                {
                    "original_risk_level": original_risk,
                    "enhanced_risk_level": enhanced_risk,
                    "security_risk_score": security_score,
                    "egress_risk_score": egress_score,
                    "security_findings_summary": self._get_findings_summary(
                        service_name, trivy_mapping, semgrep_mapping
                    ),
                    "egress_analysis": service.get("egress_analysis", {}),
                }
            )

            enhanced_services.append(enhanced_service)
            enhanced_counts[enhanced_risk] += 1

        # Sort by enhanced priority
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        enhanced_services.sort(
            key=lambda s: priority_order.get(s["enhanced_risk_level"], 3)
        )

        # Create enhanced report
        enhanced_report = prioritization_report.copy()
        enhanced_report["prioritized_services"] = enhanced_services
        enhanced_report["enhanced_summary"] = {
            "original_priorities": original_counts,
            "enhanced_priorities": enhanced_counts,
            "security_impact": self._calculate_security_impact(
                original_counts, enhanced_counts
            ),
        }

        # Print comparison
        self._print_priority_comparison(original_counts, enhanced_counts)

        return enhanced_report

    def _calculate_security_score(
        self,
        service_name: str,
        trivy_mapping: Dict[str, Any],
        semgrep_mapping: Dict[str, Any],
    ) -> float:
        """Calculate security risk score for a service."""
        score = 0.0

        # Add Trivy findings score
        if service_name in trivy_mapping["services"]:
            for finding in trivy_mapping["services"][service_name]["trivy_findings"]:
                severity = finding.get("level", "warning").lower()
                score += self.severity_weights.get(severity, 1.0)

        # Add Semgrep findings score
        if service_name in semgrep_mapping["services"]:
            for finding in semgrep_mapping["services"][service_name][
                "semgrep_findings"
            ]:
                severity = finding.get("level", "warning").lower()
                score += self.severity_weights.get(severity, 1.0)

        return score

    def _calculate_enhanced_priority(
        self, original_risk: str, security_score: float, egress_score: float
    ) -> str:
        """Calculate enhanced priority based on original risk, security score, and egress score."""
        exposure_weight = self.exposure_weights.get(original_risk, 1.0)

        # Combine exposure, security, and egress factors
        combined_score = exposure_weight * (1.0 + security_score * 0.1) * egress_score

        # Determine enhanced priority
        if combined_score >= 2.5:
            return "HIGH"
        elif combined_score >= 1.2:
            return "MEDIUM"
        else:
            return "LOW"

    def _get_findings_summary(
        self,
        service_name: str,
        trivy_mapping: Dict[str, Any],
        semgrep_mapping: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Get summary of security findings for a service."""
        summary = {
            "trivy_findings": 0,
            "semgrep_findings": 0,
            "critical_findings": 0,
            "high_findings": 0,
            "medium_findings": 0,
            "low_findings": 0,
        }

        # Count Trivy findings
        if service_name in trivy_mapping["services"]:
            for finding in trivy_mapping["services"][service_name]["trivy_findings"]:
                summary["trivy_findings"] += 1
                severity = finding.get("level", "warning").lower()
                if severity in ["error", "critical"]:
                    summary["critical_findings"] += 1
                elif severity == "high":
                    summary["high_findings"] += 1
                elif severity == "medium":
                    summary["medium_findings"] += 1
                else:
                    summary["low_findings"] += 1

        # Count Semgrep findings
        if service_name in semgrep_mapping["services"]:
            for finding in semgrep_mapping["services"][service_name][
                "semgrep_findings"
            ]:
                summary["semgrep_findings"] += 1
                severity = finding.get("level", "warning").lower()
                if severity == "error":
                    summary["critical_findings"] += 1
                elif severity == "warning":
                    summary["high_findings"] += 1
                elif severity == "info":
                    summary["medium_findings"] += 1
                else:
                    summary["low_findings"] += 1

        return summary

    def _count_original_priorities(self, report: Dict[str, Any]) -> Dict[str, int]:
        """Count original priority levels."""
        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for service in report.get("prioritized_services", []):
            risk_level = service.get("risk_level", "LOW")
            if risk_level in counts:
                counts[risk_level] += 1
        return counts

    def _calculate_security_impact(
        self, original_counts: Dict[str, int], enhanced_counts: Dict[str, int]
    ) -> Dict[str, Any]:
        """Calculate the impact of security findings on prioritization."""
        impact = {
            "services_upgraded": 0,
            "services_downgraded": 0,
            "net_impact": "neutral",
        }

        for level in ["HIGH", "MEDIUM", "LOW"]:
            if enhanced_counts[level] > original_counts[level]:
                impact["services_upgraded"] += (
                    enhanced_counts[level] - original_counts[level]
                )
            elif enhanced_counts[level] < original_counts[level]:
                impact["services_downgraded"] += (
                    original_counts[level] - enhanced_counts[level]
                )

        if impact["services_upgraded"] > impact["services_downgraded"]:
            impact["net_impact"] = "increased_priority"
        elif impact["services_upgraded"] < impact["services_downgraded"]:
            impact["net_impact"] = "decreased_priority"

        return impact

    def _print_priority_comparison(
        self, original_counts: Dict[str, int], enhanced_counts: Dict[str, int]
    ):
        """Print comparison between original and enhanced priorities."""
        print("\n📊 Enhanced Prioritization Results:")
        for level in ["HIGH", "MEDIUM", "LOW"]:
            original = original_counts.get(level, 0)
            enhanced = enhanced_counts.get(level, 0)
            change = enhanced - original

            if change > 0:
                change_str = f"(+{change})"
            elif change < 0:
                change_str = f"({change})"
            else:
                change_str = "(no change)"

            print(f"   - {level}: {enhanced} services {change_str}")

        # Calculate overall impact
        upgraded = sum(
            max(0, enhanced_counts[level] - original_counts[level])
            for level in ["HIGH", "MEDIUM", "LOW"]
        )
        downgraded = sum(
            max(0, original_counts[level] - enhanced_counts[level])
            for level in ["HIGH", "MEDIUM", "LOW"]
        )

        print(f"\n   📈 Services upgraded: {upgraded}")
        print(f"   📉 Services downgraded: {downgraded}")

    def _calculate_egress_risk_score(self, service: Dict[str, Any]) -> float:
        """
        Calculate egress risk score based on network policy analysis.

        Args:
            service: Service information including egress analysis

        Returns:
            Egress risk multiplier
        """
        egress_analysis = service.get("egress_analysis", {})
        egress_risk_level = egress_analysis.get("egress_risk_level", "LOW")

        # Get multiplier based on egress risk level
        return self.egress_risk_multipliers.get(egress_risk_level, 1.0)
