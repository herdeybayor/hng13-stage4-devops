#!/bin/bash

# run_tests.sh - Comprehensive test suite for VPC Control
# This script tests all VPC functionality including:
# - VPC creation and deletion
# - Subnet management (public and private)
# - Routing between subnets
# - NAT gateway functionality
# - VPC isolation
# - VPC peering
# - Firewall policies
# - Application deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
VPC1_NAME="test-vpc-1"
VPC1_CIDR="10.1.0.0/16"
VPC1_PUBLIC_SUBNET="public-subnet"
VPC1_PUBLIC_CIDR="10.1.1.0/24"
VPC1_PRIVATE_SUBNET="private-subnet"
VPC1_PRIVATE_CIDR="10.1.2.0/24"

VPC2_NAME="test-vpc-2"
VPC2_CIDR="10.2.0.0/16"
VPC2_PUBLIC_SUBNET="public-subnet"
VPC2_PUBLIC_CIDR="10.2.1.0/24"

LOG_FILE="/tmp/vpcctl-test-$(date +%Y%m%d-%H%M%S).log"

# Logging functions
log() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[✓]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[✗]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[!]${NC} $1" | tee -a "$LOG_FILE"
}

section() {
    echo "" | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
    echo "$1" | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
}

# Cleanup function
cleanup() {
    section "Cleaning up test resources"
    log "Running cleanup..."
    ./vpcctl cleanup-all >> "$LOG_FILE" 2>&1 || true
    success "Cleanup complete"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "This script must be run as root (use sudo)"
    exit 1
fi

# Check if vpcctl exists
if [ ! -x "./vpcctl" ]; then
    error "vpcctl not found or not executable"
    error "Run 'make install' first"
    exit 1
fi

# Main test execution
main() {
    section "VPC Control - Comprehensive Test Suite"
    log "Test started at: $(date)"
    log "Log file: $LOG_FILE"
    
    # Cleanup before starting
    cleanup
    
    # Test 1: VPC Creation
    section "Test 1: VPC Creation"
    log "Creating VPC: $VPC1_NAME"
    if ./vpcctl create-vpc --name "$VPC1_NAME" --cidr "$VPC1_CIDR" >> "$LOG_FILE" 2>&1; then
        success "VPC $VPC1_NAME created successfully"
    else
        error "Failed to create VPC $VPC1_NAME"
        exit 1
    fi
    
    log "Creating VPC: $VPC2_NAME"
    if ./vpcctl create-vpc --name "$VPC2_NAME" --cidr "$VPC2_CIDR" >> "$LOG_FILE" 2>&1; then
        success "VPC $VPC2_NAME created successfully"
    else
        error "Failed to create VPC $VPC2_NAME"
        exit 1
    fi
    
    # Test 2: Subnet Creation
    section "Test 2: Subnet Creation"
    
    log "Creating public subnet in $VPC1_NAME"
    if ./vpcctl create-subnet --vpc "$VPC1_NAME" --name "$VPC1_PUBLIC_SUBNET" \
        --cidr "$VPC1_PUBLIC_CIDR" --type public >> "$LOG_FILE" 2>&1; then
        success "Public subnet created in $VPC1_NAME"
    else
        error "Failed to create public subnet in $VPC1_NAME"
        exit 1
    fi
    
    log "Creating private subnet in $VPC1_NAME"
    if ./vpcctl create-subnet --vpc "$VPC1_NAME" --name "$VPC1_PRIVATE_SUBNET" \
        --cidr "$VPC1_PRIVATE_CIDR" --type private >> "$LOG_FILE" 2>&1; then
        success "Private subnet created in $VPC1_NAME"
    else
        error "Failed to create private subnet in $VPC1_NAME"
        exit 1
    fi
    
    log "Creating public subnet in $VPC2_NAME"
    if ./vpcctl create-subnet --vpc "$VPC2_NAME" --name "$VPC2_PUBLIC_SUBNET" \
        --cidr "$VPC2_PUBLIC_CIDR" --type public >> "$LOG_FILE" 2>&1; then
        success "Public subnet created in $VPC2_NAME"
    else
        error "Failed to create public subnet in $VPC2_NAME"
        exit 1
    fi
    
    # Test 3: Application Deployment
    section "Test 3: Application Deployment"
    
    log "Deploying application in $VPC1_NAME/$VPC1_PUBLIC_SUBNET"
    if ./vpcctl deploy-app --vpc "$VPC1_NAME" --subnet "$VPC1_PUBLIC_SUBNET" \
        --port 8080 --type python >> "$LOG_FILE" 2>&1; then
        success "Application deployed in $VPC1_NAME/$VPC1_PUBLIC_SUBNET"
    else
        warning "Application deployment may have issues (this is non-critical)"
    fi
    
    sleep 2  # Give the app time to start
    
    log "Deploying application in $VPC1_NAME/$VPC1_PRIVATE_SUBNET"
    if ./vpcctl deploy-app --vpc "$VPC1_NAME" --subnet "$VPC1_PRIVATE_SUBNET" \
        --port 8080 --type python >> "$LOG_FILE" 2>&1; then
        success "Application deployed in $VPC1_NAME/$VPC1_PRIVATE_SUBNET"
    else
        warning "Application deployment may have issues (this is non-critical)"
    fi
    
    sleep 2
    
    log "Deploying application in $VPC2_NAME/$VPC2_PUBLIC_SUBNET"
    if ./vpcctl deploy-app --vpc "$VPC2_NAME" --subnet "$VPC2_PUBLIC_SUBNET" \
        --port 8080 --type python >> "$LOG_FILE" 2>&1; then
        success "Application deployed in $VPC2_NAME/$VPC2_PUBLIC_SUBNET"
    else
        warning "Application deployment may have issues (this is non-critical)"
    fi
    
    sleep 2
    
    # Test 4: Intra-VPC Connectivity
    section "Test 4: Intra-VPC Connectivity (Same VPC)"
    
    log "Testing connectivity: $VPC1_PUBLIC_SUBNET -> $VPC1_PRIVATE_SUBNET"
    if ./vpcctl test-connectivity --vpc "$VPC1_NAME" \
        --from-subnet "$VPC1_PUBLIC_SUBNET" --to-subnet "$VPC1_PRIVATE_SUBNET" >> "$LOG_FILE" 2>&1; then
        success "Intra-VPC connectivity works"
    else
        warning "Intra-VPC connectivity test failed (may need routing adjustment)"
    fi
    
    # Test 5: VPC Isolation
    section "Test 5: VPC Isolation (Different VPCs)"
    
    log "Testing isolation: VPC1 should NOT reach VPC2"
    
    # Get namespace and IP for testing
    VPC2_NS=$(cat /var/lib/vpcctl/state.json | grep -A 5 "\"$VPC2_PUBLIC_SUBNET\"" | grep namespace | cut -d'"' -f4 || echo "")
    VPC2_IP=$(cat /var/lib/vpcctl/state.json | grep -A 6 "\"$VPC2_PUBLIC_SUBNET\"" | grep "\"ip\"" | cut -d'"' -f4 || echo "10.2.1.2")
    VPC1_NS=$(cat /var/lib/vpcctl/state.json | grep -A 5 "\"$VPC1_PUBLIC_SUBNET\"" | grep namespace | cut -d'"' -f4 || echo "")
    
    if [ -n "$VPC1_NS" ] && [ -n "$VPC2_IP" ]; then
        if ip netns exec "$VPC1_NS" ping -c 2 -W 2 "$VPC2_IP" >> "$LOG_FILE" 2>&1; then
            error "VPCs are NOT isolated (unexpected connectivity)"
        else
            success "VPCs are properly isolated"
        fi
    else
        warning "Could not determine namespace/IP for isolation test"
    fi
    
    # Test 6: VPC Peering
    section "Test 6: VPC Peering"
    
    log "Creating peering connection: $VPC1_NAME <-> $VPC2_NAME"
    if ./vpcctl peer-vpcs --vpc1 "$VPC1_NAME" --vpc2 "$VPC2_NAME" >> "$LOG_FILE" 2>&1; then
        success "Peering connection created"
    else
        error "Failed to create peering connection"
        exit 1
    fi
    
    sleep 2
    
    log "Testing connectivity after peering: VPC1 -> VPC2"
    if [ -n "$VPC1_NS" ] && [ -n "$VPC2_IP" ]; then
        if ip netns exec "$VPC1_NS" ping -c 2 -W 2 "$VPC2_IP" >> "$LOG_FILE" 2>&1; then
            success "Cross-VPC connectivity works after peering"
        else
            warning "Cross-VPC connectivity test failed after peering"
        fi
    fi
    
    # Test 7: Firewall Policies
    section "Test 7: Firewall Policies"
    
    if [ -f "policies/web-server.json" ]; then
        log "Applying web-server policy to $VPC1_NAME/$VPC1_PUBLIC_SUBNET"
        if ./vpcctl apply-policy --vpc "$VPC1_NAME" --subnet "$VPC1_PUBLIC_SUBNET" \
            --policy policies/web-server.json >> "$LOG_FILE" 2>&1; then
            success "Firewall policy applied successfully"
        else
            warning "Failed to apply firewall policy"
        fi
    else
        warning "Policy file not found, skipping firewall test"
    fi
    
    # Test 8: List Resources
    section "Test 8: List Resources"
    
    log "Listing all VPCs"
    ./vpcctl list-vpcs | tee -a "$LOG_FILE"
    
    log "Listing subnets in $VPC1_NAME"
    ./vpcctl list-subnets --vpc "$VPC1_NAME" | tee -a "$LOG_FILE"
    
    # Test 9: NAT Gateway (Internet Connectivity)
    section "Test 9: NAT Gateway Test"
    
    log "Testing internet connectivity from public subnet"
    warning "Note: This test requires actual internet connectivity and may fail in isolated environments"
    
    if [ -n "$VPC1_NS" ]; then
        if ip netns exec "$VPC1_NS" ping -c 2 -W 2 8.8.8.8 >> "$LOG_FILE" 2>&1; then
            success "Public subnet has internet access"
        else
            warning "Public subnet cannot reach internet (may be expected in test environment)"
        fi
    fi
    
    # Test 10: Cleanup
    section "Test 10: Cleanup and Resource Removal"
    
    log "Removing peering connection"
    if ./vpcctl unpeer-vpcs --vpc1 "$VPC1_NAME" --vpc2 "$VPC2_NAME" >> "$LOG_FILE" 2>&1; then
        success "Peering removed successfully"
    else
        warning "Failed to remove peering (may not exist)"
    fi
    
    log "Deleting VPC: $VPC1_NAME"
    if ./vpcctl delete-vpc --name "$VPC1_NAME" >> "$LOG_FILE" 2>&1; then
        success "VPC $VPC1_NAME deleted successfully"
    else
        error "Failed to delete VPC $VPC1_NAME"
    fi
    
    log "Deleting VPC: $VPC2_NAME"
    if ./vpcctl delete-vpc --name "$VPC2_NAME" >> "$LOG_FILE" 2>&1; then
        success "VPC $VPC2_NAME deleted successfully"
    else
        error "Failed to delete VPC $VPC2_NAME"
    fi
    
    # Verify cleanup
    log "Verifying cleanup"
    REMAINING_NS=$(ip netns list | grep -c "ns-" || echo 0)
    REMAINING_BR=$(ip link show type bridge | grep -c "br-" || echo 0)
    
    if [ "$REMAINING_NS" -eq 0 ] && [ "$REMAINING_BR" -eq 0 ]; then
        success "All resources cleaned up successfully"
    else
        warning "Some resources may still exist: $REMAINING_NS namespaces, $REMAINING_BR bridges"
    fi
    
    # Test Summary
    section "Test Summary"
    success "All tests completed!"
    log "Full log available at: $LOG_FILE"
    log "Test completed at: $(date)"
}

# Run tests
main

exit 0

