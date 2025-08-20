"""
Reticulum - Exposure Scanner for Cloud Infrastructure Security Analysis

This tool analyzes monorepos containing Helm charts to identify internet exposure
and map affected source code paths. It provides comprehensive security assessment
for DevSecOps and Cloud Security teams.
"""

__version__ = "0.2.2"
__author__ = "Jose Palanco <jose.palanco@plexicus.ai>"
__license__ = "MIT"

from .main import ExposureScanner

__all__ = ["ExposureScanner"]
