"""
Subnet Manager - Handles subnet creation and management

Note: The routing setup here took me a while to figure out.
The key was using the 'onlink' flag to allow gateways outside the subnet.
"""

import os
from utils import (
    run_command, load_vpc_state, save_vpc_state,
    validate_cidr, cidr_contains, get_namespace_ip,
    namespace_exists
)

class SubnetManager:
    def __init__(self, logger):
        self.logger = logger

    def create_subnet(self, vpc_name, subnet_name, cidr, subnet_type):
        """Create a subnet within a VPC"""
        self.logger.info(f"Creating subnet {subnet_name} in VPC {vpc_name}")
        
        # Validate CIDR
        if not validate_cidr(cidr):
            raise ValueError(f"Invalid CIDR: {cidr}")
        
        # Load state
        state = load_vpc_state()
        
        if vpc_name not in state['vpcs']:
            raise ValueError(f"VPC {vpc_name} does not exist")
        
        vpc = state['vpcs'][vpc_name]
        
        # Check if subnet already exists
        if subnet_name in vpc['subnets']:
            raise ValueError(f"Subnet {subnet_name} already exists in VPC {vpc_name}")
        
        # Validate CIDR is within VPC CIDR
        if not cidr_contains(vpc['cidr'], cidr):
            raise ValueError(f"Subnet CIDR {cidr} is not within VPC CIDR {vpc['cidr']}")
        
        # Create namespace
        ns_name = f"ns-{vpc_name}-{subnet_name}"
        
        if namespace_exists(ns_name):
            self.logger.warning(f"Namespace {ns_name} exists, removing it first")
            run_command(f"ip netns delete {ns_name}", check=False)
        
        self.logger.info(f"Creating namespace: {ns_name}")
        run_command(f"ip netns add {ns_name}")
        
        # Create veth pair
        # IMPORTANT: Linux has a 15-char limit for interface names (IFNAMSIZ)
        # Learned this the hard way when long names like "veth-demo-vpc-public" failed
        # Now using MD5 hash to keep names short but unique
        import hashlib
        name_hash = hashlib.md5(f"{vpc_name}-{subnet_name}".encode()).hexdigest()[:6]
        
        veth_host = f"veth-{name_hash}"
        veth_ns = f"vpeer-{name_hash}"
        
        self.logger.info(f"Creating veth pair: {veth_host} <-> {veth_ns}")
        run_command(f"ip link add {veth_host} type veth peer name {veth_ns}")
        
        # Move one end to namespace
        run_command(f"ip link set {veth_ns} netns {ns_name}")
        
        # Rename interface inside namespace to eth0 for simplicity
        run_command(f"ip netns exec {ns_name} ip link set {veth_ns} name eth0")
        veth_ns_renamed = "eth0"
        
        # Attach host end to bridge
        bridge_name = vpc['bridge']
        self.logger.info(f"Attaching {veth_host} to bridge {bridge_name}")
        run_command(f"ip link set {veth_host} master {bridge_name}")
        run_command(f"ip link set {veth_host} up")
        
        # Configure namespace interface
        ns_ip = get_namespace_ip(cidr)
        # Get the correct prefix length from CIDR
        prefix_len = cidr.split('/')[1]
        self.logger.info(f"Configuring namespace interface with IP: {ns_ip}/{prefix_len}")
        run_command(f"ip netns exec {ns_name} ip addr add {ns_ip}/{prefix_len} dev {veth_ns_renamed}")
        run_command(f"ip netns exec {ns_name} ip link set {veth_ns_renamed} up")
        run_command(f"ip netns exec {ns_name} ip link set lo up")
        
        # Add route to VPC network through the bridge
        # The bridge has the first IP in the VPC CIDR range
        import ipaddress
        vpc_network = ipaddress.ip_network(vpc['cidr'], strict=False)
        gateway_ip = str(list(vpc_network.hosts())[0])
        
        # Add route for the entire VPC CIDR through the bridge
        # The 'onlink' flag here is crucial - it tells the kernel the gateway is reachable
        # even though it's not in the same subnet. Without this, you get "Network unreachable"
        self.logger.info(f"Adding route to VPC {vpc['cidr']} via {gateway_ip}")
        run_command(f"ip netns exec {ns_name} ip route add {vpc['cidr']} via {gateway_ip} dev {veth_ns_renamed} onlink", check=False)
        
        # Add default route for everything else
        self.logger.info(f"Setting default gateway: {gateway_ip}")
        run_command(f"ip netns exec {ns_name} ip route add default via {gateway_ip} dev {veth_ns_renamed} onlink", check=False)
        
        # Enable forwarding in namespace
        run_command(f"ip netns exec {ns_name} sysctl -w net.ipv4.ip_forward=1")
        
        # Configure NAT if public subnet
        if subnet_type == 'public':
            self._configure_nat(ns_name, cidr, vpc.get('interface', 'eth0'))
        
        # Store subnet info
        vpc['subnets'][subnet_name] = {
            'cidr': cidr,
            'type': subnet_type,
            'namespace': ns_name,
            'veth_host': veth_host,
            'veth_ns': veth_ns_renamed,
            'ip': ns_ip
        }
        
        save_vpc_state(state)
        
        self.logger.info(f"✓ Subnet {subnet_name} created successfully")
        self.logger.info(f"  Type: {subnet_type}")
        self.logger.info(f"  CIDR: {cidr}")
        self.logger.info(f"  Namespace: {ns_name}")
        self.logger.info(f"  IP: {ns_ip}")

    def _configure_nat(self, ns_name, cidr, interface):
        """Configure NAT for public subnet"""
        self.logger.info(f"Configuring NAT for subnet {cidr}")
        
        # Enable IP forwarding on host
        run_command("sysctl -w net.ipv4.ip_forward=1")
        
        # Add MASQUERADE rule
        run_command(
            f"iptables -t nat -A POSTROUTING -s {cidr} -o {interface} -j MASQUERADE"
        )
        
        # Allow forwarding
        run_command(f"iptables -A FORWARD -s {cidr} -j ACCEPT")
        run_command(f"iptables -A FORWARD -d {cidr} -j ACCEPT")

    def delete_subnet(self, vpc_name, subnet_name):
        """Delete a subnet"""
        self.logger.info(f"Deleting subnet {subnet_name} from VPC {vpc_name}")
        
        state = load_vpc_state()
        
        if vpc_name not in state['vpcs']:
            raise ValueError(f"VPC {vpc_name} does not exist")
        
        vpc = state['vpcs'][vpc_name]
        
        if subnet_name not in vpc['subnets']:
            raise ValueError(f"Subnet {subnet_name} does not exist in VPC {vpc_name}")
        
        subnet = vpc['subnets'][subnet_name]
        ns_name = subnet['namespace']
        veth_host = subnet['veth_host']
        
        # Stop applications
        self.stop_app(vpc_name, subnet_name)
        
        # Remove NAT rules if public
        if subnet['type'] == 'public':
            interface = vpc.get('interface', 'eth0')
            run_command(
                f"iptables -t nat -D POSTROUTING -s {subnet['cidr']} -o {interface} -j MASQUERADE",
                check=False
            )
        
        # Delete veth pair
        run_command(f"ip link delete {veth_host}", check=False)
        
        # Delete namespace
        if namespace_exists(ns_name):
            run_command(f"ip netns delete {ns_name}")
        
        # Remove from state
        del vpc['subnets'][subnet_name]
        save_vpc_state(state)
        
        self.logger.info(f"✓ Subnet {subnet_name} deleted successfully")

    def list_subnets(self, vpc_name):
        """List all subnets in a VPC"""
        state = load_vpc_state()
        
        if vpc_name not in state['vpcs']:
            raise ValueError(f"VPC {vpc_name} does not exist")
        
        vpc = state['vpcs'][vpc_name]
        
        if not vpc['subnets']:
            print(f"No subnets found in VPC {vpc_name}")
            return
        
        print(f"\nSubnets in VPC: {vpc_name}")
        print("="*80)
        
        for subnet_name, subnet_data in vpc['subnets'].items():
            print(f"\nSubnet: {subnet_name}")
            print(f"  Type: {subnet_data['type']}")
            print(f"  CIDR: {subnet_data['cidr']}")
            print(f"  Namespace: {subnet_data['namespace']}")
            print(f"  IP: {subnet_data['ip']}")
            print(f"  Veth (host): {subnet_data['veth_host']}")

    def deploy_app(self, vpc_name, subnet_name, port, app_type='python'):
        """Deploy a test application in a subnet"""
        self.logger.info(f"Deploying {app_type} app in {vpc_name}/{subnet_name} on port {port}")
        
        state = load_vpc_state()
        
        if vpc_name not in state['vpcs']:
            raise ValueError(f"VPC {vpc_name} does not exist")
        
        vpc = state['vpcs'][vpc_name]
        
        if subnet_name not in vpc['subnets']:
            raise ValueError(f"Subnet {subnet_name} does not exist")
        
        subnet = vpc['subnets'][subnet_name]
        ns_name = subnet['namespace']
        
        if app_type == 'python':
            # Create a simple HTTP server
            app_script = f"""
import http.server
import socketserver

PORT = {port}

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        response = f'''
        <html>
        <head><title>VPC Test App</title></head>
        <body>
            <h1>Hello from {vpc_name}/{subnet_name}!</h1>
            <p>Subnet IP: {subnet['ip']}</p>
            <p>Subnet CIDR: {subnet['cidr']}</p>
            <p>Subnet Type: {subnet['type']}</p>
        </body>
        </html>
        '''
        self.wfile.write(response.encode())

with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    print(f"Server running on port {{PORT}}")
    httpd.serve_forever()
"""
            
            # Write script to namespace
            script_path = f"/tmp/app-{vpc_name}-{subnet_name}.py"
            with open(script_path, 'w') as f:
                f.write(app_script)
            
            # Start server in background
            self.logger.info(f"Starting Python HTTP server on port {port}")
            run_command(
                f"ip netns exec {ns_name} python3 {script_path} > /dev/null 2>&1 &",
                check=False
            )
        
        self.logger.info(f"✓ Application deployed successfully")
        self.logger.info(f"  Access via: http://{subnet['ip']}:{port}")

    def stop_app(self, vpc_name, subnet_name):
        """Stop application in a subnet"""
        self.logger.info(f"Stopping application in {vpc_name}/{subnet_name}")
        
        state = load_vpc_state()
        
        if vpc_name not in state['vpcs']:
            raise ValueError(f"VPC {vpc_name} does not exist")
        
        vpc = state['vpcs'][vpc_name]
        
        if subnet_name not in vpc['subnets']:
            raise ValueError(f"Subnet {subnet_name} does not exist")
        
        subnet = vpc['subnets'][subnet_name]
        ns_name = subnet['namespace']
        
        # Kill processes
        run_command(f"ip netns exec {ns_name} pkill -9 python3", check=False)
        run_command(f"ip netns exec {ns_name} pkill -9 nginx", check=False)
        
        self.logger.info(f"✓ Application stopped")

    def test_connectivity(self, vpc_name, from_subnet, to_subnet):
        """Test connectivity between subnets"""
        self.logger.info(f"Testing connectivity: {from_subnet} -> {to_subnet}")
        
        state = load_vpc_state()
        
        if vpc_name not in state['vpcs']:
            raise ValueError(f"VPC {vpc_name} does not exist")
        
        vpc = state['vpcs'][vpc_name]
        
        if from_subnet not in vpc['subnets']:
            raise ValueError(f"Subnet {from_subnet} does not exist")
        
        if to_subnet not in vpc['subnets']:
            raise ValueError(f"Subnet {to_subnet} does not exist")
        
        from_ns = vpc['subnets'][from_subnet]['namespace']
        to_ip = vpc['subnets'][to_subnet]['ip']
        
        self.logger.info(f"Pinging {to_ip} from {from_ns}")
        
        result = run_command(
            f"ip netns exec {from_ns} ping -c 3 -W 2 {to_ip}",
            check=False
        )
        
        if result.returncode == 0:
            self.logger.info("✓ Connectivity test PASSED")
            print(result.stdout)
        else:
            self.logger.error("✗ Connectivity test FAILED")
            print(result.stderr)

