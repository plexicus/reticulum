import os
import subprocess

def process_task(task_data):
    # RCE Vulnerability: using eval on untrusted input
    # Semgrep rule: python.lang.security.audit.eval-detected
    result = eval(task_data)
    return result

def run_command(cmd):
    # Command Injection Vulnerability
    # Semgrep rule: python.lang.security.audit.subprocess-shell-true
    subprocess.call(cmd, shell=True)

def connect_db():
    # Hardcoded Secret
    # Semgrep rule: generic.secrets.gitleaks.hardcoded-secret
    password = "super-secret-password-123"
    print(f"Connecting with {password}")
