"""
Command Line Interface for Reticulum.

Handles argument parsing and CLI-specific logic.
"""

import argparse
import json
import sys
from .main import ExposureScanner
from .security_scanner import SecurityScanner


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
        description="Reticulum - Cloud Infrastructure Security Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", metavar="COMMAND"
    )

    # Original scan command
    scan_parser = subparsers.add_parser(
        "scan",
        help="Run exposure analysis on repository",
        description="Analyze Helm charts and generate exposure-based prioritization report",
        epilog="""
Examples:
  reticulum scan /path/to/repo                 # Generate prioritization report
  reticulum scan /path/to/repo --json          # Pretty JSON output (formatted like jq)
  reticulum scan /path/to/repo --dot diagram.dot  # Export network topology as DOT file
        """,
    )

    scan_parser.add_argument(
        "repository_path",
        help="Path to the repository containing Helm charts to analyze",
    )

    scan_parser.add_argument(
        "--json",
        action="store_true",
        help="Pretty print JSON output (always formatted like jq)",
    )

    scan_parser.add_argument(
        "--dot",
        metavar="FILE",
        help="Export network topology as Graphviz DOT file",
    )

    # Security scan command
    security_parser = subparsers.add_parser(
        "security-scan",
        help="Run integrated security scan with Trivy and Semgrep",
        description="Run comprehensive security scan with Trivy SCA, Semgrep SAST, and exposure analysis",
        epilog="""
Examples:
  reticulum security-scan /path/to/repo                    # Run complete security scan
  reticulum security-scan /path/to/repo --output results.sarif  # Save SARIF report
        """,
    )

    security_parser.add_argument(
        "repository_path",
        help="Path to the repository to scan",
    )

    security_parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="Save enhanced SARIF report to file",
    )

    parser.add_argument("--version", action="version", version="%(prog)s 0.6.9")

    return parser


def handle_scan_command(args):
    """Handle the original scan command."""
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


def handle_security_scan_command(args):
    """Handle the security-scan command."""
    try:
        scanner = SecurityScanner()
        results = scanner.security_scan(args.repository_path, args.output)

        if not results.get("success", True):
            print(f"\n❌ Security scan failed: {results.get('error', 'Unknown error')}")
            if results.get("tool_error"):
                print(f"   Tool error: {results.get('tool_error')}")
            sys.exit(1)

        # Print final results summary
        print("\n" + "=" * 50)
        print("✅ Security scan completed successfully!")

    except Exception as e:
        print(f"\n❌ Security scan failed: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "scan":
        handle_scan_command(args)
    elif args.command == "security-scan":
        handle_security_scan_command(args)


if __name__ == "__main__":
    main()
