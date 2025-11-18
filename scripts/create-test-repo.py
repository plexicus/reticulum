#!/usr/bin/env python3
"""
Advanced Test Repository Generator

This script dynamically generates a comprehensive test repository for Reticulum scanner testing.
The repository includes various Helm charts, Dockerfiles, and source code to test different
exposure scenarios and edge cases.
"""

import os
import shutil
import yaml
from pathlib import Path


def create_directory_structure(base_path: Path):
    """Create the main directory structure for the test repository."""
    directories = [
        "charts",
        "dockerfiles",
        "source-code",
        "source-code/frontend",
        "source-code/backend",
        "source-code/database",
        "source-code/monitoring"
    ]

    for directory in directories:
        (base_path / directory).mkdir(parents=True, exist_ok=True)

    return base_path


def create_chart_yaml(chart_name: str, version: str = "1.0.0", description: str = ""):
    """Create a basic Chart.yaml file."""
    return {
        "apiVersion": "v2",
        "name": chart_name,
        "description": description or f"{chart_name} Helm chart",
        "type": "application",
        "version": version,
        "appVersion": version
    }


def create_frontend_web_chart(chart_path: Path):
    """Create frontend web chart with high exposure (Ingress)."""
    # Chart.yaml
    chart_yaml = create_chart_yaml(
        "frontend-web",
        description="Frontend web application with external ingress"
    )
    (chart_path / "Chart.yaml").write_text(yaml.dump(chart_yaml))

    # values.yaml
    values = {
        "image": {
            "repository": "nginx",
            "tag": "latest",
            "pullPolicy": "IfNotPresent"
        },
        "service": {
            "type": "ClusterIP",
            "port": 80,
            "targetPort": 80
        },
        "ingress": {
            "enabled": True,
            "className": "nginx",
            "hosts": [
                {
                    "host": "frontend.example.com",
                    "paths": [
                        {"path": "/", "pathType": "Prefix"}
                    ]
                }
            ]
        },
        "resources": {
            "requests": {
                "memory": "128Mi",
                "cpu": "100m"
            },
            "limits": {
                "memory": "256Mi",
                "cpu": "200m"
            }
        }
    }
    (chart_path / "values.yaml").write_text(yaml.dump(values))

    # templates/service.yaml
    service_template = """apiVersion: v1
kind: Service
metadata:
  name: {{ .Chart.Name }}
  labels:
    app: {{ .Chart.Name }}
spec:
  type: {{ .Values.service.type }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
      protocol: TCP
  selector:
    app: {{ .Chart.Name }}
"""
    (chart_path / "templates").mkdir(exist_ok=True)
    (chart_path / "templates" / "service.yaml").write_text(service_template)

    # templates/networkpolicy.yaml - Allow internet egress
    networkpolicy_template = """apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ .Chart.Name }}-network-policy
  labels:
    app: {{ .Chart.Name }}
spec:
  podSelector:
    matchLabels:
      app: {{ .Chart.Name }}
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
        except:
        - 10.0.0.0/8
        - 172.16.0.0/12
        - 192.168.0.0/16
    ports:
    - protocol: TCP
      port: 80
    - protocol: TCP
      port: 443
"""
    (chart_path / "templates" / "networkpolicy.yaml").write_text(networkpolicy_template)


def create_api_gateway_chart(chart_path: Path):
    """Create API gateway chart with high exposure (LoadBalancer)."""
    chart_yaml = create_chart_yaml(
        "api-gateway",
        description="API Gateway with external load balancer"
    )
    (chart_path / "Chart.yaml").write_text(yaml.dump(chart_yaml))

    values = {
        "image": {
            "repository": "kong",
            "tag": "3.4",
            "pullPolicy": "IfNotPresent"
        },
        "service": {
            "type": "LoadBalancer",
            "port": 8000,
            "targetPort": 8000
        },
        "resources": {
            "requests": {
                "memory": "256Mi",
                "cpu": "200m"
            },
            "limits": {
                "memory": "512Mi",
                "cpu": "500m"
            }
        }
    }
    (chart_path / "values.yaml").write_text(yaml.dump(values))

    # templates/networkpolicy.yaml - Restricted egress
    networkpolicy_template = """apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ .Chart.Name }}-network-policy
  labels:
    app: {{ .Chart.Name }}
spec:
  podSelector:
    matchLabels:
      app: {{ .Chart.Name }}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: backend-services
    ports:
    - protocol: TCP
      port: 8080
  - to:
    - ipBlock:
        cidr: 10.0.0.0/8
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
"""
    (chart_path / "templates").mkdir(exist_ok=True)
    (chart_path / "templates" / "networkpolicy.yaml").write_text(networkpolicy_template)


