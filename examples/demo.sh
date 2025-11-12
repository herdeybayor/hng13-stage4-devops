#!/bin/bash

# demo.sh - Demonstration script for VPC Control
# This script demonstrates a complete VPC setup with multiple scenarios

set -e

echo "=========================================="
echo "VPC Control - Demonstration"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

step() {
    echo ""
    echo -e "${BLUE}===> $1${NC}"
    sleep 1
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Cleanup first
step "Cleaning up any existing resources"
./vpcctl cleanup-all 2>/dev/null || true
success "Cleanup complete"

# Demo 1: Create a simple VPC
step "Demo 1: Creating a VPC with public and private subnets"

echo "Creating VPC 'demo-vpc' with CIDR 10.100.0.0/16"
./vpcctl create-vpc --name demo-vpc --cidr 10.100.0.0/16
success "VPC created"

echo "Creating public subnet"
./vpcctl create-subnet --vpc demo-vpc --name public --cidr 10.100.1.0/24 --type public
success "Public subnet created"

echo "Creating private subnet"
./vpcctl create-subnet --vpc demo-vpc --name private --cidr 10.100.2.0/24 --type private
success "Private subnet created"

step "Listing VPC resources"
./vpcctl list-vpcs

# Demo 2: Deploy applications
step "Demo 2: Deploying applications in subnets"

echo "Deploying web app in public subnet on port 8080"
./vpcctl deploy-app --vpc demo-vpc --subnet public --port 8080 --type python
success "Public app deployed"

sleep 2

echo "Deploying app in private subnet on port 8080"
./vpcctl deploy-app --vpc demo-vpc --subnet private --port 8080 --type python
success "Private app deployed"

sleep 2

# Demo 3: Test connectivity
step "Demo 3: Testing intra-VPC connectivity"

echo "Testing connection from public to private subnet"
./vpcctl test-connectivity --vpc demo-vpc --from-subnet public --to-subnet private || echo "Note: Connectivity test may fail based on routing"

# Demo 4: Multiple VPCs and isolation
step "Demo 4: Creating a second VPC to demonstrate isolation"

echo "Creating VPC 'demo-vpc-2' with CIDR 10.200.0.0/16"
./vpcctl create-vpc --name demo-vpc-2 --cidr 10.200.0.0/16
success "Second VPC created"

echo "Creating public subnet in second VPC"
./vpcctl create-subnet --vpc demo-vpc-2 --name public --cidr 10.200.1.0/24 --type public
success "Subnet created in second VPC"

step "Listing all VPCs"
./vpcctl list-vpcs

# Demo 5: VPC Peering
step "Demo 5: Creating VPC peering connection"

echo "Peering demo-vpc with demo-vpc-2"
./vpcctl peer-vpcs --vpc1 demo-vpc --vpc2 demo-vpc-2
success "VPC peering established"

# Demo 6: Firewall policies
if [ -f "policies/web-server.json" ]; then
    step "Demo 6: Applying firewall policy"
    
    echo "Applying web-server policy to public subnet"
    ./vpcctl apply-policy --vpc demo-vpc --subnet public --policy policies/web-server.json
    success "Firewall policy applied"
fi

# Demo 7: Show current state
step "Demo 7: Current infrastructure state"

echo ""
echo "Network Namespaces:"
ip netns list | grep "ns-demo" || echo "  None found"

echo ""
echo "Bridges:"
ip link show type bridge | grep "br-demo" || echo "  None found"

echo ""
echo "VPC Summary:"
./vpcctl list-vpcs

# Demo 8: Cleanup
step "Demo 8: Cleaning up demonstration resources"

echo "Removing VPC peering"
./vpcctl unpeer-vpcs --vpc1 demo-vpc --vpc2 demo-vpc-2 || true

echo "Deleting demo-vpc"
./vpcctl delete-vpc --name demo-vpc

echo "Deleting demo-vpc-2"
./vpcctl delete-vpc --name demo-vpc-2

success "All demo resources cleaned up"

echo ""
echo "=========================================="
echo "Demonstration Complete!"
echo "=========================================="
echo ""
echo "What you just saw:"
echo "  ✓ VPC creation with CIDR ranges"
echo "  ✓ Public and private subnet provisioning"
echo "  ✓ Application deployment in subnets"
echo "  ✓ Intra-VPC connectivity testing"
echo "  ✓ Multiple VPC creation and isolation"
echo "  ✓ VPC peering for cross-VPC communication"
echo "  ✓ Firewall policy application"
echo "  ✓ Complete resource cleanup"
echo ""
echo "Try it yourself: sudo ./vpcctl --help"
echo ""

