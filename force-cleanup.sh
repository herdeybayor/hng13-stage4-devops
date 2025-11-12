#!/bin/bash

# Force cleanup script - removes all VPC resources

echo "Force cleaning VPC resources..."

# Remove state file
sudo rm -f /var/lib/vpcctl/state.json
echo "✓ Removed state file"

# Kill all Python processes in namespaces
sudo pkill -9 python3 2>/dev/null || true

# Delete all namespaces starting with ns-
for ns in $(ip netns list 2>/dev/null | grep "ns-" | awk '{print $1}'); do
    echo "Deleting namespace: $ns"
    sudo ip netns delete "$ns" 2>/dev/null || true
done

# Delete all bridges starting with br-
for br in $(ip link show type bridge 2>/dev/null | grep "br-" | awk -F: '{print $2}' | awk '{print $1}'); do
    echo "Deleting bridge: $br"
    sudo ip link set "$br" down 2>/dev/null || true
    sudo ip link delete "$br" 2>/dev/null || true
done

# Delete all veth interfaces
for veth in $(ip link show 2>/dev/null | grep "veth-" | awk -F: '{print $2}' | awk '{print $1}'); do
    echo "Deleting veth: $veth"
    sudo ip link delete "$veth" 2>/dev/null || true
done

# Delete all peer interfaces
for peer in $(ip link show 2>/dev/null | grep -E "peer[12]-" | awk -F: '{print $2}' | awk '{print $1}'); do
    echo "Deleting peer: $peer"
    sudo ip link delete "$peer" 2>/dev/null || true
done

# Flush iptables NAT rules
echo "Flushing iptables NAT rules..."
sudo iptables -t nat -F POSTROUTING 2>/dev/null || true
sudo iptables -F FORWARD 2>/dev/null || true

echo ""
echo "✓ Force cleanup complete!"
echo ""
echo "Verification:"
echo "Namespaces: $(ip netns list | wc -l)"
echo "Bridges: $(ip link show type bridge 2>/dev/null | grep -c 'br-' || echo 0)"

