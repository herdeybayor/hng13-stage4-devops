"""
Peering Manager - Handles VPC peering connections
"""

from utils import run_command, load_vpc_state, save_vpc_state
import ipaddress

class PeeringManager:
    def __init__(self, logger):
        self.logger = logger

    def peer_vpcs(self, vpc1_name, vpc2_name):
        """Create a peering connection between two VPCs"""
        self.logger.info(f"Creating peering connection: {vpc1_name} <-> {vpc2_name}")
        
        state = load_vpc_state()
        
        # Validate VPCs exist
        if vpc1_name not in state['vpcs']:
            raise ValueError(f"VPC {vpc1_name} does not exist")
        
        if vpc2_name not in state['vpcs']:
            raise ValueError(f"VPC {vpc2_name} does not exist")
        
        vpc1 = state['vpcs'][vpc1_name]
        vpc2 = state['vpcs'][vpc2_name]
        
        # Check if peering already exists
        for peering in state.get('peerings', []):
            if (peering['vpc1'] == vpc1_name and peering['vpc2'] == vpc2_name) or \
               (peering['vpc1'] == vpc2_name and peering['vpc2'] == vpc1_name):
                raise ValueError(f"Peering already exists between {vpc1_name} and {vpc2_name}")
        
        # Check for CIDR overlap
        cidr1 = ipaddress.ip_network(vpc1['cidr'], strict=False)
        cidr2 = ipaddress.ip_network(vpc2['cidr'], strict=False)
        
        if cidr1.overlaps(cidr2):
            raise ValueError(f"VPC CIDRs overlap: {vpc1['cidr']} and {vpc2['cidr']}")
        
        # Create veth pair to connect bridges
        veth1 = f"peer-{vpc1_name}-{vpc2_name}"
        veth2 = f"peer-{vpc2_name}-{vpc1_name}"
        
        self.logger.info(f"Creating veth pair: {veth1} <-> {veth2}")
        run_command(f"ip link add {veth1} type veth peer name {veth2}")
        
        # Attach to bridges
        bridge1 = vpc1['bridge']
        bridge2 = vpc2['bridge']
        
        self.logger.info(f"Attaching {veth1} to {bridge1}")
        run_command(f"ip link set {veth1} master {bridge1}")
        run_command(f"ip link set {veth1} up")
        
        self.logger.info(f"Attaching {veth2} to {bridge2}")
        run_command(f"ip link set {veth2} master {bridge2}")
        run_command(f"ip link set {veth2} up")
        
        # Add routes for each subnet in the VPCs
        for subnet1_name, subnet1_data in vpc1['subnets'].items():
            for subnet2_name, subnet2_data in vpc2['subnets'].items():
                # Add route from subnet1 to subnet2
                ns1 = subnet1_data['namespace']
                cidr2 = subnet2_data['cidr']
                
                self.logger.info(f"Adding route: {ns1} -> {cidr2} via {bridge1}")
                run_command(
                    f"ip netns exec {ns1} ip route add {cidr2} via {subnet1_data['ip'].rsplit('.', 1)[0]}.1",
                    check=False
                )
                
                # Add route from subnet2 to subnet1
                ns2 = subnet2_data['namespace']
                cidr1 = subnet1_data['cidr']
                
                self.logger.info(f"Adding route: {ns2} -> {cidr1} via {bridge2}")
                run_command(
                    f"ip netns exec {ns2} ip route add {cidr1} via {subnet2_data['ip'].rsplit('.', 1)[0]}.1",
                    check=False
                )
        
        # Store peering info
        if 'peerings' not in state:
            state['peerings'] = []
        
        state['peerings'].append({
            'vpc1': vpc1_name,
            'vpc2': vpc2_name,
            'veth1': veth1,
            'veth2': veth2
        })
        
        save_vpc_state(state)
        
        self.logger.info(f"✓ Peering connection created successfully")
        self.logger.info(f"  {vpc1_name} ({vpc1['cidr']}) <-> {vpc2_name} ({vpc2['cidr']})")

    def unpeer_vpcs(self, vpc1_name, vpc2_name):
        """Remove peering connection between two VPCs"""
        self.logger.info(f"Removing peering connection: {vpc1_name} <-> {vpc2_name}")
        
        state = load_vpc_state()
        
        # Find peering
        peering = None
        for p in state.get('peerings', []):
            if (p['vpc1'] == vpc1_name and p['vpc2'] == vpc2_name) or \
               (p['vpc1'] == vpc2_name and p['vpc2'] == vpc1_name):
                peering = p
                break
        
        if not peering:
            raise ValueError(f"No peering exists between {vpc1_name} and {vpc2_name}")
        
        # Delete veth pair
        veth1 = peering['veth1']
        self.logger.info(f"Deleting veth pair: {veth1}")
        run_command(f"ip link delete {veth1}", check=False)
        
        # Remove routes
        vpc1 = state['vpcs'][peering['vpc1']]
        vpc2 = state['vpcs'][peering['vpc2']]
        
        for subnet1_name, subnet1_data in vpc1['subnets'].items():
            for subnet2_name, subnet2_data in vpc2['subnets'].items():
                # Remove route from subnet1 to subnet2
                ns1 = subnet1_data['namespace']
                cidr2 = subnet2_data['cidr']
                
                run_command(
                    f"ip netns exec {ns1} ip route del {cidr2}",
                    check=False
                )
                
                # Remove route from subnet2 to subnet1
                ns2 = subnet2_data['namespace']
                cidr1 = subnet1_data['cidr']
                
                run_command(
                    f"ip netns exec {ns2} ip route del {cidr1}",
                    check=False
                )
        
        # Remove from state
        state['peerings'].remove(peering)
        save_vpc_state(state)
        
        self.logger.info(f"✓ Peering connection removed successfully")

    def list_peerings(self):
        """List all VPC peerings"""
        state = load_vpc_state()
        
        if not state.get('peerings'):
            print("No VPC peerings found")
            return
        
        print("\nVPC Peerings")
        print("="*80)
        
        for peering in state['peerings']:
            vpc1 = state['vpcs'][peering['vpc1']]
            vpc2 = state['vpcs'][peering['vpc2']]
            
            print(f"\n{peering['vpc1']} <-> {peering['vpc2']}")
            print(f"  {peering['vpc1']} CIDR: {vpc1['cidr']}")
            print(f"  {peering['vpc2']} CIDR: {vpc2['cidr']}")
            print(f"  Veth interfaces: {peering['veth1']} <-> {peering['veth2']}")

