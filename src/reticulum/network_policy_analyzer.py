"""
NetworkPolicy Analyzer

Analyzes Kubernetes NetworkPolicy resources to detect internet egress capabilities
and assess security exposure based on network traffic patterns.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any


class NetworkPolicyAnalyzer:
    """Analyzes Kubernetes NetworkPolicy resources for security assessment."""

    def __init__(self):
        self.internet_cidrs = ["0.0.0.0/0", "::/0"]

    def analyze_network_policies(self, repo_path: str) -> Dict[str, Any]:
        """
        Analyze NetworkPolicy resources in the repository.

        Args:
            repo_path: Path to repository containing Kubernetes manifests

        Returns:
            Dictionary with network policy analysis results
        """
        repo_path_obj = Path(repo_path)
        network_policies = self._find_network_policies(repo_path_obj)

        analysis_results = {
            "total_policies": len(network_policies),
            "policies_with_internet_egress": 0,
            "policies_analyzed": [],
            "egress_risk_summary": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
        }

        for policy_path in network_policies:
            policy_analysis = self._analyze_single_policy(policy_path)
            analysis_results["policies_analyzed"].append(policy_analysis)

            if policy_analysis["has_internet_egress"]:
                analysis_results["policies_with_internet_egress"] += 1

            # Update egress risk summary for all policies
            analysis_results["egress_risk_summary"][
                policy_analysis["egress_risk_level"]
            ] += 1

        return analysis_results

    def _find_network_policies(self, repo_path: Path) -> List[Path]:
        """
        Find all NetworkPolicy YAML files in the repository.

        Args:
            repo_path: Path to repository

        Returns:
            List of paths to NetworkPolicy files
        """
        network_policies = []
        seen_files = set()

        # Look for NetworkPolicy files in common locations
        search_patterns = [
            "**/*.yaml",
            "**/*.yml",
            "charts/**/templates/*.yaml",
            "charts/**/templates/*.yml",
            "manifests/**/*.yaml",
            "manifests/**/*.yml",
        ]

        for pattern in search_patterns:
            for file_path in repo_path.glob(pattern):
                if file_path not in seen_files and self._is_network_policy_file(
                    file_path
                ):
                    network_policies.append(file_path)
                    seen_files.add(file_path)

        return network_policies

    def _is_network_policy_file(self, file_path: Path) -> bool:
        """
        Check if a file contains a NetworkPolicy resource.

        Args:
            file_path: Path to YAML file

        Returns:
            True if file contains NetworkPolicy, False otherwise
        """
        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Handle multi-document YAML files
            documents = list(yaml.safe_load_all(content))

            for doc in documents:
                if doc and isinstance(doc, dict):
                    if doc.get("kind") == "NetworkPolicy":
                        return True

        except (yaml.YAMLError, UnicodeDecodeError, OSError):
            # Skip files that can't be parsed
            pass

        return False

    def _analyze_single_policy(self, policy_path: Path) -> Dict[str, Any]:
        """
        Analyze a single NetworkPolicy file.

        Args:
            policy_path: Path to NetworkPolicy YAML file

        Returns:
            Analysis results for this policy
        """
        analysis = {
            "policy_file": str(policy_path),
            "policy_name": "",
            "namespace": "default",
            "has_egress": False,
            "has_internet_egress": False,
            "egress_rules": [],
            "egress_risk_level": "LOW",
            "internet_cidrs_found": [],
        }

        try:
            with open(policy_path, "r") as f:
                content = f.read()

            documents = list(yaml.safe_load_all(content))

            for doc in documents:
                if doc and isinstance(doc, dict) and doc.get("kind") == "NetworkPolicy":
                    metadata = doc.get("metadata", {})
                    spec = doc.get("spec", {})

                    analysis["policy_name"] = metadata.get("name", "unknown")
                    analysis["namespace"] = metadata.get("namespace", "default")

                    # Analyze egress rules
                    egress_rules = spec.get("egress", [])
                    if egress_rules:
                        analysis["has_egress"] = True
                        analysis["egress_rules"] = egress_rules

                        # Check for internet egress
                        internet_egress_found = self._check_internet_egress(
                            egress_rules
                        )
                        analysis["has_internet_egress"] = internet_egress_found["found"]
                        analysis["internet_cidrs_found"] = internet_egress_found[
                            "cidrs"
                        ]

                        # Determine egress risk level
                        analysis["egress_risk_level"] = (
                            self._determine_egress_risk_level(
                                internet_egress_found["found"], len(egress_rules)
                            )
                        )

                    break  # Only analyze first NetworkPolicy in file

        except (yaml.YAMLError, UnicodeDecodeError, OSError) as e:
            analysis["error"] = str(e)

        return analysis

    def _check_internet_egress(self, egress_rules: List[Dict]) -> Dict[str, Any]:
        """
        Check if egress rules allow internet access.

        Args:
            egress_rules: List of egress rules from NetworkPolicy

        Returns:
            Dictionary with internet egress analysis
        """
        internet_cidrs_found = []

        for rule in egress_rules:
            # Check for CIDR blocks in to section
            to_section = rule.get("to", [])
            for to_item in to_section:
                ip_block = to_item.get("ipBlock", {})
                cidr = ip_block.get("cidr", "")

                if cidr in self.internet_cidrs:
                    internet_cidrs_found.append(cidr)

                # Check for except blocks that might restrict internet access
                except_cidrs = ip_block.get("except", [])
                if cidr in self.internet_cidrs and except_cidrs:
                    # If internet CIDR is allowed but with exceptions, still consider it internet access
                    internet_cidrs_found.append(cidr)

        return {"found": len(internet_cidrs_found) > 0, "cidrs": internet_cidrs_found}

    def _determine_egress_risk_level(
        self, has_internet_egress: bool, egress_rule_count: int
    ) -> str:
        """
        Determine the egress risk level based on internet access and rule complexity.

        Args:
            has_internet_egress: Whether internet egress is allowed
            egress_rule_count: Number of egress rules

        Returns:
            Risk level: HIGH, MEDIUM, or LOW
        """
        if has_internet_egress:
            return "HIGH"
        elif (
            egress_rule_count > 3
        ):  # Complex egress rules indicate higher attack surface
            return "MEDIUM"
        else:
            return "LOW"

    def get_egress_risk_multiplier(self, egress_risk_level: str) -> float:
        """
        Get the risk multiplier for egress analysis.

        Args:
            egress_risk_level: Risk level (HIGH, MEDIUM, LOW)

        Returns:
            Multiplier value for risk scoring
        """
        multipliers = {"HIGH": 1.5, "MEDIUM": 1.2, "LOW": 1.0}
        return multipliers.get(egress_risk_level, 1.0)

    def generate_egress_summary(
        self, analysis_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a summary of egress analysis results.

        Args:
            analysis_results: Results from analyze_network_policies

        Returns:
            Summary of egress analysis
        """
        summary = {
            "total_network_policies": analysis_results["total_policies"],
            "policies_with_egress": sum(
                1
                for p in analysis_results["policies_analyzed"]
                if p.get("has_egress", False)
            ),
            "policies_with_internet_egress": analysis_results[
                "policies_with_internet_egress"
            ],
            "egress_risk_breakdown": analysis_results["egress_risk_summary"],
            "recommendations": [],
        }

        # Generate recommendations based on findings
        if summary["policies_with_internet_egress"] > 0:
            summary["recommendations"].append(
                f"Found {summary['policies_with_internet_egress']} NetworkPolicies allowing internet egress. "
                "Consider restricting egress to specific CIDR blocks."
            )

        if summary["total_network_policies"] == 0:
            summary["recommendations"].append(
                "No NetworkPolicy resources found. Consider implementing network policies "
                "to restrict pod-to-pod and external communication."
            )

        return summary
