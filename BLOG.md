# Building Your Own Virtual Private Cloud (VPC) on Linux from Scratch

## Introduction

Have you ever wondered how cloud providers like AWS, Azure, or Google Cloud create those isolated virtual networks we call VPCs? In this comprehensive guide, you'll learn to build your own VPC system using nothing but Linux networking primitives. By the end, you'll have a deep understanding of network namespaces, bridges, routing, NAT, and how they all work together to create isolated virtual networks.

## What You'll Build

We'll create `vpcctl` - a command-line tool that lets you:
- Create isolated virtual networks (VPCs) on a single Linux machine
- Provision subnets (both public with internet access and private internal-only)
- Deploy applications within these subnets
- Control connectivity through routing and peering
- Apply firewall rules for security

Think of it as building a miniature version of AWS VPC, but understanding every line of code and networking command.

## Prerequisites

Before we begin, you'll need:
- A Linux machine (Ubuntu 20.04+ recommended)
- Root/sudo access
- Basic understanding of networking concepts (IP addresses, subnets)
- Familiarity with command line

## Understanding the Core Concepts

### Network Namespaces

Network namespaces are Linux's way of creating isolated network stacks. Each namespace has its own:
- Network interfaces
- IP addresses
- Routing tables
- Firewall rules

It's like having multiple computers on one physical machine!

### Virtual Ethernet (veth) Pairs

Think of veth pairs as virtual network cables. They always come in pairs - what goes in one end comes out the other. We use them to connect namespaces to bridges.

### Linux Bridges

Bridges act as virtual switches, connecting multiple network interfaces together. In our VPC, the bridge serves as the central router.

### Network Address Translation (NAT)

NAT allows our private IP addresses to access the internet by translating them to the host's public IP address.

## Architecture Overview

Here's what we're building:

```
Host System
├── VPC (10.0.0.0/16)
│   ├── Bridge (br-my-vpc)
│   ├── Public Subnet (10.0.1.0/24)
│   │   ├── Namespace (ns-my-vpc-public)
│   │   ├── NAT Gateway (iptables)
│   │   └── Application
│   └── Private Subnet (10.0.2.0/24)
│       ├── Namespace (ns-my-vpc-private)
│       └── Application
└── Internet Connection
```

## Step-by-Step Implementation

### Step 1: Project Setup

First, let's create our project structure:

```bash
mkdir vpc-control
cd vpc-control
mkdir -p lib policies tests logs
```

### Step 2: The Core CLI Tool

Create the main `vpcctl` script. This will be our interface to manage VPCs:

```python
#!/usr/bin/env python3
"""
vpcctl - Virtual Private Cloud Control CLI
"""
import argparse
import sys
import os

# Main CLI framework with commands for:
# - create-vpc
# - create-subnet
# - deploy-app
# - peer-vpcs
# - apply-policy
# And more...
```

The full implementation includes modules for:
- `vpc_manager.py` - Creates and manages VPCs
- `subnet_manager.py` - Handles subnet operations
- `nat_manager.py` - Configures NAT for internet access
- `peering_manager.py` - Connects VPCs together
- `firewall_manager.py` - Applies security rules

### Step 3: Creating a VPC

When you create a VPC, here's what happens behind the scenes:

```bash
sudo ./vpcctl create-vpc --name my-vpc --cidr 10.0.0.0/16
```

This command:
1. Creates a Linux bridge: `ip link add br-my-vpc type bridge`
2. Brings it up: `ip link set br-my-vpc up`
3. Stores the VPC configuration in a state file

The bridge acts as the VPC's virtual router.

### Step 4: Adding Subnets

Subnets are implemented as network namespaces:

```bash
sudo ./vpcctl create-subnet --vpc my-vpc --name public --cidr 10.0.1.0/24 --type public
```

Behind the scenes:
1. Create namespace: `ip netns add ns-my-vpc-public`
2. Create veth pair: `ip link add veth-public type veth peer name eth0`
3. Move one end to namespace: `ip link set eth0 netns ns-my-vpc-public`
4. Attach other end to bridge: `ip link set veth-public master br-my-vpc`
5. Configure IP address in namespace
6. Set up routing

For public subnets, we also configure NAT:

```bash
# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1

# Add NAT rule
iptables -t nat -A POSTROUTING -s 10.0.1.0/24 -o eth0 -j MASQUERADE
```

### Step 5: Deploying Applications

You can deploy test applications in your subnets:

```bash
sudo ./vpcctl deploy-app --vpc my-vpc --subnet public --port 8080
```

This creates a simple Python HTTP server inside the namespace:

```python
import http.server
import socketserver

PORT = 8080
with socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
    httpd.serve_forever()
```

### Step 6: VPC Isolation

By default, VPCs are completely isolated. Create a second VPC:

```bash
sudo ./vpcctl create-vpc --name dev-vpc --cidr 10.1.0.0/16
sudo ./vpcctl create-subnet --vpc dev-vpc --name public --cidr 10.1.1.0/24 --type public
```

Try to ping from one VPC to another - it won't work! This is isolation in action.

### Step 7: VPC Peering

To allow communication between VPCs:

```bash
sudo ./vpcctl peer-vpcs --vpc1 my-vpc --vpc2 dev-vpc
```

This:
1. Creates a veth pair connecting both bridges
2. Adds routes in each namespace to reach the other VPC's subnets

Now the VPCs can communicate!

### Step 8: Firewall Policies

Create a JSON policy file:

