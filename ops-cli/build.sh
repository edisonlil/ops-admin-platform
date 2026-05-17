#!/bin/bash
# Build ops-cli executable for Linux/Mac
# Requires: pip install pyinstaller

echo "Building ops-cli..."

cd "$(dirname "$0")"

# Install build dependencies
pip install pyinstaller paramiko cryptography pyyaml jinja2 packaging -q

# Build
pyinstaller ops-cli.spec --clean

echo ""
echo "Build complete! Executable is in:"
echo "  dist/ops-cli"
echo ""
echo "To distribute:"
echo "  1. Copy dist/ops-cli to target machine"
echo "  2. User needs only to run it (no Python required)"
echo "  3. On Linux: chmod +x ops-cli"