"""
Command Line Interface for Reticulum.

Handles argument parsing and CLI-specific logic.
"""

import argparse
import json
import sys
from .main import ExposureScanner


def format_console_output(data: dict, args) -> str:
    """Format output for beautiful console display."""
    if args.paths:
        return _format_paths_console(data)
    else:
        return _format_containers_console(data)


def _format_containers_console(data: dict) -> str:
    """Format container analysis results for console output."""
    output = []

    # Header
    output.append("🔍 Reticulum - Cloud Infrastructure Security Analysis")
    output.append("=" * 60)
    output.append(f"📁 Repository: {data['repo_path']}")
    output.append("")

    # Scan Summary
    summary = data.get("scan_summary", {})
    if summary:
        output.append("📊 Scan Summary")
        output.append("-" * 20)
        output.append(f"   Charts analyzed: {summary.get('charts_analyzed', 0)}")
        output.append(f"   Containers found: {summary.get('containers_found', 0)}")
        output.append(f"   Total exposures: {summary.get('total_exposures', 0)}")
        output.append("")

    # Containers
    containers = data.get("containers", [])
    if containers:
        output.append("🐳 Container Analysis")
        output.append("-" * 20)

        # Group by exposure level
        by_level = {}
        for container in containers:
            level = container.get("exposure_level", "UNKNOWN")
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(container)

        # Display by level (HIGH first, then MEDIUM, then LOW)
        level_order = ["HIGH", "MEDIUM", "LOW"]
        for level in level_order:
            if level in by_level:
                level_containers = by_level[level]
                level_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(level, "⚪")
                output.append(
                    f"   {level_emoji} {level} Exposure ({len(level_containers)} containers)"
                )

                for container in level_containers:
                    name = container.get("name", "Unknown")
                    chart = container.get("chart_name", "Unknown")
                    gateway = container.get("gateway_type", "Unknown")
                    host = container.get("host", "N/A")

                    output.append(f"      • {name}")
                    output.append(f"        Chart: {chart}")
                    output.append(f"        Gateway: {gateway}")
                    if host != "N/A":
                        output.append(f"        Host: {host}")
                    output.append("")

        output.append("")

    # Network Topology
    topology = data.get("network_topology", {})
    if topology:
        output.append("🌐 Network Topology")
        output.append("-" * 20)
        for gateway_type, hosts in topology.items():
            if hosts:
                output.append(f"   {gateway_type}:")
                for host in hosts:
                    output.append(f"     • {host}")
                output.append("")

    # Mermaid Diagram
    mermaid = data.get("mermaid_diagram", "")
    if mermaid:
        output.append("📋 Mermaid Diagram")
        output.append("-" * 20)
        output.append("   (Use --json to see the full diagram)")
        output.append("")

    return "\n".join(output)


def _format_paths_console(data: dict) -> str:
    """Format paths analysis results for console output."""
    output = []

    # Header
    output.append("🔍 Reticulum - Source Code Path Analysis")
    output.append("=" * 60)
    output.append(f"📁 Repository: {data['repo_path']}")
    output.append("")

    # Scan Summary
    summary = data.get("scan_summary", {})
    if summary:
        output.append("📊 Scan Summary")
        output.append("-" * 20)
        output.append(f"   Charts analyzed: {summary.get('charts_analyzed', 0)}")
        output.append(f"   Dockerfiles found: {summary.get('dockerfiles_found', 0)}")
        output.append("")

    # Master Paths
    master_paths = data.get("master_paths", [])
    if master_paths:
        output.append("🛤️  Source Code Paths")
        output.append("-" * 20)
        for i, path in enumerate(master_paths, 1):
            output.append(f"   {i}. {path}")
        output.append("")

    return "\n".join(output)


def format_json_output(data: dict, args) -> str:
    """Format JSON output - always pretty formatted like jq."""
    if args.json:
        return json.dumps(data, indent=2, sort_keys=True)
    else:
        return json.dumps(data)


def create_parser():
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="reticulum",
        description="Reticulum - Exposure Scanner for Cloud Infrastructure Security Analysis",
        epilog="""
Examples:
  reticulum /path/to/repo                 # Container exposure analysis
  reticulum /path/to/repo --paths         # Source code path analysis
  reticulum /path/to/repo --json          # Pretty JSON output (formatted like jq)
  reticulum /path/to/repo --console      # Beautiful console output
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "repository_path",
        help="Path to the repository containing Helm charts to analyze",
    )

    parser.add_argument(
        "--paths",
        action="store_true",
        help="Enable paths analysis mode (default: container analysis mode)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Pretty print JSON output (always formatted like jq)",
    )

    parser.add_argument(
        "--console",
        action="store_true",
        help="Display beautiful formatted output in console",
    )

    parser.add_argument("--version", action="version", version="%(prog)s 4.1.0")

    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        scanner = ExposureScanner()
        results = scanner.scan_repo(args.repository_path)

        # Filter output based on mode
        if args.paths:
            # Paths mode: only master_paths and basic info
            filtered_results = {
                "repo_path": results["repo_path"],
                "scan_summary": results["scan_summary"],
                "master_paths": results["master_paths"],
            }
        else:
            # Default mode: containers and topology (no master_paths)
            filtered_results = {
                "repo_path": results["repo_path"],
                "scan_summary": results["scan_summary"],
                "containers": results["containers"],
                "network_topology": results["network_topology"],
                "mermaid_diagram": results["mermaid_diagram"],
            }

        # Output based on flags
        if args.console and not args.json:
            # Beautiful console output
            print(format_console_output(filtered_results, args))
        else:
            # JSON output (with enhanced formatting options)
            print(format_json_output(filtered_results, args))

    except Exception as e:
        error_result = {
            "error": str(e),
            "repo_path": args.repository_path,
            "scan_summary": {},
        }

        # Add appropriate empty structures based on mode
        if args.paths:
            error_result["master_paths"] = {}
        else:
            error_result.update(
                {"containers": [], "network_topology": {}, "mermaid_diagram": ""}
            )

        # Output error based on flags
        if args.console and not args.json:
            # Beautiful error output
            output = []
            output.append("❌ Error during analysis")
            output.append("=" * 30)
            output.append(f"Repository: {args.repository_path}")
            output.append(f"Error: {str(e)}")
            print("\n".join(output))
        else:
            # Error JSON output
            print(format_json_output(error_result, args))
        sys.exit(1)


if __name__ == "__main__":
    main()