```json
{
  "subnet": "10.0.1.0/24",
  "ingress": [
    {
      "port": 80,
      "protocol": "tcp",
      "action": "allow"
    },
    {
      "port": 22,
      "protocol": "tcp",
      "action": "deny"
    }
  ]
}
```

Apply it:

```bash
sudo ./vpcctl apply-policy --vpc my-vpc --subnet public --policy policy.json
```

This translates to iptables rules in the namespace:

```bash
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -j DROP
```

## Testing Your VPC

### Test 1: Intra-VPC Connectivity

Subnets within the same VPC should communicate:

```bash
sudo ./vpcctl test-connectivity --vpc my-vpc --from-subnet public --to-subnet private
```

### Test 2: VPC Isolation

Different VPCs should be isolated:

```bash
# Get the namespace and IP
NS1="ns-my-vpc-public"
IP2="10.1.1.2"  # IP from dev-vpc

# Try to ping (should fail)
sudo ip netns exec $NS1 ping -c 2 $IP2
# Result: Network unreachable ✓
```

### Test 3: Internet Access

Public subnets should reach the internet:

```bash
sudo ip netns exec ns-my-vpc-public ping -c 3 8.8.8.8
# Result: Success ✓
```

Private subnets should NOT:

```bash
sudo ip netns exec ns-my-vpc-private ping -c 3 8.8.8.8
# Result: Network unreachable ✓
```

### Test 4: Peering

After peering, VPCs should communicate:

```bash
sudo ./vpcctl peer-vpcs --vpc1 my-vpc --vpc2 dev-vpc
sudo ip netns exec ns-my-vpc-public ping -c 2 10.1.1.2
# Result: Success ✓
```

## Common Issues and Solutions

### Issue 1: "Operation not permitted"

**Solution**: Always run with sudo:
```bash
sudo ./vpcctl create-vpc --name test --cidr 10.0.0.0/16
```

### Issue 2: "Bridge already exists"

**Solution**: Clean up first:
```bash
sudo ./cleanup.sh
```

### Issue 3: "No internet connectivity"

**Solutions**:
- Check IP forwarding: `sysctl net.ipv4.ip_forward`
- Verify interface name (might be ens33 instead of eth0)
- Check iptables rules: `sudo iptables -t nat -L`

## Cleanup

Always clean up your resources:

```bash
# Delete specific VPC
sudo ./vpcctl delete-vpc --name my-vpc

# Delete everything
sudo ./vpcctl cleanup-all

# Or use the cleanup script
sudo ./cleanup.sh
```

This removes:
- All network namespaces
- All bridges
- All veth pairs
- All iptables rules
- State files

## Running the Full Test Suite

The project includes a comprehensive test suite:

```bash
sudo make test
```

This tests:
- ✅ VPC creation and deletion
- ✅ Subnet management
- ✅ Application deployment
- ✅ Connectivity
- ✅ Isolation
- ✅ Peering
- ✅ Firewall policies
- ✅ NAT gateway
- ✅ Cleanup

## What You've Learned

By building this project, you now understand:

1. **Linux Network Namespaces**: How to create isolated network environments
2. **Virtual Networking**: How veth pairs and bridges connect namespaces
3. **Routing**: How packets flow between different network segments
4. **NAT**: How private networks access the internet
5. **iptables**: How to implement firewall rules
6. **VPC Architecture**: How cloud providers implement network isolation
7. **Infrastructure as Code**: How to automate network provisioning

## Real-World Applications

These concepts are used in:
- **Docker**: Container networking uses network namespaces
- **Kubernetes**: Pod networking and network policies
- **Cloud VPCs**: AWS VPC, Azure VNet, Google VPC
- **SD-WAN**: Software-defined networking
- **NFV**: Network function virtualization

## Next Steps

To extend this project, you could:
1. Add support for custom DHCP
2. Implement load balancing
3. Add VPN gateway functionality
4. Create a web dashboard
5. Support for IPv6
6. Integration with container runtimes

## Conclusion

You've just built a fully functional Virtual Private Cloud system from scratch using only Linux primitives. This knowledge is invaluable for understanding cloud networking, container orchestration, and modern infrastructure.

The complete code is available in the repository. Try it out, break it, fix it, and most importantly - understand how every piece works together.

## Resources

- Linux Network Namespaces: `man ip-netns`
- iptables Documentation: `man iptables`
- Linux Bridge: `man bridge`
- iproute2 Documentation: `man ip`

## Repository Structure

```
vpc-control/
├── vpcctl                  # Main CLI tool
├── lib/                    # Python modules
├── policies/               # Example policies
├── tests/                  # Test scripts
├── cleanup.sh              # Cleanup script
├── Makefile               # Build automation
└── README.md              # Documentation
```

## Installation

```bash
git clone <repository-url>
cd vpc-control
make install
sudo ./vpcctl --help
```

## Quick Start

```bash
# Create a VPC
sudo ./vpcctl create-vpc --name demo --cidr 10.0.0.0/16

# Add a public subnet
sudo ./vpcctl create-subnet --vpc demo --name web --cidr 10.0.1.0/24 --type public

# Deploy an app
sudo ./vpcctl deploy-app --vpc demo --subnet web --port 8080

# View your infrastructure
sudo ./vpcctl list-vpcs

# Clean up
sudo ./vpcctl delete-vpc --name demo
```

---

**Author**: HNG13 Stage 4 DevOps Challenge  
**Date**: November 2025  
**Tags**: Linux, Networking, VPC, DevOps, Infrastructure

---

Did you find this helpful? Try implementing it yourself and share your results!

