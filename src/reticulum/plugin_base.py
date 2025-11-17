"""
Plugin Base Classes for Reticulum Security Scanner.

Provides abstract base classes for creating custom security tools
and processing plugins that can extend the scanner's capabilities.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class SecurityToolPlugin(ABC):
    """Base class for security tool plugins."""

    @abstractmethod
    def scan(self, repo_path: str, output_file: str) -> Dict[str, Any]:
        """
        Perform security scan on repository.

        Args:
            repo_path: Path to repository to scan
            output_file: Path to save results

        Returns:
            Dictionary with scan results and metadata
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this security tool."""
        pass

    @abstractmethod
    def get_version(self) -> str:
        """Get the version of this security tool."""
        pass

    def get_supported_formats(self) -> List[str]:
        """Get supported output formats (e.g., 'sarif', 'json')."""
        return ["sarif"]


class ProcessingPlugin(ABC):
    """Base class for processing plugins that modify scan results."""

    @abstractmethod
    def process(self, scan_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process scan results.

        Args:
            scan_results: Dictionary containing scan results

        Returns:
            Modified scan results
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this processing plugin."""
        pass

    def get_description(self) -> str:
        """Get description of what this plugin does."""
        return ""


class PluginManager:
    """Manages security tool and processing plugins."""

    def __init__(self):
        self.security_tools: Dict[str, SecurityToolPlugin] = {}
        self.processors: Dict[str, ProcessingPlugin] = {}

    def register_security_tool(self, tool: SecurityToolPlugin):
        """Register a security tool plugin."""
        name = tool.get_name()
        if name in self.security_tools:
            print(f"⚠️  Security tool '{name}' already registered, overwriting")
        self.security_tools[name] = tool
        print(f"✅ Registered security tool: {name}")

    def register_processor(self, processor: ProcessingPlugin):
        """Register a processing plugin."""
        name = processor.get_name()
        if name in self.processors:
            print(f"⚠️  Processor '{name}' already registered, overwriting")
        self.processors[name] = processor
        print(f"✅ Registered processor: {name}")

    def run_security_tool(
        self, tool_name: str, repo_path: str, output_file: str
    ) -> Dict[str, Any]:
        """Run a registered security tool."""
        if tool_name not in self.security_tools:
            raise ValueError(f"Security tool '{tool_name}' not found")

        tool = self.security_tools[tool_name]
        print(f"🔍 Running {tool_name} scan...")
        return tool.scan(repo_path, output_file)

    def process_results(self, scan_results: Dict[str, Any]) -> Dict[str, Any]:
        """Run all registered processors on scan results."""
        processed_results = scan_results.copy()

        for name, processor in self.processors.items():
            print(f"🔄 Applying processor: {name}")
            processed_results = processor.process(processed_results)

        return processed_results

    def get_available_tools(self) -> List[str]:
        """Get list of available security tool names."""
        return list(self.security_tools.keys())

    def get_available_processors(self) -> List[str]:
        """Get list of available processor names."""
        return list(self.processors.keys())
