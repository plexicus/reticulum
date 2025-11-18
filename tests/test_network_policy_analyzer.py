"""
Tests for NetworkPolicyAnalyzer module
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.reticulum.network_policy_analyzer import NetworkPolicyAnalyzer


class TestNetworkPolicyAnalyzer:
    """Test cases for NetworkPolicyAnalyzer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = NetworkPolicyAnalyzer()
        self.temp_dir = tempfile.mkdtemp(prefix="reticulum_test_")

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_analyze_empty_repository(self):
        """Test analyzing a repository with no NetworkPolicy files."""
        results = self.analyzer.analyze_network_policies(self.temp_dir)

        assert results["total_policies"] == 0
        assert results["policies_with_internet_egress"] == 0
        assert len(results["policies_analyzed"]) == 0
        assert results["egress_risk_summary"]["HIGH"] == 0
        assert results["egress_risk_summary"]["MEDIUM"] == 0
        assert results["egress_risk_summary"]["LOW"] == 0

    def test_analyze_network_policy_with_internet_egress(self):
        """Test analyzing a NetworkPolicy that allows internet egress."""
        # Create a NetworkPolicy YAML file with internet egress
        policy_content = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-internet-egress
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
  ports:
  - protocol: TCP
    port: 80
  - protocol: TCP
    port: 443
"""

        policy_file = Path(self.temp_dir) / "networkpolicy.yaml"
        with open(policy_file, "w") as f:
            f.write(policy_content)

        results = self.analyzer.analyze_network_policies(self.temp_dir)

        assert results["total_policies"] == 1
        assert results["policies_with_internet_egress"] == 1
        assert len(results["policies_analyzed"]) == 1

        policy_analysis = results["policies_analyzed"][0]
        assert policy_analysis["has_internet_egress"] == True
        assert policy_analysis["egress_risk_level"] == "HIGH"
        assert "0.0.0.0/0" in policy_analysis["internet_cidrs_found"]

    def test_analyze_network_policy_without_internet_egress(self):
        """Test analyzing a NetworkPolicy that restricts egress."""
        # Create a NetworkPolicy YAML file without internet egress
        policy_content = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: restrict-egress
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 10.0.0.0/8
  ports:
  - protocol: TCP
    port: 53
"""

        policy_file = Path(self.temp_dir) / "networkpolicy.yaml"
        with open(policy_file, "w") as f:
            f.write(policy_content)

        results = self.analyzer.analyze_network_policies(self.temp_dir)

        assert results["total_policies"] == 1
        assert results["policies_with_internet_egress"] == 0
        assert len(results["policies_analyzed"]) == 1

        policy_analysis = results["policies_analyzed"][0]
        assert policy_analysis["has_internet_egress"] == False
        assert policy_analysis["egress_risk_level"] == "LOW"
        assert len(policy_analysis["internet_cidrs_found"]) == 0

    def test_analyze_multiple_network_policies(self):
        """Test analyzing multiple NetworkPolicy files."""
        # Create multiple NetworkPolicy files
        policies = [
            ("allow-internet.yaml", """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-internet
spec:
  podSelector: {}
  egress:
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
"""),
            ("restrict-internal.yaml", """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: restrict-internal
spec:
  podSelector: {}
  egress:
  - to:
    - ipBlock:
        cidr: 10.0.0.0/8
"""),
        ]

        for filename, content in policies:
            policy_file = Path(self.temp_dir) / filename
            with open(policy_file, "w") as f:
                f.write(content)

        results = self.analyzer.analyze_network_policies(self.temp_dir)

        assert results["total_policies"] == 2
        assert results["policies_with_internet_egress"] == 1
        assert results["egress_risk_summary"]["HIGH"] == 1
        assert results["egress_risk_summary"]["LOW"] == 1

    def test_analyze_network_policy_with_complex_egress(self):
        """Test analyzing a NetworkPolicy with complex egress rules."""
        # Create a NetworkPolicy with many egress rules
        policy_content = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: complex-egress
spec:
  podSelector: {}
  egress:
  - to:
    - ipBlock:
        cidr: 10.0.0.0/8
  - to:
    - ipBlock:
        cidr: 172.16.0.0/12
  - to:
    - ipBlock:
        cidr: 192.168.0.0/16
  - to:
    - namespaceSelector: {}
  - to:
    - podSelector: {}
  ports:
  - protocol: TCP
    port: 80
  - protocol: TCP
    port: 443
  - protocol: TCP
    port: 53
  - protocol: UDP
    port: 53
