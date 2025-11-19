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
    """Generate Trivy SARIF file from test repository."""
    print("🔍 Generating Trivy SARIF file...")

    # Create test repository
    test_repo_dir = tempfile.mkdtemp(prefix="reticulum-test-")

    # Create vulnerable_app.py
    vulnerable_app_content = '''import subprocess
import pickle
import os

def sql_injection_vulnerable(username):
    # VULNERABLE: SQL injection
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return query

def command_injection_vulnerable(command):
    # VULNERABLE: Command injection
    result = subprocess.run(f"echo {command}", shell=True, capture_output=True)
    return result.stdout

def insecure_deserialization_vulnerable(data):
    # VULNERABLE: Insecure deserialization
    return pickle.loads(data)

def xss_vulnerable(user_input):
    # VULNERABLE: XSS - direct HTML injection
    html = f"<div>{user_input}</div>"
    return html

def hardcoded_secret_vulnerable():
    # VULNERABLE: Hardcoded secret
    api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
    return api_key

def weak_crypto_vulnerable():
    # VULNERABLE: Weak cryptographic algorithm
    import hashlib
    password_hash = hashlib.md5(b"password123").hexdigest()
    return password_hash

def path_traversal_vulnerable(filename):
    # VULNERABLE: Path traversal
    file_path = f"/var/www/uploads/{filename}"
    with open(file_path, 'r') as f:
        return f.read()

def eval_injection_vulnerable(user_input):
    # VULNERABLE: eval injection
    result = eval(user_input)
    return result
'''

    with open(os.path.join(test_repo_dir, "vulnerable_app.py"), "w") as f:
        f.write(vulnerable_app_content)

    # Create requirements.txt with vulnerable dependencies
    requirements_content = """requests==2.25.1
Django==3.1.14
urllib3==1.26.4
"""

    with open(os.path.join(test_repo_dir, "requirements.txt"), "w") as f:
        f.write(requirements_content)

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

    # Clean up
    import shutil
    shutil.rmtree(test_repo_dir)

    return result["success"]


def generate_semgrep_sarif():
    """Generate Semgrep SARIF file from test repository."""
    print("🔍 Generating Semgrep SARIF file...")

    # Create test repository
    test_repo_dir = tempfile.mkdtemp(prefix="reticulum-test-")

    # Create vulnerable_app.py
    vulnerable_app_content = '''import subprocess
import pickle
import os

def sql_injection_vulnerable(username):
    # VULNERABLE: SQL injection
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return query

def command_injection_vulnerable(command):
    # VULNERABLE: Command injection
    result = subprocess.run(f"echo {command}", shell=True, capture_output=True)
    return result.stdout

def insecure_deserialization_vulnerable(data):
    # VULNERABLE: Insecure deserialization
    return pickle.loads(data)

def xss_vulnerable(user_input):
    # VULNERABLE: XSS - direct HTML injection
    html = f"<div>{user_input}</div>"
    return html

def hardcoded_secret_vulnerable():
    # VULNERABLE: Hardcoded secret
    api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
    return api_key

def weak_crypto_vulnerable():
    # VULNERABLE: Weak cryptographic algorithm
    import hashlib
    password_hash = hashlib.md5(b"password123").hexdigest()
    return password_hash

def path_traversal_vulnerable(filename):
    # VULNERABLE: Path traversal
    file_path = f"/var/www/uploads/{filename}"
    with open(file_path, 'r') as f:
        return f.read()

def eval_injection_vulnerable(user_input):
    # VULNERABLE: eval injection
    result = eval(user_input)
    return result
'''

    with open(os.path.join(test_repo_dir, "vulnerable_app.py"), "w") as f:
        f.write(vulnerable_app_content)

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

    # Clean up
    import shutil
    shutil.rmtree(test_repo_dir)

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