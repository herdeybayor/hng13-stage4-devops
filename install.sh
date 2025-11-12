#!/bin/bash

# Installation script for VPC Control
# This installs vpcctl system-wide so you can run it from anywhere

set -e

echo "=========================================="
echo "Installing VPC Control"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Installation directories
INSTALL_DIR="/opt/vpcctl"
BIN_LINK="/usr/local/bin/vpcctl"

# Create installation directory
echo "Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/lib"
mkdir -p "$INSTALL_DIR/policies"

# Copy files
echo "Copying vpcctl..."
cp vpcctl "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/vpcctl"

echo "Copying library modules..."
cp lib/*.py "$INSTALL_DIR/lib/"

echo "Copying policy examples..."
cp policies/*.json "$INSTALL_DIR/policies/"

echo "Copying helper scripts..."
cp cleanup.sh "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/cleanup.sh"

# Create symlink
echo "Creating symlink in /usr/local/bin..."
ln -sf "$INSTALL_DIR/vpcctl" "$BIN_LINK"

# Create required directories
echo "Creating state and log directories..."
mkdir -p /var/lib/vpcctl
mkdir -p /var/log/vpcctl

echo ""
echo "=========================================="
echo "✓ Installation Complete!"
echo "=========================================="
echo ""
echo "Installation details:"
echo "  Installation directory: $INSTALL_DIR"
echo "  Command location: $BIN_LINK"
echo "  State directory: /var/lib/vpcctl"
echo "  Log directory: /var/log/vpcctl"
echo ""
echo "Usage:"
echo "  vpcctl --help"
echo "  vpcctl create-vpc --name my-vpc --cidr 10.0.0.0/16"
echo ""
echo "Note: You can now run 'vpcctl' from anywhere!"
echo ""

