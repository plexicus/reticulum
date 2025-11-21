"""
Enhanced Prioritizer

Modifies service priorities based on security findings and exposure levels.
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from .network_policy_analyzer import NetworkPolicyAnalyzer


@dataclass
class FindingScore:
    """Individual finding score with preserved context."""
    finding_id: str
    tool: str  # "trivy" or "semgrep"
    severity: str
    base_score: float
    context_modifier: float
    final_score: float
    finding_data: Dict[str, Any]

    def __post_init__(self):
        """Calculate final score after initialization."""
        self.final_score = self.base_score * self.context_modifier


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

            # Calculate individual finding scores
            finding_scores = self._calculate_finding_scores(
                service_name, trivy_mapping, semgrep_mapping
            )

            # Aggregate finding scores into service-level metrics
            security_metrics = self._aggregate_finding_scores(finding_scores)
            security_score = security_metrics["aggregated_score"]

            # Calculate egress risk score
            egress_score = self._calculate_egress_risk_score(service)

            # Get findings summary to check for critical findings
            findings_summary = self._get_findings_summary(
                service_name, trivy_mapping, semgrep_mapping
            )
            has_critical_findings = findings_summary.get("critical_findings", 0) > 0

            # Calculate enhanced priority and rank
            enhanced_risk, combined_score, rank = self._calculate_enhanced_priority(
                original_risk, security_score, egress_score, has_critical_findings
            )

            # Create enhanced service entry
            enhanced_service = service.copy()
            enhanced_service.update(
                {
                    "original_risk_level": original_risk,
                    "enhanced_risk_level": enhanced_risk,
                    "combined_score": combined_score,
                    "reticulum_score": rank,
                    "security_risk_score": security_score,
                    "egress_risk_score": egress_score,
                    "security_findings_summary": findings_summary,
                    "egress_analysis": service.get("egress_analysis", {}),
                    # Per-finding scoring data
                    "finding_scores": [
                        {
                            "finding_id": fs.finding_id,
                            "tool": fs.tool,
                            "severity": fs.severity,
                            "base_score": fs.base_score,
                            "context_modifier": fs.context_modifier,
                            "final_score": fs.final_score,
                            "finding_data": fs.finding_data
                        }
                        for fs in finding_scores
                    ],
                    "security_metrics": security_metrics,
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

    def _calculate_finding_scores(
        self,
        service_name: str,
        trivy_mapping: Dict[str, Any],
        semgrep_mapping: Dict[str, Any],
    ) -> List[FindingScore]:
        """Calculate individual scores for all findings in a service."""
        finding_scores = []

        # Calculate scores for Trivy findings
        if service_name in trivy_mapping["services"]:
            for finding in trivy_mapping["services"][service_name]["trivy_findings"]:
                finding_score = self._calculate_finding_score(finding, "trivy")
                finding_scores.append(finding_score)

        # Calculate scores for Semgrep findings
        if service_name in semgrep_mapping["services"]:
            for finding in semgrep_mapping["services"][service_name][
                "semgrep_findings"
            ]:
                finding_score = self._calculate_finding_score(finding, "semgrep")
                finding_scores.append(finding_score)

        return finding_scores

    def _calculate_finding_score(self, finding: Dict[str, Any], tool: str) -> FindingScore:
        """Calculate individual score for a single finding."""
        # Extract finding identifier
        finding_id = finding.get("ruleId", f"{tool}-finding-{id(finding)}")

        # Base score from severity
        severity = finding.get("level", "warning").lower()
        base_score = self.severity_weights.get(severity, 1.0)

        # Add context-based modifiers
        context_modifier = self._calculate_context_modifier(finding, tool)

        return FindingScore(
            finding_id=finding_id,
            tool=tool,
            severity=severity,
            base_score=base_score,
            context_modifier=context_modifier,
            final_score=base_score * context_modifier,
            finding_data=finding
        )

    def _calculate_context_modifier(self, finding: Dict[str, Any], tool: str) -> float:
        """Calculate context modifier for a finding based on additional factors."""
        modifier = 1.0

        # Tool-specific modifiers
        if tool == "trivy":
            # Trivy findings: consider package criticality
            properties = finding.get("properties", {})
            package_name = properties.get("package_name", "")
            if any(critical_pkg in package_name.lower() for critical_pkg in ["openssl", "kernel", "libc"]):
                modifier *= 1.5  # Critical system packages
        elif tool == "semgrep":
            # Semgrep findings: consider rule confidence and impact
            properties = finding.get("properties", {})
            confidence = properties.get("confidence", "medium")
            if confidence == "high":
                modifier *= 1.3
            elif confidence == "low":
                modifier *= 0.7

        # Location-based modifiers
        locations = finding.get("locations", [])
        if locations:
            location = locations[0].get("physicalLocation", {}).get("artifactLocation", {})
            file_path = location.get("uri", "")
            if any(critical_path in file_path for critical_path in ["/etc/", "/bin/", "/sbin/", "/usr/bin/"]):
                modifier *= 1.4  # Critical system locations

        return max(0.5, min(2.0, modifier))  # Bound between 0.5 and 2.0

    def _aggregate_finding_scores(self, finding_scores: List[FindingScore]) -> Dict[str, Any]:
        """
        Aggregate individual finding scores into service-level metrics.

        Uses weighted aggregation that preserves critical findings impact.
        """
        if not finding_scores:
            return {
                "aggregated_score": 0.0,
                "max_finding_score": 0.0,
                "critical_findings_count": 0,
                "top_findings": [],
                "total_findings": 0
            }

        # Calculate key metrics
        total_findings = len(finding_scores)
        critical_findings = [fs for fs in finding_scores if fs.severity in ["critical", "error"]]
        critical_findings_count = len(critical_findings)
        max_finding_score = max(fs.final_score for fs in finding_scores) if finding_scores else 0.0

        # Weighted aggregation formula: max severity + weighted average of others
        if critical_findings:
            # If critical findings exist, they dominate the score
            critical_max = max(fs.final_score for fs in critical_findings)
            other_findings = [fs for fs in finding_scores if fs.severity not in ["critical", "error"]]

            if other_findings:
                # Weighted average of non-critical findings (lower weight)
                other_avg = sum(fs.final_score for fs in other_findings) / len(other_findings)
                aggregated_score = critical_max + (other_avg * 0.3)  # Critical dominates
            else:
                aggregated_score = critical_max
        else:
            # No critical findings - use weighted average
            weights = {
                "high": 1.0,
                "warning": 0.8,
                "medium": 0.6,
                "low": 0.4,
                "info": 0.2
            }
            weighted_sum = sum(fs.final_score * weights.get(fs.severity, 0.5) for fs in finding_scores)
            weight_sum = sum(weights.get(fs.severity, 0.5) for fs in finding_scores)
            aggregated_score = weighted_sum / weight_sum if weight_sum > 0 else 0.0

        # Get top 5 findings by score
        top_findings = sorted(finding_scores, key=lambda fs: fs.final_score, reverse=True)[:5]

        return {
            "aggregated_score": aggregated_score,
            "max_finding_score": max_finding_score,
            "critical_findings_count": critical_findings_count,
            "top_findings": [
                {
                    "finding_id": fs.finding_id,
                    "tool": fs.tool,
                    "severity": fs.severity,
                    "final_score": fs.final_score,
                    "description": fs.finding_data.get("message", {}).get("text", "No description")
                }
                for fs in top_findings
            ],
            "total_findings": total_findings
        }

    def _calculate_reticulum_score(
        self, combined_score: float, has_critical_findings: bool
    ) -> int:
        """
        Calculate reticulum score (1-100) based on combined score and critical findings.

        Args:
            combined_score: The calculated combined score from enhanced prioritizer
            has_critical_findings: Whether the service has critical/error level findings

        Returns:
            Integer reticulum_score from 1-100 (higher = more critical)
        """
        # Base reticulum_score from combined score (scaled 0-80)
        base_reticulum_score = min(80, max(0, int((combined_score / 10.0) * 80)))

        # Add bonus for critical findings (up to +20)
        critical_bonus = 20 if has_critical_findings else 0

        return min(100, base_reticulum_score + critical_bonus)

    def _calculate_enhanced_priority(
        self, original_risk: str, security_score: float, egress_score: float, has_critical_findings: bool
    ) -> tuple[str, float, int]:
        """
        Calculate enhanced priority based on original risk, security score, and egress score.

        Returns:
            Tuple of (enhanced_priority, combined_score, reticulum_score)
        """
        exposure_weight = self.exposure_weights.get(original_risk, 1.0)

        # Combine exposure, security, and egress factors
        combined_score = exposure_weight * (1.0 + security_score * 0.1) * egress_score

        # Determine enhanced priority
        if combined_score >= 2.5:
            enhanced_priority = "HIGH"
        elif combined_score >= 1.2:
            enhanced_priority = "MEDIUM"
        else:
            enhanced_priority = "LOW"

        # Calculate reticulum_score
        reticulum_score = self._calculate_reticulum_score(combined_score, has_critical_findings)

        return enhanced_priority, combined_score, reticulum_score

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
