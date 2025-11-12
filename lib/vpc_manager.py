"""
VPC Manager - Handles VPC creation and management
"""

import os
from utils import (
    run_command, load_vpc_state, save_vpc_state,
    validate_cidr, bridge_exists, namespace_exists
)

class VPCManager:
    def __init__(self, logger):
        self.logger = logger

    def create_vpc(self, name, cidr, interface='eth0'):
        """Create a new VPC"""
        self.logger.info(f"Creating VPC: {name} with CIDR: {cidr}")
        
        # Validate CIDR
        if not validate_cidr(cidr):
            raise ValueError(f"Invalid CIDR: {cidr}")
        
        # Load current state
        state = load_vpc_state()
        
        # Check if VPC already exists
        if name in state['vpcs']:
            raise ValueError(f"VPC {name} already exists")
        
        # Create bridge for VPC
        bridge_name = f"br-{name}"
        
        if bridge_exists(bridge_name):
            self.logger.warning(f"Bridge {bridge_name} already exists, removing it first")
            run_command(f"ip link delete {bridge_name}", check=False)
        
        self.logger.info(f"Creating bridge: {bridge_name}")
        run_command(f"ip link add {bridge_name} type bridge")
        
        # Assign IP to bridge (first IP in CIDR range) so it can route
        import ipaddress
        network = ipaddress.ip_network(cidr, strict=False)
        bridge_ip = str(list(network.hosts())[0])
        
        self.logger.info(f"Assigning IP {bridge_ip} to bridge")
        run_command(f"ip addr add {bridge_ip}/16 dev {bridge_name}")
        run_command(f"ip link set {bridge_name} up")
        
        # Enable IP forwarding
        run_command("sysctl -w net.ipv4.ip_forward=1")
        
        # Allow forwarding on the bridge
        run_command(f"iptables -A FORWARD -i {bridge_name} -o {bridge_name} -j ACCEPT", check=False)
        run_command(f"iptables -A FORWARD -i {bridge_name} -j ACCEPT", check=False)
        run_command(f"iptables -A FORWARD -o {bridge_name} -j ACCEPT", check=False)
        
        # Store VPC info
        state['vpcs'][name] = {
            'cidr': cidr,
            'bridge': bridge_name,
            'interface': interface,
            'subnets': {}
        }
        
        save_vpc_state(state)
        
        self.logger.info(f"✓ VPC {name} created successfully")
        self.logger.info(f"  Bridge: {bridge_name}")
        self.logger.info(f"  CIDR: {cidr}")
        self.logger.info(f"  Internet Interface: {interface}")

    def delete_vpc(self, name):
        """Delete a VPC and all its resources"""
        self.logger.info(f"Deleting VPC: {name}")
        
        state = load_vpc_state()
        
        if name not in state['vpcs']:
            raise ValueError(f"VPC {name} does not exist")
        
        vpc = state['vpcs'][name]
        bridge_name = vpc['bridge']
        
        # Delete all subnets first
        subnets = list(vpc['subnets'].keys())
        for subnet_name in subnets:
            self._delete_subnet_resources(name, subnet_name, vpc)
        
        # Remove peerings
        peerings_to_remove = []
        for peering in state.get('peerings', []):
            if name in [peering['vpc1'], peering['vpc2']]:
                peerings_to_remove.append(peering)
        
        for peering in peerings_to_remove:
            self.logger.info(f"Removing peering: {peering['vpc1']} <-> {peering['vpc2']}")
            state['peerings'].remove(peering)
            # Clean up peering interfaces
            peer_if = f"peer-{peering['vpc1']}-{peering['vpc2']}"
            run_command(f"ip link delete {peer_if}", check=False)
        
        # Delete bridge
        if bridge_exists(bridge_name):
            self.logger.info(f"Deleting bridge: {bridge_name}")
            run_command(f"ip link set {bridge_name} down", check=False)
            run_command(f"ip link delete {bridge_name}", check=False)
        
        # Remove from state
        del state['vpcs'][name]
        save_vpc_state(state)
        
        self.logger.info(f"✓ VPC {name} deleted successfully")

    def _delete_subnet_resources(self, vpc_name, subnet_name, vpc):
        """Delete subnet resources"""
        subnet = vpc['subnets'][subnet_name]
        ns_name = subnet['namespace']
        veth_host = subnet['veth_host']
        
        # Stop any running apps
        self.logger.info(f"Stopping applications in subnet {subnet_name}")
        run_command(f"ip netns exec {ns_name} pkill -9 python3", check=False)
        run_command(f"ip netns exec {ns_name} pkill -9 nginx", check=False)
        
        # Remove NAT rules if public subnet
        if subnet.get('type') == 'public':
            self.logger.info(f"Removing NAT rules for {subnet_name}")
            interface = vpc.get('interface', 'eth0')
            run_command(
                f"iptables -t nat -D POSTROUTING -s {subnet['cidr']} -o {interface} -j MASQUERADE",
                check=False
            )
        
        # Remove firewall rules
        self.logger.info(f"Flushing firewall rules in {subnet_name}")
        run_command(f"ip netns exec {ns_name} iptables -F", check=False)
        run_command(f"ip netns exec {ns_name} iptables -X", check=False)
        
        # Delete veth pair
        self.logger.info(f"Deleting veth pair: {veth_host}")
        run_command(f"ip link delete {veth_host}", check=False)
        
        # Delete namespace
        if namespace_exists(ns_name):
            self.logger.info(f"Deleting namespace: {ns_name}")
            run_command(f"ip netns delete {ns_name}", check=False)

    def list_vpcs(self):
        """List all VPCs"""
        state = load_vpc_state()
        
        if not state['vpcs']:
            print("No VPCs found")
            return
        
        print("\n" + "="*80)
        print("VPC List")
        print("="*80)
        
        for vpc_name, vpc_data in state['vpcs'].items():
            print(f"\nVPC: {vpc_name}")
            print(f"  CIDR: {vpc_data['cidr']}")
            print(f"  Bridge: {vpc_data['bridge']}")
            print(f"  Internet Interface: {vpc_data.get('interface', 'N/A')}")
            print(f"  Subnets: {len(vpc_data['subnets'])}")
            
            if vpc_data['subnets']:
                for subnet_name, subnet_data in vpc_data['subnets'].items():
                    print(f"    - {subnet_name} ({subnet_data['cidr']}) [{subnet_data.get('type', 'N/A')}]")
        
        # Show peerings
        if state.get('peerings'):
            print("\n" + "="*80)
            print("VPC Peerings")
            print("="*80)
            for peering in state['peerings']:
                print(f"  {peering['vpc1']} <-> {peering['vpc2']}")
        
        print("\n" + "="*80)

    def cleanup_all(self):
        """Clean up all VPCs and resources"""
        self.logger.info("Cleaning up all VPCs and resources")
        
        state = load_vpc_state()
        
        vpc_names = list(state['vpcs'].keys())
        
        for vpc_name in vpc_names:
            try:
                self.delete_vpc(vpc_name)
            except Exception as e:
                self.logger.error(f"Error deleting VPC {vpc_name}: {e}")
        
        # Clean orphaned namespaces
        self.logger.info("Cleaning orphaned namespaces")
        result = run_command("ip netns list", check=False)
        for line in result.stdout.splitlines():
            ns_name = line.split()[0]
            if ns_name.startswith('ns-'):
                self.logger.info(f"Removing orphaned namespace: {ns_name}")
                run_command(f"ip netns delete {ns_name}", check=False)
        
        # Clean orphaned bridges
        self.logger.info("Cleaning orphaned bridges")
        result = run_command("ip link show type bridge", check=False)
        for line in result.stdout.splitlines():
            if 'br-' in line:
                bridge_name = line.split(':')[1].strip().split('@')[0]
                if bridge_name.startswith('br-'):
                    self.logger.info(f"Removing orphaned bridge: {bridge_name}")
                    run_command(f"ip link set {bridge_name} down", check=False)
                    run_command(f"ip link delete {bridge_name}", check=False)
        
        self.logger.info("✓ Cleanup completed")

