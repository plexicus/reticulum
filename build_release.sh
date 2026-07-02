#!/bin/bash
set -e

# Local release build. CI releases (multi-platform) are produced by
# .github/workflows/release.yml on tag push; this script packages a tarball
# for the HOST platform only.

VERSION="v$(grep -m1 '^version' Cargo.toml | cut -d'"' -f2)"
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64) ARCH="amd64" ;;
  arm64|aarch64) ARCH="arm64" ;;
esac

DIST_DIR="dist"
PKG="reticulum-${VERSION}-${OS}-${ARCH}"
ARCHIVE_NAME="${PKG}.tar.gz"

echo "[*] Building Reticulum Release ${VERSION} (${OS}/${ARCH})..."

# Build binary
cargo build --release

# Prepare distribution directory
rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}/${PKG}/rules"

# Copy assets
cp target/release/reticulum "${DIST_DIR}/${PKG}/"
cp -r rules/* "${DIST_DIR}/${PKG}/rules/"
cp README.md RULES.md LICENSE "${DIST_DIR}/${PKG}/"

# Create archive
echo "[*] Creating archive ${ARCHIVE_NAME}..."
tar -czf "${ARCHIVE_NAME}" -C "${DIST_DIR}" "${PKG}"
shasum -a 256 "${ARCHIVE_NAME}" > "${ARCHIVE_NAME}.sha256"

echo "[+] Release ready: ${ARCHIVE_NAME}"
