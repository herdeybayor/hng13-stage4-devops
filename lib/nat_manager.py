"""
NAT Manager - Handles Network Address Translation
"""

from utils import run_command, load_vpc_state

class NATManager:
    def __init__(self, logger):
        self.logger = logger

    def configure_nat_gateway(self, vpc_name, subnet_name):
        """Configure NAT gateway for a subnet"""
        self.logger.info(f"Configuring NAT gateway for {vpc_name}/{subnet_name}")
        
        state = load_vpc_state()
        
        if vpc_name not in state['vpcs']:
            raise ValueError(f"VPC {vpc_name} does not exist")
        
        vpc = state['vpcs'][vpc_name]
        
        if subnet_name not in vpc['subnets']:
            raise ValueError(f"Subnet {subnet_name} does not exist")
        
        subnet = vpc['subnets'][subnet_name]
        interface = vpc.get('interface', 'eth0')
        cidr = subnet['cidr']
        
        # Enable IP forwarding
        self.logger.info("Enabling IP forwarding")
        run_command("sysctl -w net.ipv4.ip_forward=1")
        
        # Add MASQUERADE rule
        self.logger.info(f"Adding MASQUERADE rule for {cidr}")
        run_command(
            f"iptables -t nat -A POSTROUTING -s {cidr} -o {interface} -j MASQUERADE"
        )
        
        # Allow forwarding
        run_command(f"iptables -A FORWARD -s {cidr} -j ACCEPT")
        run_command(f"iptables -A FORWARD -d {cidr} -j ACCEPT")
        
        self.logger.info("✓ NAT gateway configured successfully")

    def remove_nat_gateway(self, vpc_name, subnet_name):
        """Remove NAT gateway configuration"""
        self.logger.info(f"Removing NAT gateway for {vpc_name}/{subnet_name}")
        
        state = load_vpc_state()
        
        if vpc_name not in state['vpcs']:
            raise ValueError(f"VPC {vpc_name} does not exist")
        
        vpc = state['vpcs'][vpc_name]
        
        if subnet_name not in vpc['subnets']:
            raise ValueError(f"Subnet {subnet_name} does not exist")
        
        subnet = vpc['subnets'][subnet_name]
        interface = vpc.get('interface', 'eth0')
        cidr = subnet['cidr']
        
        # Remove MASQUERADE rule
        self.logger.info(f"Removing MASQUERADE rule for {cidr}")
        run_command(
            f"iptables -t nat -D POSTROUTING -s {cidr} -o {interface} -j MASQUERADE",
            check=False
        )
        
        # Remove forwarding rules
        run_command(f"iptables -D FORWARD -s {cidr} -j ACCEPT", check=False)
        run_command(f"iptables -D FORWARD -d {cidr} -j ACCEPT", check=False)
        
        self.logger.info("✓ NAT gateway removed successfully")

    def test_internet_connectivity(self, vpc_name, subnet_name):
        """Test internet connectivity from a subnet"""
        self.logger.info(f"Testing internet connectivity from {vpc_name}/{subnet_name}")
        
        state = load_vpc_state()
        
        if vpc_name not in state['vpcs']:
            raise ValueError(f"VPC {vpc_name} does not exist")
        
        vpc = state['vpcs'][vpc_name]
        
        if subnet_name not in vpc['subnets']:
            raise ValueError(f"Subnet {subnet_name} does not exist")
        
        subnet = vpc['subnets'][subnet_name]
        ns_name = subnet['namespace']
        
        self.logger.info("Pinging 8.8.8.8 (Google DNS)")
        
        result = run_command(
            f"ip netns exec {ns_name} ping -c 3 -W 2 8.8.8.8",
            check=False
        )
        
        if result.returncode == 0:
            self.logger.info("✓ Internet connectivity test PASSED")
            return True
        else:
            self.logger.warning("✗ Internet connectivity test FAILED")
            return False

