#!/bin/bash
set -euo pipefail

# Check for required tools
if ! command -v trivy &> /dev/null; then
    echo "Error: trivy is not installed."
    exit 1
fi

if ! command -v semgrep &> /dev/null; then
    echo "Error: semgrep is not installed."
    exit 1
fi


if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <monorepo-directory>"
    exit 1
fi

BASE_DIR="$1"

if [ ! -d "$BASE_DIR" ]; then
    echo "Error: Directory $BASE_DIR does not exist."
    exit 1
fi

echo "[*] Running Trivy on $BASE_DIR..."
trivy fs "$BASE_DIR" --format sarif --output "$BASE_DIR/trivy.sarif" --severity CRITICAL,HIGH,MEDIUM,LOW

echo "[*] Running Semgrep on $BASE_DIR..."
# Find all source files explicitly to avoid git tracking issues
SEMGREP_FILES=$(find "$BASE_DIR" -type f \( -name "*.js" -o -name "*.py" -o -name "*.rb" -o -name "*.go" -o -name "*.java" \) ! -path "*/node_modules/*" ! -path "*/.git/*" ! -path "*/vendor/*")

if [ -n "$SEMGREP_FILES" ]; then
    semgrep scan $SEMGREP_FILES --config=p/security-audit --sarif --output "$BASE_DIR/semgrep.sarif" --disable-version-check --no-git-ignore
else
    echo "[!] No source files found for Semgrep scanning"
    # Create empty SARIF file
    echo '{"version":"2.1.0","$schema":"https://json.schemastore.org/sarif-2.1.0.json","runs":[{"tool":{"driver":{"name":"Semgrep","version":"1.0.0"}},"results":[]}]}' > "$BASE_DIR/semgrep.sarif"
fi

echo "[+] Scans complete. SARIF files generated in $BASE_DIR"