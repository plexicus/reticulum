"""
DOT Diagram Builder Module for Reticulum.

Handles the generation of Graphviz DOT diagrams for network topology visualization.
"""

from typing import Dict, List, Any


class DOTBuilder:
    """Builds Graphviz DOT diagrams for network topology visualization."""

    def build_diagram(self, containers: List[Dict[str, Any]]) -> str:
        """Build DOT diagram string."""
        if not containers:
            return 'digraph G {\n    label="No containers found";\n}'

        dot_lines = ["digraph G {"]

        # Graph attributes
        dot_lines.append('    rankdir="LR";')
        dot_lines.append('    node [shape=box, style=filled, fontname="Arial"];')
        dot_lines.append('    edge [fontname="Arial", fontsize=10];')
        dot_lines.append("")

        # Add internet node
        dot_lines.append(
            '    Internet [label="Internet", shape=ellipse, fillcolor="#ff6b6b"];'
        )

        # Group containers by exposure level
        high_containers = [c for c in containers if c["exposure_level"] == "HIGH"]
        medium_containers = [c for c in containers if c["exposure_level"] == "MEDIUM"]
        low_containers = [c for c in containers if c["exposure_level"] == "LOW"]

        # Define color schemes for different exposure levels
        high_color = "#ff6b6b"  # Red for high exposure
        medium_color = "#ffd166"  # Yellow for medium exposure
        low_color = "#06d6a0"  # Green for low exposure

        # Add high exposure containers (direct internet access)
        for container in high_containers:
            node_name = self._sanitize_node_name(container["name"])
            label = f"{container['name']}\n({container['gateway_type']})"
            dot_lines.append(
                f'    {node_name} [label="{label}", fillcolor="{high_color}"];'
            )
            dot_lines.append(f'    Internet -> {node_name} [label="direct"];')

        # Add medium exposure containers (linked through exposed containers)
        for container in medium_containers:
            node_name = self._sanitize_node_name(container["name"])
            label = f"{container['name']}\n(linked)"
            dot_lines.append(
                f'    {node_name} [label="{label}", fillcolor="{medium_color}"];'
            )
            # Link to exposed containers
            for exposed_by in container.get("exposed_by", []):
                exposed_node = self._sanitize_node_name(exposed_by)
                dot_lines.append(
                    f'    {exposed_node} -> {node_name} [label="dependency"];'
                )

        # Add low exposure containers (internal only)
        for container in low_containers:
            node_name = self._sanitize_node_name(container["name"])
            label = f"{container['name']}\n(internal)"
            dot_lines.append(
                f'    {node_name} [label="{label}", fillcolor="{low_color}"];'
            )

        # Add subgraphs for better organization
        if high_containers:
            dot_lines.append("")
            dot_lines.append("    subgraph cluster_high {")
            dot_lines.append('        label="High Exposure (Internet Access)";')
            dot_lines.append("        style=filled;")
            dot_lines.append('        fillcolor="#fff5f5";')
            for container in high_containers:
                node_name = self._sanitize_node_name(container["name"])
                dot_lines.append(f"        {node_name};")
            dot_lines.append("    }")

        if medium_containers:
            dot_lines.append("")
            dot_lines.append("    subgraph cluster_medium {")
            dot_lines.append('        label="Medium Exposure (Linked)";')
            dot_lines.append("        style=filled;")
            dot_lines.append('        fillcolor="#fffaf0";')
            for container in medium_containers:
                node_name = self._sanitize_node_name(container["name"])
                dot_lines.append(f"        {node_name};")
            dot_lines.append("    }")

        if low_containers:
            dot_lines.append("")
            dot_lines.append("    subgraph cluster_low {")
            dot_lines.append('        label="Low Exposure (Internal)";')
            dot_lines.append("        style=filled;")
            dot_lines.append('        fillcolor="#f0fff4";')
            for container in low_containers:
                node_name = self._sanitize_node_name(container["name"])
                dot_lines.append(f"        {node_name};")
            dot_lines.append("    }")

        dot_lines.append("}")

        return "\n".join(dot_lines)

    def _sanitize_node_name(self, name: str) -> str:
        """Sanitize container name for use as DOT node identifier."""
        # Replace problematic characters with underscores
        sanitized = name.replace("-", "_").replace(" ", "_").replace(".", "_")
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = "node_" + sanitized
        return sanitized

    def save_dot_file(self, containers: List[Dict[str, Any]], file_path: str) -> None:
        """Generate and save DOT diagram to file."""
        dot_content = self.build_diagram(containers)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(dot_content)
