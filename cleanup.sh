#!/bin/bash

# cleanup.sh - Clean up all VPC resources
# This script removes all VPCs, namespaces, bridges, and firewall rules

set -e

echo "=========================================="
echo "VPC Cleanup Script"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Use vpcctl to clean up if available
if [ -x "./vpcctl" ]; then
    echo "Using vpcctl to clean up..."
    ./vpcctl cleanup-all
else
    echo "vpcctl not found, performing manual cleanup..."
    
    # Clean up namespaces
    echo "Cleaning up network namespaces..."
    for ns in $(ip netns list | grep "ns-" | awk '{print $1}'); do
        echo "  Deleting namespace: $ns"
        ip netns delete "$ns" 2>/dev/null || true
    done
    
    # Clean up bridges
    echo "Cleaning up bridges..."
    for br in $(ip link show type bridge | grep "br-" | awk -F: '{print $2}' | tr -d ' '); do
        echo "  Deleting bridge: $br"
        ip link set "$br" down 2>/dev/null || true
        ip link delete "$br" 2>/dev/null || true
    done
    
    # Clean up veth pairs
    echo "Cleaning up veth interfaces..."
    for veth in $(ip link show | grep "veth-" | awk -F: '{print $2}' | tr -d ' '); do
        echo "  Deleting veth: $veth"
        ip link delete "$veth" 2>/dev/null || true
    done
    
    for peer in $(ip link show | grep "peer-" | awk -F: '{print $2}' | tr -d ' '); do
        echo "  Deleting peer: $peer"
        ip link delete "$peer" 2>/dev/null || true
    done
    
    # Clean up iptables NAT rules
    echo "Cleaning up iptables NAT rules..."
    iptables -t nat -F POSTROUTING 2>/dev/null || true
    iptables -F FORWARD 2>/dev/null || true
    
    # Remove state file
    echo "Removing state file..."
    rm -f /var/lib/vpcctl/state.json
    
    echo ""
    echo "✓ Manual cleanup completed"
fi

echo ""
echo "=========================================="
echo "Cleanup Summary"
echo "=========================================="
echo "Remaining namespaces: $(ip netns list | wc -l)"
echo "Remaining bridges: $(ip link show type bridge | grep -c "br-" || echo 0)"
echo ""
echo "✓ Cleanup complete!"

