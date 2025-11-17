"""
Configuration system for Reticulum Security Scanner.

Provides centralized configuration management for security tools,
Docker settings, and scan parameters.
"""

import os
from typing import Dict, Any, Optional


class SecurityScannerConfig:
    """Configuration manager for security scanner settings."""

    # Default configuration
    DEFAULTS = {
        # Docker settings
        "docker": {
            "timeout": 600,  # 10 minutes
            "max_retries": 3,
            "memory_limit": "1g",
            "cpu_limit": "1.0",
        },
        # Security tool versions
        "tools": {
            "trivy": {
                "image": "aquasec/trivy:latest",
                "severity_levels": "CRITICAL,HIGH,MEDIUM,LOW",
            },
            "semgrep": {
                "image": "returntocorp/semgrep:latest",
                "config": "auto",
            },
        },
        # Scanner behavior
        "scanner": {
            "parallel_execution": True,
            "enable_trivy": True,
            "enable_semgrep": True,
            "output_format": "sarif",
        },
        # Performance settings
        "performance": {
            "max_workers": 2,
            "cache_results": False,
            "cache_ttl": 3600,  # 1 hour
        },
    }

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_file: Optional path to configuration file
        """
        self.config = self.DEFAULTS.copy()
        self.config_file = config_file

        if config_file and os.path.exists(config_file):
            self._load_config_file(config_file)

        # Load environment variables
        self._load_environment_variables()

    def _load_config_file(self, config_file: str):
        """Load configuration from file."""
        try:
            import yaml

            with open(config_file, "r") as f:
                file_config = yaml.safe_load(f) or {}
                self._merge_config(file_config)
            print(f"✅ Loaded configuration from: {config_file}")
        except Exception as e:
            print(f"⚠️  Failed to load config file {config_file}: {e}")

    def _load_environment_variables(self):
        """Load configuration from environment variables."""
        env_mappings = {
            # Docker settings
            "RETICULUM_DOCKER_TIMEOUT": ("docker", "timeout", int),
            "RETICULUM_DOCKER_MAX_RETRIES": ("docker", "max_retries", int),
            "RETICULUM_DOCKER_MEMORY_LIMIT": ("docker", "memory_limit", str),
            "RETICULUM_DOCKER_CPU_LIMIT": ("docker", "cpu_limit", str),
            # Tool settings
            "RETICULUM_TRIVY_IMAGE": ("tools", "trivy", "image", str),
            "RETICULUM_TRIVY_SEVERITY": ("tools", "trivy", "severity_levels", str),
            "RETICULUM_SEMGREP_IMAGE": ("tools", "semgrep", "image", str),
            "RETICULUM_SEMGREP_CONFIG": ("tools", "semgrep", "config", str),
            # Scanner settings
            "RETICULUM_PARALLEL_EXECUTION": ("scanner", "parallel_execution", bool),
            "RETICULUM_ENABLE_TRIVY": ("scanner", "enable_trivy", bool),
            "RETICULUM_ENABLE_SEMGREP": ("scanner", "enable_semgrep", bool),
            # Performance settings
            "RETICULUM_MAX_WORKERS": ("performance", "max_workers", int),
            "RETICULUM_CACHE_RESULTS": ("performance", "cache_results", bool),
            "RETICULUM_CACHE_TTL": ("performance", "cache_ttl", int),
        }

        for env_var, (section, *keys, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    if converter == bool:
                        value = value.lower() in ("true", "1", "yes", "on")
                    else:
                        value = converter(value)
                    self._set_nested_value(self.config, [section] + list(keys), value)
                except (ValueError, TypeError) as e:
                    print(f"⚠️  Invalid environment variable {env_var}: {e}")

    def _merge_config(self, new_config: Dict[str, Any]):
        """Recursively merge configuration dictionaries."""
        for key, value in new_config.items():
            if (
                key in self.config
                and isinstance(self.config[key], dict)
                and isinstance(value, dict)
            ):
                self._merge_config_section(self.config[key], value)
            else:
                self.config[key] = value

    def _merge_config_section(self, base: Dict[str, Any], updates: Dict[str, Any]):
        """Merge a configuration section."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config_section(base[key], value)
            else:
                base[key] = value

    def _set_nested_value(self, config_dict: Dict[str, Any], keys: list, value: Any):
        """Set a nested value in configuration dictionary."""
        current = config_dict
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated path.

        Args:
            key_path: Dot-separated path to configuration value
            default: Default value if path not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split(".")
        current = self.config

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default

    def get_docker_config(self) -> Dict[str, Any]:
        """Get Docker configuration."""
        return self.get("docker", {})

    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """Get configuration for a specific security tool."""
        return self.get(f"tools.{tool_name}", {})

    def get_scanner_config(self) -> Dict[str, Any]:
        """Get scanner behavior configuration."""
        return self.get("scanner", {})

    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration."""
        return self.get("performance", {})

    def validate(self) -> bool:
        """Validate configuration settings."""
        try:
            # Validate Docker settings
            docker_config = self.get_docker_config()
            assert docker_config["timeout"] > 0, "Docker timeout must be positive"
            assert docker_config["max_retries"] >= 0, "Max retries must be non-negative"

            # Validate scanner settings
            scanner_config = self.get_scanner_config()
            assert isinstance(
                scanner_config["parallel_execution"], bool
            ), "Parallel execution must be boolean"

            return True
        except (AssertionError, KeyError) as e:
            print(f"❌ Configuration validation failed: {e}")
            return False

    def save(self, config_file: str):
        """Save configuration to file."""
        try:
            import yaml

            with open(config_file, "w") as f:
                yaml.dump(self.config, f, default_flow_style=False)
            print(f"✅ Configuration saved to: {config_file}")
        except Exception as e:
            print(f"❌ Failed to save configuration: {e}")

    def __str__(self) -> str:
        """String representation of configuration."""
        import json

        return json.dumps(self.config, indent=2)