def create_backend_service_chart(chart_path: Path):
    """Create backend service chart with medium exposure (internal)."""
    chart_yaml = create_chart_yaml(
        "backend-service",
        description="Backend service with internal access only"
    )
    (chart_path / "Chart.yaml").write_text(yaml.dump(chart_yaml))

    values = {
        "image": {
            "repository": "python",
            "tag": "3.11",
            "pullPolicy": "IfNotPresent"
        },
        "service": {
            "type": "ClusterIP",
            "port": 8080,
            "targetPort": 8080
        },
        "database": {
            "host": "database-primary",
            "port": 5432
        },
        "resources": {
            "requests": {
                "memory": "256Mi",
                "cpu": "200m"
            },
            "limits": {
                "memory": "512Mi",
                "cpu": "500m"
            }
        }
    }
    (chart_path / "values.yaml").write_text(yaml.dump(values))


def create_worker_service_chart(chart_path: Path):
    """Create worker service chart with low exposure (no external access)."""
    chart_yaml = create_chart_yaml(
        "worker-service",
        description="Background worker service with no external access"
    )
    (chart_path / "Chart.yaml").write_text(yaml.dump(chart_yaml))

    values = {
        "image": {
            "repository": "redis",
            "tag": "7.2",
            "pullPolicy": "IfNotPresent"
        },
        "service": {
            "type": "ClusterIP",
            "port": 6379,
            "targetPort": 6379
        },
        "resources": {
            "requests": {
                "memory": "128Mi",
                "cpu": "100m"
            },
            "limits": {
                "memory": "256Mi",
                "cpu": "200m"
            }
        }
    }
    (chart_path / "values.yaml").write_text(yaml.dump(values))


def create_database_primary_chart(chart_path: Path):
    """Create database chart with medium exposure (internal)."""
    chart_yaml = create_chart_yaml(
        "database-primary",
        description="Primary database with internal access"
    )
    (chart_path / "Chart.yaml").write_text(yaml.dump(chart_yaml))

    values = {
        "image": {
            "repository": "postgres",
            "tag": "15",
            "pullPolicy": "IfNotPresent"
        },
        "service": {
            "type": "ClusterIP",
            "port": 5432,
            "targetPort": 5432
        },
        "persistence": {
            "enabled": True,
            "size": "10Gi"
        },
        "resources": {
            "requests": {
                "memory": "512Mi",
                "cpu": "500m"
            },
            "limits": {
                "memory": "1Gi",
                "cpu": "1"
            }
        }
    }
    (chart_path / "values.yaml").write_text(yaml.dump(values))


def create_cache_service_chart(chart_path: Path):
    """Create cache service chart with low exposure."""
    chart_yaml = create_chart_yaml(
        "cache-service",
        description="Redis cache service"
    )
    (chart_path / "Chart.yaml").write_text(yaml.dump(chart_yaml))

    values = {
        "image": {
            "repository": "redis",
            "tag": "7.2",
            "pullPolicy": "IfNotPresent"
        },
        "service": {
            "type": "ClusterIP",
            "port": 6379,
            "targetPort": 6379
        },
        "resources": {
            "requests": {
                "memory": "128Mi",
                "cpu": "100m"
            },
            "limits": {
                "memory": "256Mi",
                "cpu": "200m"
            }
        }
    }
    (chart_path / "values.yaml").write_text(yaml.dump(values))


def create_monitoring_stack_chart(chart_path: Path):
    """Create monitoring stack chart with high exposure (NodePort)."""
    chart_yaml = create_chart_yaml(
        "monitoring-stack",
        description="Monitoring stack with external access"
    )
    (chart_path / "Chart.yaml").write_text(yaml.dump(chart_yaml))

    values = {
        "grafana": {
            "enabled": True,
            "service": {
                "type": "NodePort",
                "port": 3000
            }
        },
        "prometheus": {
            "enabled": True,
            "service": {
                "type": "ClusterIP",
                "port": 9090
            }
        }
    }
    (chart_path / "values.yaml").write_text(yaml.dump(values))


