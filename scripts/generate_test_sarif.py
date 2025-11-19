#!/usr/bin/env python3
"""
Generate test SARIF files for Trivy and Semgrep from a test repository.
These files can be used in CI environments where Docker is not available.
"""

import json
import os
import tempfile
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reticulum.docker_runner import DockerRunner


def generate_trivy_sarif():
    """Generate Trivy SARIF file from static test repository."""
    print("🔍 Generating Trivy SARIF file...")

    # Use the static test repository
    test_repo_dir = "tests/advanced-test-repo"

    if not os.path.exists(test_repo_dir):
        print(f"❌ Static test repository not found: {test_repo_dir}")
        return False

    # Run Trivy scan
    runner = DockerRunner()

    # Use temporary directory for output to avoid path issues
    with tempfile.NamedTemporaryFile(suffix='.sarif', delete=False) as temp_file:
        output_file = temp_file.name

    result = runner.run_trivy_sca(test_repo_dir, output_file)

    # Copy to final location
    final_output = "tests/test_data/trivy_results.sarif"
    os.makedirs(os.path.dirname(final_output), exist_ok=True)

    if result["success"]:
        import shutil
        shutil.copy(output_file, final_output)
        os.unlink(output_file)  # Clean up temp file

    if result["success"]:
        print(f"✅ Trivy SARIF generated: {final_output}")
        print(f"   Vulnerabilities found: {result['severity_counts']['total']}")
    else:
        print(f"❌ Failed to generate Trivy SARIF: {result['error']}")

    return result["success"]


def generate_semgrep_sarif():
    """Generate Semgrep SARIF file from static test repository."""
    print("🔍 Generating Semgrep SARIF file...")

    # Use the static test repository
    test_repo_dir = "tests/advanced-test-repo"

    if not os.path.exists(test_repo_dir):
        print(f"❌ Static test repository not found: {test_repo_dir}")
        return False

    # Run Semgrep scan
    runner = DockerRunner()

    # Use temporary directory for output to avoid path issues
    with tempfile.NamedTemporaryFile(suffix='.sarif', delete=False) as temp_file:
        output_file = temp_file.name

    result = runner.run_semgrep_sast(test_repo_dir, output_file)

    # Copy to final location
    final_output = "tests/test_data/semgrep_results.sarif"
    os.makedirs(os.path.dirname(final_output), exist_ok=True)

    if result["success"]:
        import shutil
        shutil.copy(output_file, final_output)
        os.unlink(output_file)  # Clean up temp file

    if result["success"]:
        print(f"✅ Semgrep SARIF generated: {final_output}")
        print(f"   Issues found: {result['severity_counts']['total']}")
    else:
        print(f"❌ Failed to generate Semgrep SARIF: {result['error']}")

    return result["success"]


def main():
    """Generate both Trivy and Semgrep SARIF files."""
    print("🚀 Generating test SARIF files for CI...")

    success = True

    # Generate Trivy SARIF
    if not generate_trivy_sarif():
        success = False

    # Generate Semgrep SARIF
    if not generate_semgrep_sarif():
        success = False

    if success:
        print("\n✅ All SARIF files generated successfully!")
        print("   These files can be used in CI environments where Docker is not available.")
    else:
        print("\n❌ Some SARIF files failed to generate")
        sys.exit(1)


if __name__ == "__main__":
    main()