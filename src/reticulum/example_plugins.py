"""
Example plugins for Reticulum Security Scanner.

This module provides example implementations of security tool
and processing plugins to demonstrate the plugin architecture.
"""

import json
from typing import Dict, Any
from .plugin_base import SecurityToolPlugin, ProcessingPlugin


class ExampleSecurityTool(SecurityToolPlugin):
    """Example security tool plugin that demonstrates the interface."""

    def scan(self, repo_path: str, output_file: str) -> Dict[str, Any]:
        """
        Perform example security scan.

        Args:
            repo_path: Path to repository to scan
            output_file: Path to save results

        Returns:
            Dictionary with scan results and metadata
        """
        # Example scan logic - in a real plugin, this would run an actual security tool
        example_results = {
            "runs": [
                {
                    "tool": {
                        "driver": {"name": "Example Security Tool", "version": "1.0.0"}
                    },
                    "results": [
                        {
                            "ruleId": "EXAMPLE-001",
                            "level": "warning",
                            "message": {"text": "Example security finding"},
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {"uri": "example/file.py"}
                                    }
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        # Save results to output file
        with open(output_file, "w") as f:
            json.dump(example_results, f, indent=2)

        return {
            "success": True,
            "sarif_data": example_results,
            "severity_counts": {"error": 0, "warning": 1, "info": 0, "total": 1},
            "output_file": output_file,
        }

    def get_name(self) -> str:
        """Get the name of this security tool."""
        return "example-security-tool"

    def get_version(self) -> str:
        """Get the version of this security tool."""
        return "1.0.0"


class ExampleProcessor(ProcessingPlugin):
    """Example processing plugin that demonstrates result modification."""

    def process(self, scan_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process scan results by adding example metadata.

        Args:
            scan_results: Dictionary containing scan results

        Returns:
            Modified scan results with added metadata
        """
        # Add example metadata to results
        processed_results = scan_results.copy()

        if "enhanced_prioritization" in processed_results:
            processed_results["enhanced_prioritization"]["example_processed"] = True
            processed_results["enhanced_prioritization"][
                "processor_applied"
            ] = self.get_name()

        return processed_results

    def get_name(self) -> str:
        """Get the name of this processing plugin."""
        return "example-processor"

    def get_description(self) -> str:
        """Get description of what this plugin does."""
        return "Adds example metadata to scan results"


class RiskScoreCalculator(ProcessingPlugin):
    """Processing plugin that calculates overall risk scores for services."""

    def process(self, scan_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate risk scores based on exposure levels and security findings.

        Args:
            scan_results: Dictionary containing scan results

        Returns:
            Modified scan results with risk scores
        """
        processed_results = scan_results.copy()

        # Calculate risk scores for services
        if "enhanced_prioritization" in processed_results:
            enhanced_data = processed_results["enhanced_prioritization"]

            if "prioritized_services" in enhanced_data:
                for service in enhanced_data["prioritized_services"]:
                    # Calculate risk score based on exposure and findings
                    risk_score = self._calculate_risk_score(service)
                    service["calculated_risk_score"] = risk_score

        return processed_results

    def _calculate_risk_score(self, service_data: Dict[str, Any]) -> float:
        """Calculate risk score for a service."""
        base_score = 0.0

        # Risk level multiplier
        risk_multipliers = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3}

        # Apply risk level multiplier
        risk_level = service_data.get("risk_level", "LOW")
        base_score += risk_multipliers.get(risk_level, 0.3)

        # Add findings impact
        findings_summary = service_data.get("security_findings_summary", {})
        critical_findings = findings_summary.get("critical_findings", 0)
        high_findings = findings_summary.get("high_findings", 0)
        medium_findings = findings_summary.get("medium_findings", 0)

        base_score += critical_findings * 0.5
        base_score += high_findings * 0.3
        base_score += medium_findings * 0.1

        # Cap at 10.0
        return min(10.0, base_score)

    def get_name(self) -> str:
        """Get the name of this processing plugin."""
        return "risk-score-calculator"

    def get_description(self) -> str:
        """Get description of what this plugin does."""
        return (
            "Calculates overall risk scores for services based on exposure and findings"
        )
