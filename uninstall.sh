#!/bin/bash

# Uninstallation script for VPC Control

set -e

echo "=========================================="
echo "Uninstalling VPC Control"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

INSTALL_DIR="/opt/vpcctl"
BIN_LINK="/usr/local/bin/vpcctl"

# Clean up VPC resources first
if [ -x "$INSTALL_DIR/vpcctl" ]; then
    echo "Cleaning up VPC resources..."
    "$INSTALL_DIR/vpcctl" cleanup-all 2>/dev/null || true
fi

# Remove symlink
if [ -L "$BIN_LINK" ]; then
    echo "Removing symlink: $BIN_LINK"
    rm -f "$BIN_LINK"
fi

# Remove installation directory
if [ -d "$INSTALL_DIR" ]; then
    echo "Removing installation directory: $INSTALL_DIR"
    rm -rf "$INSTALL_DIR"
fi

# Optionally remove state and logs
echo ""
read -p "Remove state and log files? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing state directory..."
    rm -rf /var/lib/vpcctl
    echo "Removing log directory..."
    rm -rf /var/log/vpcctl
fi

echo ""
echo "✓ Uninstallation complete!"
echo ""