"""

        policy_file = Path(self.temp_dir) / "networkpolicy.yaml"
        with open(policy_file, "w") as f:
            f.write(policy_content)

        results = self.analyzer.analyze_network_policies(self.temp_dir)

        assert results["total_policies"] == 1
        assert results["policies_with_internet_egress"] == 0

        policy_analysis = results["policies_analyzed"][0]
        assert policy_analysis["has_internet_egress"] == False
        assert policy_analysis["egress_risk_level"] == "MEDIUM"  # Complex rules
        assert len(policy_analysis["egress_rules"]) > 0

    def test_analyze_network_policy_with_except_blocks(self):
        """Test analyzing a NetworkPolicy with except blocks."""
        # Create a NetworkPolicy with internet egress but with exceptions
        policy_content = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: internet-with-exceptions
spec:
  podSelector: {}
  egress:
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
        except:
        - 10.0.0.0/8
        - 172.16.0.0/12
"""

        policy_file = Path(self.temp_dir) / "networkpolicy.yaml"
        with open(policy_file, "w") as f:
            f.write(policy_content)

        results = self.analyzer.analyze_network_policies(self.temp_dir)

        assert results["total_policies"] == 1
        assert results["policies_with_internet_egress"] == 1

        policy_analysis = results["policies_analyzed"][0]
        assert policy_analysis["has_internet_egress"] == True
        assert "0.0.0.0/0" in policy_analysis["internet_cidrs_found"]

    def test_generate_egress_summary(self):
        """Test generating egress summary from analysis results."""
        analysis_results = {
            "total_policies": 3,
            "policies_with_internet_egress": 1,
            "policies_analyzed": [
                {"has_egress": True, "has_internet_egress": True, "egress_risk_level": "HIGH"},
                {"has_egress": True, "has_internet_egress": False, "egress_risk_level": "LOW"},
                {"has_egress": True, "has_internet_egress": False, "egress_risk_level": "LOW"},
            ],
            "egress_risk_summary": {"HIGH": 1, "MEDIUM": 0, "LOW": 2},
        }

        summary = self.analyzer.generate_egress_summary(analysis_results)

        assert summary["total_network_policies"] == 3
        assert summary["policies_with_egress"] == 3  # All policies have egress analysis
        assert summary["policies_with_internet_egress"] == 1
        assert summary["egress_risk_breakdown"]["HIGH"] == 1
        assert summary["egress_risk_breakdown"]["LOW"] == 2
        assert len(summary["recommendations"]) > 0

    def test_get_egress_risk_multiplier(self):
        """Test getting egress risk multipliers."""
        assert self.analyzer.get_egress_risk_multiplier("HIGH") == 1.5
        assert self.analyzer.get_egress_risk_multiplier("MEDIUM") == 1.2
        assert self.analyzer.get_egress_risk_multiplier("LOW") == 1.0
        assert self.analyzer.get_egress_risk_multiplier("UNKNOWN") == 1.0

    def test_find_network_policies_in_subdirectories(self):
        """Test finding NetworkPolicy files in subdirectories."""
        # Create subdirectories with NetworkPolicy files
        charts_dir = Path(self.temp_dir) / "charts" / "myapp" / "templates"
        charts_dir.mkdir(parents=True, exist_ok=True)

        policy_content = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: chart-network-policy
spec:
  podSelector: {}
  egress:
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
"""

        policy_file = charts_dir / "networkpolicy.yaml"
        with open(policy_file, "w") as f:
            f.write(policy_content)

        results = self.analyzer.analyze_network_policies(self.temp_dir)

        assert results["total_policies"] == 1
        assert results["policies_with_internet_egress"] == 1

    def test_analyze_invalid_yaml_file(self):
        """Test handling of invalid YAML files."""
        # Create an invalid YAML file
        invalid_file = Path(self.temp_dir) / "invalid.yaml"
        with open(invalid_file, "w") as f:
            f.write("invalid: yaml: content: [")

        # Should not crash and should ignore invalid files
        results = self.analyzer.analyze_network_policies(self.temp_dir)
        assert results["total_policies"] == 0

    def test_analyze_non_networkpolicy_yaml(self):
        """Test handling of YAML files that don't contain NetworkPolicy resources."""
        # Create a YAML file with a different resource type
        deployment_content = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
"""

        deployment_file = Path(self.temp_dir) / "deployment.yaml"
        with open(deployment_file, "w") as f:
            f.write(deployment_content)

        results = self.analyzer.analyze_network_policies(self.temp_dir)

        # Should not count as a NetworkPolicy
        assert results["total_policies"] == 0