# Quick Start Guide - VPC Control

## 5-Minute Setup

### 1. Installation (30 seconds)

```bash
cd /Users/sherifdeenadebayo/Developer/hng13-stage4-devops
make install
```

### 2. Your First VPC (2 minutes)

```bash
# Create a VPC
sudo ./vpcctl create-vpc --name test-vpc --cidr 10.0.0.0/16

# Add a public subnet (with internet access)
sudo ./vpcctl create-subnet --vpc test-vpc --name public --cidr 10.0.1.0/24 --type public

# Add a private subnet (internal only)
sudo ./vpcctl create-subnet --vpc test-vpc --name private --cidr 10.0.2.0/24 --type private

# View your VPC
sudo ./vpcctl list-vpcs
```

### 3. Deploy & Test (2 minutes)

```bash
# Deploy web apps
sudo ./vpcctl deploy-app --vpc test-vpc --subnet public --port 8080
sudo ./vpcctl deploy-app --vpc test-vpc --subnet private --port 8080

# Test connectivity between subnets
sudo ./vpcctl test-connectivity --vpc test-vpc --from-subnet public --to-subnet private
```

### 4. Cleanup (30 seconds)

```bash
sudo ./vpcctl delete-vpc --name test-vpc
```

## Run the Demo

```bash
sudo ./examples/demo.sh
```

This demonstrates:

- VPC creation
- Subnet management
- App deployment
- VPC peering
- Firewall policies
- Complete cleanup

## Run Tests

```bash
sudo make test
```

This validates all functionality automatically.

## Common Commands

```bash
# List all VPCs
sudo ./vpcctl list-vpcs

# List subnets in a VPC
sudo ./vpcctl list-subnets --vpc <vpc-name>

# Create VPC peering
sudo ./vpcctl peer-vpcs --vpc1 <name1> --vpc2 <name2>

# Apply firewall policy
sudo ./vpcctl apply-policy --vpc <vpc-name> --subnet <subnet-name> --policy policies/web-server.json

# Clean up everything
sudo ./vpcctl cleanup-all
```

## Troubleshooting

If something goes wrong:

```bash
# Clean up all resources
sudo ./cleanup.sh

# Check logs
sudo tail -f /var/log/vpcctl/vpcctl-$(date +%Y%m%d).log

# Verify namespaces
ip netns list

# Verify bridges
ip link show type bridge
```

## Next Steps

1. Read the full [README.md](README.md) for detailed documentation
2. Read the [BLOG.md](BLOG.md) to understand how it works
3. Experiment with the example policies in `policies/`
4. Create your own multi-VPC setup

## Stage 4 Submission Checklist

- ✅ Working VPC CLI (`vpcctl`)
- ✅ VPC creation with CIDR ranges
- ✅ Public and private subnets
- ✅ Routing between subnets
- ✅ NAT gateway for internet access
- ✅ VPC isolation demonstrated
- ✅ VPC peering implemented
- ✅ Firewall policies with JSON
- ✅ App deployment capability
- ✅ Comprehensive testing
- ✅ Complete documentation
- ✅ Blog post included
- ✅ Cleanup automation

**Status: Ready for submission! 🚀**
