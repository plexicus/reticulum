"""
Mermaid Diagram Builder Module for Reticulum.

Handles the generation of Mermaid diagrams for network topology visualization.
"""

from typing import Dict, List, Any


class MermaidBuilder:
    """Builds Mermaid diagrams for network topology visualization."""

    def build_diagram(self, containers: List[Dict[str, Any]]) -> str:
        """Build Mermaid diagram string."""
        if not containers:
            return "graph TD\n    Internet[Internet]\n    No_Containers[No containers found]"

        mermaid_lines = ["graph TD"]

        # Add internet node
        mermaid_lines.append("    Internet[Internet]")

        # Group containers by exposure level
        high_containers = [c for c in containers if c["exposure_level"] == "HIGH"]
        medium_containers = [c for c in containers if c["exposure_level"] == "MEDIUM"]
        low_containers = [c for c in containers if c["exposure_level"] == "LOW"]

        # Add high exposure containers (direct internet access)
        for container in high_containers:
            node_name = container["name"].replace("-", "_").replace(" ", "_")
            mermaid_lines.append(f"    {node_name}[{container['name']}]")
            mermaid_lines.append(f"    Internet --> {node_name}")

        # Add medium exposure containers (linked through exposed containers)
        for container in medium_containers:
            node_name = container["name"].replace("-", "_").replace(" ", "_")
            mermaid_lines.append(f"    {node_name}[{container['name']}]")
            # Link to exposed containers
            for exposed_by in container.get("exposed_by", []):
                exposed_node = exposed_by.replace("-", "_").replace(" ", "_")
                mermaid_lines.append(f"    {exposed_node} --> {node_name}")

        # Add low exposure containers (internal only)
        for container in low_containers:
            node_name = container["name"].replace("-", "_").replace(" ", "_")
            mermaid_lines.append(f"    {node_name}[{container['name']}]")

        # Add subgraph for better organization
        if high_containers or medium_containers or low_containers:
            mermaid_lines.append("")
            mermaid_lines.append("    subgraph Exposure_Levels")
            if high_containers:
                mermaid_lines.append("        subgraph High_Exposure")
                for container in high_containers:
                    node_name = container["name"].replace("-", "_").replace(" ", "_")
                    mermaid_lines.append(f"            {node_name}")
                mermaid_lines.append("        end")

            if medium_containers:
                mermaid_lines.append("        subgraph Medium_Exposure")
                for container in medium_containers:
                    node_name = container["name"].replace("-", "_").replace(" ", "_")
                    mermaid_lines.append(f"            {node_name}")
                mermaid_lines.append("        end")

            if low_containers:
                mermaid_lines.append("        subgraph Low_Exposure")
                for container in low_containers:
                    node_name = container["name"].replace("-", "_").replace(" ", "_")
                    mermaid_lines.append(f"            {node_name}")
                mermaid_lines.append("        end")
            mermaid_lines.append("    end")

        return "\n".join(mermaid_lines)
