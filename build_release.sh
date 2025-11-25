#!/bin/bash
set -e

VERSION="v1.0.0"
DIST_DIR="dist"
ARCHIVE_NAME="reticulum-${VERSION}-linux-amd64.tar.gz"

echo "[*] Building Reticulum Release ${VERSION}..."

# Build binary
dub build --build=release --compiler=ldc2

# Prepare distribution directory
rm -rf ${DIST_DIR}
mkdir -p ${DIST_DIR}/rules

# Copy assets
cp reticulum ${DIST_DIR}/
cp -r rules/* ${DIST_DIR}/rules/
cp README.md ${DIST_DIR}/
cp LICENSE ${DIST_DIR}/

# Create archive
echo "[*] Creating archive ${ARCHIVE_NAME}..."
tar -czf ${ARCHIVE_NAME} -C ${DIST_DIR} .

echo "[+] Release ready: ${ARCHIVE_NAME}"
