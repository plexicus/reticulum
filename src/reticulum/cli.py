"""
Command Line Interface for Reticulum.

Handles argument parsing and CLI-specific logic.
"""

import argparse
import json
import sys
from .main import ExposureScanner


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

    parser.add_argument("--version", action="version", version="%(prog)s 0.3.0")

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

        # Output JSON with enhanced formatting options
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

        # Output error JSON with enhanced formatting options
        print(format_json_output(error_result, args))
        sys.exit(1)


if __name__ == "__main__":
    main()
