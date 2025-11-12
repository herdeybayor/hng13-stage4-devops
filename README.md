# VPC Control - Virtual Private Cloud on Linux

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Linux-orange)

A comprehensive command-line tool for creating and managing Virtual Private Clouds (VPCs) on Linux using network namespaces, veth pairs, bridges, and iptables. This project recreates the fundamentals of cloud VPCs entirely with Linux networking primitives.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
- [Testing](#testing)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🎯 Overview

VPC Control (`vpcctl`) allows you to:

- Create isolated virtual networks (VPCs) on a single Linux host
- Provision multiple subnets (public and private) within each VPC
- Enable routing between subnets and across VPCs
- Implement NAT gateway for internet access
- Deploy applications within subnets
- Apply firewall policies (security groups)
- Demonstrate network isolation and controlled peering

## ✨ Features

- **VPC Management**: Create, list, and delete virtual private clouds
- **Subnet Provisioning**: Support for public and private subnets
- **Network Isolation**: Complete isolation between VPCs by default
- **VPC Peering**: Controlled connectivity between VPCs
- **NAT Gateway**: Internet access for public subnets
- **Firewall Policies**: JSON-based security group rules
- **Application Deployment**: Deploy test web servers in subnets
- **Comprehensive Logging**: All operations logged for audit
- **Clean Teardown**: Proper cleanup of all resources

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Host System                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    VPC (10.1.0.0/16)                │   │
│  │                                                     │   │
│  │  ┌──────────────────┐      ┌──────────────────┐   │   │
│  │  │  Public Subnet   │      │  Private Subnet  │   │
│  │  │  (10.1.1.0/24)   │      │  (10.1.2.0/24)   │   │
│  │  │                  │      │                  │   │
│  │  │  [Namespace]     │      │  [Namespace]     │   │
│  │  │  - eth0          │      │  - eth0          │   │
│  │  │  - App (8080)    │      │  - App (8080)    │   │
│  │  └────────┬─────────┘      └────────┬─────────┘   │
│  │           │                         │             │
│  │           └────────┬────────────────┘             │
│  │                    │                              │
│  │          ┌─────────▼────────┐                     │
│  │          │   Linux Bridge   │                     │
│  │          │   (br-vpc-name)  │                     │
│  │          └─────────┬────────┘                     │
│  │                    │                              │
│  └────────────────────┼──────────────────────────────┘
│                       │                                
│                 ┌─────▼──────┐                        
│                 │ NAT/iptables│                       
│                 └─────┬──────┘                        
│                       │                               
└───────────────────────┼───────────────────────────────┘
                        │
                  ┌─────▼──────┐
                  │  Internet  │
                  └────────────┘
```

### Key Components

1. **Network Namespaces**: Each subnet is implemented as a network namespace, providing complete network isolation
2. **veth Pairs**: Virtual ethernet pairs connect namespaces to bridges
3. **Linux Bridges**: Act as virtual switches/routers for each VPC
4. **iptables**: Provide NAT, forwarding, and firewall rules
5. **Routing Tables**: Enable connectivity within and across VPCs

## 📦 Requirements

- Linux operating system (kernel 3.8+)
- Root/sudo access
- Required packages:
  - `iproute2` (ip command)
  - `iptables`
  - `bridge-utils`
  - `python3` (for CLI)

Install dependencies:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y iproute2 iptables bridge-utils python3

# CentOS/RHEL
sudo yum install -y iproute iptables bridge-utils python3

# Arch Linux
sudo pacman -S iproute2 iptables bridge-utils python
```

## 🚀 Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd hng13-stage4-devops
```

2. Run the installation:

```bash
make install
```

This will:
- Make scripts executable
- Create necessary directories
- Set up logging

## 🎬 Quick Start

Here's a 5-minute walkthrough to create a fully functional VPC:

```bash
# 1. Create a VPC
sudo ./vpcctl create-vpc --name my-vpc --cidr 10.0.0.0/16

# 2. Add a public subnet
sudo ./vpcctl create-subnet --vpc my-vpc --name public --cidr 10.0.1.0/24 --type public

# 3. Add a private subnet
sudo ./vpcctl create-subnet --vpc my-vpc --name private --cidr 10.0.2.0/24 --type private

# 4. Deploy applications
sudo ./vpcctl deploy-app --vpc my-vpc --subnet public --port 8080
sudo ./vpcctl deploy-app --vpc my-vpc --subnet private --port 8080

# 5. Test connectivity
sudo ./vpcctl test-connectivity --vpc my-vpc --from-subnet public --to-subnet private

# 6. View your VPC
sudo ./vpcctl list-vpcs

# 7. Clean up
sudo ./vpcctl delete-vpc --name my-vpc
```

## 📖 Usage Guide

### Create a VPC

```bash
sudo ./vpcctl create-vpc --name <vpc-name> --cidr <cidr-block> [--interface <interface>]
```

**Options:**
- `--name`: Unique name for the VPC
- `--cidr`: IP address range in CIDR notation (e.g., 10.0.0.0/16)
- `--interface`: Host's internet interface (default: eth0)

**Example:**
```bash
sudo ./vpcctl create-vpc --name prod-vpc --cidr 10.0.0.0/16 --interface eth0
```

### Create a Subnet

```bash
sudo ./vpcctl create-subnet --vpc <vpc-name> --name <subnet-name> --cidr <cidr> --type <public|private>
```

**Options:**
- `--vpc`: VPC name
- `--name`: Subnet name
- `--cidr`: Subnet CIDR (must be within VPC CIDR)
- `--type`: `public` (with NAT) or `private` (internal only)

**Example:**
```bash
sudo ./vpcctl create-subnet --vpc prod-vpc --name web-tier --cidr 10.0.1.0/24 --type public
sudo ./vpcctl create-subnet --vpc prod-vpc --name db-tier --cidr 10.0.2.0/24 --type private
```

### Deploy an Application

```bash
sudo ./vpcctl deploy-app --vpc <vpc-name> --subnet <subnet-name> --port <port> [--type <python|nginx>]
```

**Example:**
```bash
sudo ./vpcctl deploy-app --vpc prod-vpc --subnet web-tier --port 8080 --type python
```

### Apply Firewall Policy

```bash
sudo ./vpcctl apply-policy --vpc <vpc-name> --subnet <subnet-name> --policy <policy-file.json>
```

**Example:**
```bash
sudo ./vpcctl apply-policy --vpc prod-vpc --subnet web-tier --policy policies/web-server.json
```

### VPC Peering

```bash
# Create peering
sudo ./vpcctl peer-vpcs --vpc1 <vpc1-name> --vpc2 <vpc2-name>

# Remove peering
sudo ./vpcctl unpeer-vpcs --vpc1 <vpc1-name> --vpc2 <vpc2-name>
```

**Example:**
```bash
sudo ./vpcctl peer-vpcs --vpc1 prod-vpc --vpc2 dev-vpc
```

### List Resources

```bash
# List all VPCs
sudo ./vpcctl list-vpcs

# List subnets in a VPC
sudo ./vpcctl list-subnets --vpc <vpc-name>
```

### Test Connectivity

```bash
sudo ./vpcctl test-connectivity --vpc <vpc-name> --from-subnet <source> --to-subnet <destination>
```

### Cleanup

```bash
# Delete specific VPC
sudo ./vpcctl delete-vpc --name <vpc-name>

# Delete all VPCs and resources
sudo ./vpcctl cleanup-all

# Or use the cleanup script
sudo ./cleanup.sh
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
sudo make test

# Run manual tests
sudo ./tests/run_tests.sh
```

The test suite validates:
- ✅ VPC creation and deletion
- ✅ Subnet management (public and private)
- ✅ Application deployment
- ✅ Intra-VPC connectivity
- ✅ VPC isolation
- ✅ VPC peering
- ✅ Firewall policies
- ✅ NAT gateway functionality
- ✅ Resource cleanup

## 💡 Examples

### Example 1: Simple Web Application

```bash
# Create VPC
sudo ./vpcctl create-vpc --name web-vpc --cidr 10.10.0.0/16

# Create public subnet for web servers
sudo ./vpcctl create-subnet --vpc web-vpc --name web --cidr 10.10.1.0/24 --type public

# Create private subnet for database
sudo ./vpcctl create-subnet --vpc web-vpc --name db --cidr 10.10.2.0/24 --type private

# Deploy web app
sudo ./vpcctl deploy-app --vpc web-vpc --subnet web --port 8080

# Deploy database app
sudo ./vpcctl deploy-app --vpc web-vpc --subnet db --port 5432

# Test connectivity
sudo ./vpcctl test-connectivity --vpc web-vpc --from-subnet web --to-subnet db
```

### Example 2: Multi-VPC with Peering

```bash
# Create production VPC
sudo ./vpcctl create-vpc --name prod --cidr 10.0.0.0/16
sudo ./vpcctl create-subnet --vpc prod --name app --cidr 10.0.1.0/24 --type public

# Create development VPC
sudo ./vpcctl create-vpc --name dev --cidr 10.1.0.0/16
sudo ./vpcctl create-subnet --vpc dev --name app --cidr 10.1.1.0/24 --type public

# Deploy apps
sudo ./vpcctl deploy-app --vpc prod --subnet app --port 8080
sudo ./vpcctl deploy-app --vpc dev --subnet app --port 8080

# Test isolation (should fail)
sudo ./vpcctl test-connectivity --vpc prod --from-subnet app --to-subnet app # Won't work across VPCs

# Create peering
sudo ./vpcctl peer-vpcs --vpc1 prod --vpc2 dev

# Now test connectivity (should work)
# You can manually test with: sudo ip netns exec ns-prod-app ping <dev-ip>
```

### Example 3: Firewall Policies

Create a policy file `policies/custom-policy.json`:

```json
{
  "subnet": "10.0.1.0/24",
  "description": "Custom security policy",
  "ingress": [
    {
      "port": 80,
      "protocol": "tcp",
      "action": "allow",
      "source": "0.0.0.0/0"
    },
    {
      "port": 443,
      "protocol": "tcp",
      "action": "allow",
      "source": "0.0.0.0/0"
    },
    {
      "port": 22,
      "protocol": "tcp",
      "action": "deny",
      "source": "0.0.0.0/0"
    }
  ],
  "egress": [
    {
      "port": "*",
      "protocol": "tcp",
      "action": "allow",
      "destination": "0.0.0.0/0"
    }
  ]
}
```

Apply the policy:

```bash
sudo ./vpcctl apply-policy --vpc my-vpc --subnet public --policy policies/custom-policy.json
```

## 🔍 Troubleshooting

### Common Issues

**1. Permission Denied**
```bash
Error: This script must be run as root (use sudo)
```
Solution: Always use `sudo` when running vpcctl commands.

**2. Network Namespace Already Exists**
```bash
Error: Namespace ns-vpc-subnet already exists
```
Solution: Clean up existing resources:
```bash
sudo ./cleanup.sh
```

**3. CIDR Overlap**
```bash
Error: Subnet CIDR is not within VPC CIDR
```
Solution: Ensure subnet CIDR is a subset of VPC CIDR.

**4. No Internet Connectivity**
```bash
Error: Cannot reach internet from public subnet
```
Solution: Check your interface name and ensure IP forwarding is enabled:
```bash
sudo sysctl -w net.ipv4.ip_forward=1
sudo iptables -L -t nat
```

**5. Application Not Starting**
```bash
Warning: Application deployment may have issues
```
Solution: Check logs:
```bash
tail -f /var/log/vpcctl/vpcctl-*.log
```

### Debug Commands

```bash
# List all network namespaces
ip netns list

# List all bridges
ip link show type bridge

# Check routes in a namespace
sudo ip netns exec ns-vpc-subnet ip route

# Check iptables rules
sudo iptables -L -n -v
sudo iptables -t nat -L -n -v

# Test from within a namespace
sudo ip netns exec ns-vpc-subnet ping 8.8.8.8
sudo ip netns exec ns-vpc-subnet curl http://10.0.1.2:8080
```

### Logs

All operations are logged to `/var/log/vpcctl/vpcctl-YYYYMMDD.log`

View logs:
```bash
sudo tail -f /var/log/vpcctl/vpcctl-$(date +%Y%m%d).log
```

## 📊 Testing Scenarios

### Scenario 1: Intra-VPC Communication
**Expected**: Subnets within the same VPC can communicate

```bash
sudo ./vpcctl test-connectivity --vpc my-vpc --from-subnet public --to-subnet private
# Expected: ✓ Connectivity test PASSED
```

### Scenario 2: VPC Isolation
**Expected**: Different VPCs cannot communicate without peering

```bash
# Get namespace and IP from VPC2
sudo ip netns exec ns-vpc1-subnet ping <vpc2-ip>
# Expected: Network unreachable or timeout
```

### Scenario 3: Internet Access
**Expected**: Public subnets can reach internet, private cannot

```bash
# Public subnet
sudo ip netns exec ns-my-vpc-public ping -c 3 8.8.8.8
# Expected: Success

# Private subnet
sudo ip netns exec ns-my-vpc-private ping -c 3 8.8.8.8
# Expected: Network unreachable
```

### Scenario 4: Peering
**Expected**: After peering, VPCs can communicate

```bash
sudo ./vpcctl peer-vpcs --vpc1 vpc-a --vpc2 vpc-b
sudo ip netns exec ns-vpc-a-subnet ping <vpc-b-ip>
# Expected: Success
```

### Scenario 5: Firewall
**Expected**: Traffic follows policy rules

```bash
sudo ./vpcctl apply-policy --vpc my-vpc --subnet public --policy policies/web-server.json
# Port 80 should be open, port 22 should be blocked
```

## 🗂 Project Structure

```
hng13-stage4-devops/
├── vpcctl                      # Main CLI tool
├── lib/                        # Python modules
│   ├── vpc_manager.py          # VPC operations
│   ├── subnet_manager.py       # Subnet operations
│   ├── nat_manager.py          # NAT gateway
│   ├── peering_manager.py      # VPC peering
│   ├── firewall_manager.py     # Firewall policies
│   ├── logger.py               # Logging setup
│   └── utils.py                # Utility functions
├── policies/                   # Example firewall policies
│   ├── web-server.json
│   ├── secure-server.json
│   └── private-subnet.json
├── tests/                      # Test scripts
│   └── run_tests.sh            # Comprehensive test suite
├── cleanup.sh                  # Cleanup script
├── Makefile                    # Build automation
└── README.md                   # This file
```

## 🔒 Security Considerations

- Always run as root (required for network operations)
- Firewall rules are enforced at the namespace level
- NAT rules are managed via iptables
- Default policy is DENY for firewall rules
- VPCs are isolated by default
- Peering must be explicitly configured

## 📝 State Management

VPC state is stored in `/var/lib/vpcctl/state.json`

Example state file:
```json
{
  "vpcs": {
    "my-vpc": {
      "cidr": "10.0.0.0/16",
      "bridge": "br-my-vpc",
      "interface": "eth0",
      "subnets": {
        "public": {
          "cidr": "10.0.1.0/24",
          "type": "public",
          "namespace": "ns-my-vpc-public",
          "veth_host": "veth-my-vpc-public",
          "veth_ns": "eth0",
          "ip": "10.0.1.2"
        }
      }
    }
  },
  "peerings": []
}
```

## 🎓 Educational Value

This project demonstrates:

1. **Linux Networking Fundamentals**
   - Network namespaces for isolation
   - Virtual ethernet (veth) pairs
   - Linux bridges as virtual switches
   - Routing tables and forwarding

2. **Network Address Translation (NAT)**
   - MASQUERADE for internet access
   - Port forwarding concepts
   - Public vs private subnets

3. **Firewall & Security**
   - iptables chains and rules
   - Stateful packet filtering
   - Security group concepts

4. **Cloud Networking Concepts**
   - VPC architecture
   - Subnet design
   - Peering connections
   - Gateway configuration

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📄 License

This project is licensed under the MIT License.

## 👥 Author

Created for HNG13 Stage 4 DevOps Challenge

## 🙏 Acknowledgments

- Linux networking documentation
- AWS VPC architecture inspiration
- HNG Internship program

## 📞 Support

For issues or questions:
- Check the troubleshooting section
- Review logs in `/var/log/vpcctl/`
- Open an issue on GitHub

---

**Note**: This is an educational project. For production use, consider using established tools like Kubernetes, Docker networking, or cloud provider VPCs.

