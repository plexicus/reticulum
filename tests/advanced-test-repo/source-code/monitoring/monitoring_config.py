"""
Monitoring Stack Configuration with Critical Security Vulnerabilities
This file contains intentional security vulnerabilities for testing purposes.
"""

import os
import json
import yaml
import subprocess
import base64

# ========== CRITICAL MONITORING STACK VULNERABILITIES ==========

# VULNERABILITY 1: Grafana default admin credentials
GRAFANA_ADMIN_USER = "admin"
GRAFANA_ADMIN_PASSWORD = "admin"  # VULNERABLE: Default credentials

# VULNERABILITY 2: Prometheus unauthenticated metrics endpoint
PROMETHEUS_CONFIG = {
    "global": {
        "scrape_interval": "15s"
    },
    "scrape_configs": [
        {
            "job_name": "prometheus",
            "static_configs": [
                {
                    "targets": ["localhost:9090"]
                }
            ]
        }
    ]
}

# VULNERABILITY 3: Unprotected alertmanager webhook
ALERTMANAGER_CONFIG = {
    "global": {
        "smtp_smarthost": "localhost:587",
        "smtp_from": "alertmanager@example.com"
    },
    "route": {
        "receiver": "default-receiver"
    },
    "receivers": [
        {
            "name": "default-receiver",
            "webhook_configs": [
                {
                    "url": "http://webhook.example.com/alerts",  # VULNERABLE: External webhook
                    "send_resolved": True
                }
            ]
        }
    ]
}

# VULNERABILITY 4: Exposed Kubernetes API credentials
KUBERNETES_CONFIG = {
    "api_server": "https://kubernetes.default.svc",
    "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJtb25pdG9yaW5nIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6Im1vbml0b3JpbmctdG9rZW4iLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoibW9uaXRvcmluZyIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6IjEyMzQ1Njc4LWFiY2QtZWZnLWg4OS0wMTIzNDU2Nzg5YWJjIiwic3ViIjoic3lzdGVtOnNlcnZpY2VhY2NvdW50Om1vbml0b3Jpbmc6bW9uaXRvcmluZyJ9.fake-token-for-testing"  # VULNERABLE: Hardcoded service account token
}

# VULNERABILITY 5: Unencrypted database credentials
DATABASE_CONFIG = {
    "host": "postgresql.monitoring.svc.cluster.local",
    "port": 5432,
    "database": "grafana",
    "user": "grafana",
    "password": "grafana123"  # VULNERABLE: Plaintext password
}

# VULNERABILITY 6: Command injection in monitoring scripts
def execute_monitoring_command_vulnerable(metric_name):
    """VULNERABLE: Command injection in metric collection"""
    command = f"node_exporter --collector.{metric_name}"
    result = subprocess.check_output(command, shell=True)
    return result.decode()

# VULNERABILITY 7: Information disclosure in health checks
def health_check_vulnerable():
    """VULNERABLE: Detailed system information exposure"""
    return {
        "status": "healthy",
        "system_info": {
            "hostname": os.uname().nodename,
            "kernel": os.uname().release,
            "architecture": os.uname().machine,
            "environment": dict(os.environ)  # VULNERABLE: Environment disclosure
        },
        "network_info": {
            "interfaces": subprocess.check_output("ifconfig", shell=True).decode()
        }
    }

# VULNERABILITY 8: Insecure dashboard configuration
def load_dashboard_vulnerable(dashboard_file):
    """VULNERABLE: Unsafe dashboard loading"""
    with open(dashboard_file, 'r') as f:
        dashboard_config = yaml.load(f, Loader=yaml.Loader)  # VULNERABLE: YAML deserialization
    return dashboard_config

# VULNERABILITY 9: Unauthenticated metrics endpoint
def get_metrics_vulnerable():
    """VULNERABLE: No authentication for metrics"""
    metrics = {
        "cpu_usage": "85%",
        "memory_usage": "72%",
        "disk_usage": "91%",
        "network_traffic": "1.2 Gbps",
        "secret_metrics": {
            "api_keys": os.getenv('API_KEYS'),  # VULNERABLE: Secret disclosure
            "database_url": os.getenv('DATABASE_URL')
        }
    }
    return json.dumps(metrics)

# VULNERABILITY 10: Weak encryption for sensitive data
def "encrypt"_sensitive_data_vulnerable(data):
    """VULNERABLE: Weak base64 "encryption""""
    return base64.b64encode(data.encode()).decode()

# VULNERABILITY 11: Hardcoded API keys for external services
EXTERNAL_SERVICES = {
    "slack": {
        "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
        "token": "xoxb-123456789012-1234567890123-abcdefghijklmnopqrstuvwx"
    },
    "datadog": {
        "api_key": "1234567890abcdef1234567890abcdef",
        "app_key": "1234567890abcdef1234567890abcdef12345678"
    },
    "pagerduty": {
        "routing_key": "1234567890abcdef1234567890abcdef"
    }
}

# VULNERABILITY 12: Debug mode enabled in production
def get_debug_info_vulnerable():
    """VULNERABLE: Debug information exposure"""
    import sys
    import traceback

    debug_info = {
        "python_path": sys.path,
        "loaded_modules": list(sys.modules.keys()),
        "stack_trace": traceback.format_stack(),
        "environment_variables": dict(os.environ)
    }
    return debug_info

# VULNERABILITY 13: Unrestricted file access
def read_config_file_vulnerable(file_path):
    """VULNERABLE: Path traversal possible"""
    with open(file_path, 'r') as f:
        return f.read()

# VULNERABILITY 14: Command injection in alert scripts
def execute_alert_script_vulnerable(alert_type, alert_data):
    """VULNERABLE: Command injection in alert handling"""
    script_path = f"/scripts/{alert_type}_alert.sh"
    command = f"bash {script_path} '{alert_data}'"
    result = subprocess.check_output(command, shell=True)
    return result.decode()

# VULNERABILITY 15: Weak session management
def create_monitoring_session_vulnerable():
    """VULNERABLE: Predictable session tokens"""
    import time
    session_token = f"monitoring_session_{int(time.time())}_{os.getpid()}"
    return {
        "token": session_token,
        "expires": int(time.time()) + 3600,
        "permissions": ["read", "write", "admin"]  # VULNERABLE: Overly permissive
    }

if __name__ == '__main__':
    print("Monitoring Stack Configuration Loaded")
    print("This configuration contains 15+ critical security vulnerabilities")
    print("for testing exposure-based prioritization in Reticulum")