def create_security_gateway_chart(chart_path: Path):
    """Create security gateway chart with high exposure."""
    chart_yaml = create_chart_yaml(
        "security-gateway",
        description="Security gateway with external access"
    )
    (chart_path / "Chart.yaml").write_text(yaml.dump(chart_yaml))

    values = {
        "image": {
            "repository": "traefik",
            "tag": "v3.0",
            "pullPolicy": "IfNotPresent"
        },
        "service": {
            "type": "LoadBalancer",
            "port": 80,
            "targetPort": 80
        },
        "resources": {
            "requests": {
                "memory": "256Mi",
                "cpu": "200m"
            },
            "limits": {
                "memory": "512Mi",
                "cpu": "500m"
            }
        }
    }
    (chart_path / "values.yaml").write_text(yaml.dump(values))


def create_load_balancer_chart(chart_path: Path):
    """Create load balancer chart with high exposure."""
    chart_yaml = create_chart_yaml(
        "load-balancer",
        description="Load balancer with external access"
    )
    (chart_path / "Chart.yaml").write_text(yaml.dump(chart_yaml))

    values = {
        "image": {
            "repository": "haproxy",
            "tag": "2.8",
            "pullPolicy": "IfNotPresent"
        },
        "service": {
            "type": "LoadBalancer",
            "port": 80,
            "targetPort": 80
        },
        "resources": {
            "requests": {
                "memory": "128Mi",
                "cpu": "100m"
            },
            "limits": {
                "memory": "256Mi",
                "cpu": "200m"
            }
        }
    }
    (chart_path / "values.yaml").write_text(yaml.dump(values))


def create_edge_cases_chart(chart_path: Path):
    """Create edge cases chart with various exposure scenarios."""
    chart_yaml = create_chart_yaml(
        "edge-cases",
        description="Edge cases with various exposure patterns"
    )
    (chart_path / "Chart.yaml").write_text(yaml.dump(chart_yaml))

    values = {
        "multipleServices": {
            "web": {
                "service": {
                    "type": "ClusterIP",
                    "port": 80
                }
            },
            "api": {
                "service": {
                    "type": "NodePort",
                    "port": 8080
                }
            },
            "admin": {
                "service": {
                    "type": "LoadBalancer",
                    "port": 8443
                }
            }
        },
        "securityContext": {
            "privileged": False,
            "runAsNonRoot": True
        }
    }
    (chart_path / "values.yaml").write_text(yaml.dump(values))

    # templates/networkpolicy.yaml - Complex NetworkPolicy with multiple rules
    networkpolicy_template = """apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ .Chart.Name }}-network-policy
  labels:
    app: {{ .Chart.Name }}
spec:
  podSelector:
    matchLabels:
      app: {{ .Chart.Name }}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: frontend
    ports:
    - protocol: TCP
      port: 80
  - from:
    - ipBlock:
        cidr: 192.168.1.0/24
    ports:
    - protocol: TCP
      port: 8080
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 9090
  egress:
  - to:
    - ipBlock:
        cidr: 10.0.0.0/8
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
  - to:
    - namespaceSelector:
        matchLabels:
          name: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          name: cache
    ports:
    - protocol: TCP
      port: 6379
"""
    (chart_path / "templates").mkdir(exist_ok=True)
    (chart_path / "templates" / "networkpolicy.yaml").write_text(networkpolicy_template)


def create_dockerfiles(base_path: Path):
    """Create sample Dockerfiles."""
    # Frontend Dockerfile
    frontend_dockerfile = """FROM nginx:latest
COPY . /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
"""
    (base_path / "dockerfiles" / "frontend.Dockerfile").write_text(frontend_dockerfile)

    # Backend Dockerfile
    backend_dockerfile = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["python", "app.py"]
"""
    (base_path / "dockerfiles" / "backend.Dockerfile").write_text(backend_dockerfile)

    # Database Dockerfile
    database_dockerfile = """FROM postgres:15
