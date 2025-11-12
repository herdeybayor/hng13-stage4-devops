"""
Utility functions for VPC management
"""

import subprocess
import json
import os
import ipaddress

def run_command(cmd, check=True, capture_output=True):
    """Execute shell command and return result"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=check,
            capture_output=capture_output,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        raise Exception(f"Command failed: {cmd}\nError: {e.stderr}")

def load_vpc_state():
    """Load VPC state from file"""
    state_file = '/var/lib/vpcctl/state.json'
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f)
    return {'vpcs': {}, 'peerings': []}

def save_vpc_state(state):
    """Save VPC state to file"""
    state_dir = '/var/lib/vpcctl'
    if not os.path.exists(state_dir):
        os.makedirs(state_dir)
    
    state_file = os.path.join(state_dir, 'state.json')
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

def validate_cidr(cidr):
    """Validate CIDR notation"""
    try:
        ipaddress.ip_network(cidr, strict=False)
        return True
    except ValueError:
        return False

def cidr_contains(parent_cidr, child_cidr):
    """Check if child CIDR is within parent CIDR"""
    parent = ipaddress.ip_network(parent_cidr, strict=False)
    child = ipaddress.ip_network(child_cidr, strict=False)
    return child.subnet_of(parent)

def get_bridge_ip(cidr):
    """Get bridge IP from CIDR (first usable IP)"""
    network = ipaddress.ip_network(cidr, strict=False)
    return str(list(network.hosts())[0])

def get_namespace_ip(cidr):
    """Get namespace IP from CIDR (second usable IP)"""
    network = ipaddress.ip_network(cidr, strict=False)
    hosts = list(network.hosts())
    if len(hosts) > 1:
        return str(hosts[1])
    return str(hosts[0])

def namespace_exists(name):
    """Check if network namespace exists"""
    result = run_command(f"ip netns list", check=False)
    return name in result.stdout

def bridge_exists(name):
    """Check if bridge exists"""
    result = run_command(f"ip link show {name}", check=False)
    return result.returncode == 0

def interface_exists(name):
    """Check if interface exists"""
    result = run_command(f"ip link show {name}", check=False)
    return result.returncode == 0

