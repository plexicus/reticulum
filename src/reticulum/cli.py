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
        description="Reticulum - Prioritization Report Generator for Cloud Infrastructure Security Analysis",
        epilog="""
Examples:
  reticulum /path/to/repo                 # Generate prioritization report
  reticulum /path/to/repo --json          # Pretty JSON output (formatted like jq)
  reticulum /path/to/repo --dot diagram.dot  # Export network topology as DOT file
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "repository_path",
        help="Path to the repository containing Helm charts to analyze",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Pretty print JSON output (always formatted like jq)",
    )

    parser.add_argument(
        "--dot",
        metavar="FILE",
        help="Export network topology as Graphviz DOT file",
    )

    parser.add_argument("--version", action="version", version="%(prog)s 0.4.6")

    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        scanner = ExposureScanner()
        results = scanner.scan_repo(args.repository_path)

        # Handle DOT file export if requested
        if args.dot:
            from .dot_builder import DOTBuilder

            dot_builder = DOTBuilder()
            dot_builder.save_dot_file(results["containers"], args.dot)

        # Always return prioritization report
        filtered_results = results["prioritization_report"]

        # Output based on flags
        print(format_json_output(filtered_results, args))

    except Exception as e:
        error_result = {
            "repo_path": args.repository_path,
            "scan_timestamp": "",
            "summary": {
                "total_services": 0,
                "high_risk": 0,
                "medium_risk": 0,
                "low_risk": 0,
            },
            "prioritized_services": [],
            "error": str(e),
        }

        # Error JSON output
        print(format_json_output(error_result, args))
        sys.exit(1)


if __name__ == "__main__":
    main()