COPY init.sql /docker-entrypoint-initdb.d/
EXPOSE 5432
"""
    (base_path / "dockerfiles" / "database.Dockerfile").write_text(database_dockerfile)


def create_source_code_files(base_path: Path):
    """Create sample source code files."""
    # Frontend files
    (base_path / "source-code" / "frontend" / "index.html").write_text("<html><body>Frontend App</body></html>")
    (base_path / "source-code" / "frontend" / "app.js").write_text("console.log('Frontend app');")

    # Backend files
    (base_path / "source-code" / "backend" / "app.py").write_text("""from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello from backend'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
""")
    (base_path / "source-code" / "backend" / "requirements.txt").write_text("flask==2.3.3")

    # Database files
    (base_path / "source-code" / "database" / "init.sql").write_text("""CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100)
);
""")

    # Monitoring files
    (base_path / "source-code" / "monitoring" / "dashboard.json").write_text("{\"dashboard\": \"monitoring\"}")


def create_readme(base_path: Path):
    """Create README for the test repository."""
    readme_content = """# Advanced Test Repository

This repository is dynamically generated for testing the Reticulum scanner.
It contains various Helm charts, Dockerfiles, and source code to test different
exposure scenarios and edge cases.

## Structure

- `charts/` - Helm charts with various exposure levels
- `dockerfiles/` - Sample Dockerfiles for different services
- `source-code/` - Sample source code files

## Test Scenarios

### High Exposure Services
- `frontend-web` - External ingress
- `api-gateway` - LoadBalancer service
- `monitoring-stack` - NodePort service
- `security-gateway` - LoadBalancer service
- `load-balancer` - LoadBalancer service

### Medium Exposure Services
- `backend-service` - Internal ClusterIP
- `database-primary` - Internal ClusterIP

### Low Exposure Services
- `worker-service` - Internal ClusterIP
- `cache-service` - Internal ClusterIP

### Edge Cases
- `edge-cases` - Multiple service types in one chart

## Usage

This repository is automatically generated by `scripts/create-test-repo.py`.
It should not be committed to version control.
"""
    (base_path / "README.md").write_text(readme_content)


def main():
    """Main function to generate the test repository."""
    repo_path = Path(__file__).parent.parent / "tests" / "advanced-test-repo"

    # Handle existing repository
    if repo_path.exists():
        print(f"⚠️  Advanced test repository already exists at: {repo_path}")
        print("Options:")
        print("  [r] Regenerate (delete and recreate)")
        print("  [s] Skip (keep existing)")
        print("  [q] Quit")

        while True:
            choice = input("\nChoose option [r/s/q]: ").strip().lower()
            if choice in ['r', 'regenerate']:
                print("🗑️  Removing existing repository...")
                shutil.rmtree(repo_path)
                break
            elif choice in ['s', 'skip']:
                print("✅ Keeping existing repository.")
                return
            elif choice in ['q', 'quit']:
                print("👋 Exiting without changes.")
                return
            else:
                print("❌ Invalid option. Please choose 'r', 's', or 'q'.")
    else:
        print(f"🔧 Creating advanced test repository at: {repo_path}")

    # Create directory structure
    create_directory_structure(repo_path)

    # Create charts
    charts = [
        ("frontend-web", create_frontend_web_chart),
        ("api-gateway", create_api_gateway_chart),
        ("backend-service", create_backend_service_chart),
        ("worker-service", create_worker_service_chart),
        ("database-primary", create_database_primary_chart),
        ("cache-service", create_cache_service_chart),
        ("monitoring-stack", create_monitoring_stack_chart),
        ("security-gateway", create_security_gateway_chart),
        ("load-balancer", create_load_balancer_chart),
        ("edge-cases", create_edge_cases_chart)
    ]

    for chart_name, create_func in charts:
        chart_path = repo_path / "charts" / chart_name
        chart_path.mkdir(parents=True, exist_ok=True)
        create_func(chart_path)

    # Create Dockerfiles
    create_dockerfiles(repo_path)

    # Create source code files
    create_source_code_files(repo_path)

    # Create README
    create_readme(repo_path)

    print(f"✅ Advanced test repository generated at: {repo_path}")
    print(f"📊 Created {len(charts)} Helm charts")
    print(f"🐳 Created 3 Dockerfiles")
    print(f"📝 Created source code files in 4 directories")


if __name__ == "__main__":
    main()