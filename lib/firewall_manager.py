"""
Firewall Manager - Handles security group rules and firewall policies
"""

import json
from utils import run_command, load_vpc_state

class FirewallManager:
    def __init__(self, logger):
        self.logger = logger

    def apply_policy(self, vpc_name, subnet_name, policy_file):
        """Apply firewall policy from JSON file to a subnet"""
        self.logger.info(f"Applying firewall policy to {vpc_name}/{subnet_name}")
        
        # Load policy
        try:
            with open(policy_file, 'r') as f:
                policy = json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load policy file: {e}")
        
        # Validate policy
        if 'subnet' not in policy:
            raise ValueError("Policy must specify 'subnet' field")
        
        # Load VPC state
        state = load_vpc_state()
        
        if vpc_name not in state['vpcs']:
            raise ValueError(f"VPC {vpc_name} does not exist")
        
        vpc = state['vpcs'][vpc_name]
        
        if subnet_name not in vpc['subnets']:
            raise ValueError(f"Subnet {subnet_name} does not exist")
        
        subnet = vpc['subnets'][subnet_name]
        ns_name = subnet['namespace']
        
        # Clear existing rules
        self.logger.info(f"Clearing existing firewall rules in {ns_name}")
        run_command(f"ip netns exec {ns_name} iptables -F INPUT")
        run_command(f"ip netns exec {ns_name} iptables -F OUTPUT")
        run_command(f"ip netns exec {ns_name} iptables -F FORWARD")
        
        # Set default policies to DROP
        self.logger.info("Setting default policy to DROP")
        run_command(f"ip netns exec {ns_name} iptables -P INPUT DROP")
        run_command(f"ip netns exec {ns_name} iptables -P FORWARD DROP")
        
        # Allow established connections
        run_command(
            f"ip netns exec {ns_name} iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT"
        )
        run_command(
            f"ip netns exec {ns_name} iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT"
        )
        
        # Allow loopback
        run_command(f"ip netns exec {ns_name} iptables -A INPUT -i lo -j ACCEPT")
        run_command(f"ip netns exec {ns_name} iptables -A OUTPUT -o lo -j ACCEPT")
        
        # Apply ingress rules
        if 'ingress' in policy:
            self.logger.info("Applying ingress rules")
            for rule in policy['ingress']:
                self._apply_ingress_rule(ns_name, rule)
        
        # Apply egress rules
        if 'egress' in policy:
            self.logger.info("Applying egress rules")
            for rule in policy['egress']:
                self._apply_egress_rule(ns_name, rule)
        else:
            # Default: allow all egress
            run_command(f"ip netns exec {ns_name} iptables -P OUTPUT ACCEPT")
        
        self.logger.info(f"✓ Firewall policy applied successfully")
        self._show_rules(ns_name)

    def _apply_ingress_rule(self, ns_name, rule):
        """Apply a single ingress rule"""
        # TODO: Add support for port ranges (e.g., 8000-9000)
        port = rule.get('port', '*')
        protocol = rule.get('protocol', 'tcp')
        action = rule.get('action', 'allow').upper()
        source = rule.get('source', '0.0.0.0/0')
        
        if action == 'ALLOW':
            target = 'ACCEPT'
        elif action == 'DENY':
            target = 'DROP'
        else:
            self.logger.warning(f"Unknown action: {action}, defaulting to DROP")
            target = 'DROP'
        
        if port == '*':
            cmd = f"ip netns exec {ns_name} iptables -A INPUT -p {protocol} -s {source} -j {target}"
        else:
            cmd = f"ip netns exec {ns_name} iptables -A INPUT -p {protocol} -s {source} --dport {port} -j {target}"
        
        self.logger.info(f"Adding ingress rule: port={port}, proto={protocol}, action={action}")
        run_command(cmd)

    def _apply_egress_rule(self, ns_name, rule):
        """Apply a single egress rule"""
        port = rule.get('port', '*')
        protocol = rule.get('protocol', 'tcp')
        action = rule.get('action', 'allow').upper()
        destination = rule.get('destination', '0.0.0.0/0')
        
        if action == 'ALLOW':
            target = 'ACCEPT'
        elif action == 'DENY':
            target = 'DROP'
        else:
            self.logger.warning(f"Unknown action: {action}, defaulting to DROP")
            target = 'DROP'
        
        if port == '*':
            cmd = f"ip netns exec {ns_name} iptables -A OUTPUT -p {protocol} -d {destination} -j {target}"
        else:
            cmd = f"ip netns exec {ns_name} iptables -A OUTPUT -p {protocol} -d {destination} --dport {port} -j {target}"
        
        self.logger.info(f"Adding egress rule: port={port}, proto={protocol}, action={action}")
        run_command(cmd)

    def _show_rules(self, ns_name):
        """Display current firewall rules"""
        self.logger.info(f"Current firewall rules in {ns_name}:")
        
        result = run_command(f"ip netns exec {ns_name} iptables -L -n -v", check=False)
        if result.returncode == 0:
            print("\n" + "="*80)
            print(result.stdout)
            print("="*80 + "\n")

    def clear_policy(self, vpc_name, subnet_name):
        """Clear firewall policy from a subnet"""
        self.logger.info(f"Clearing firewall policy from {vpc_name}/{subnet_name}")
        
        state = load_vpc_state()
        
        if vpc_name not in state['vpcs']:
            raise ValueError(f"VPC {vpc_name} does not exist")
        
        vpc = state['vpcs'][vpc_name]
        
        if subnet_name not in vpc['subnets']:
            raise ValueError(f"Subnet {subnet_name} does not exist")
        
        subnet = vpc['subnets'][subnet_name]
        ns_name = subnet['namespace']
        
        # Flush all rules
        run_command(f"ip netns exec {ns_name} iptables -F")
        run_command(f"ip netns exec {ns_name} iptables -X")
        
        # Set default policies to ACCEPT
        run_command(f"ip netns exec {ns_name} iptables -P INPUT ACCEPT")
        run_command(f"ip netns exec {ns_name} iptables -P FORWARD ACCEPT")
        run_command(f"ip netns exec {ns_name} iptables -P OUTPUT ACCEPT")
        
        self.logger.info(f"✓ Firewall policy cleared successfully")

    def show_policy(self, vpc_name, subnet_name):
        """Show current firewall policy for a subnet"""
        state = load_vpc_state()
        
        if vpc_name not in state['vpcs']:
            raise ValueError(f"VPC {vpc_name} does not exist")
        
        vpc = state['vpcs'][vpc_name]
        
        if subnet_name not in vpc['subnets']:
            raise ValueError(f"Subnet {subnet_name} does not exist")
        
        subnet = vpc['subnets'][subnet_name]
        ns_name = subnet['namespace']
        
        print(f"\nFirewall rules for {vpc_name}/{subnet_name} ({ns_name})")
        print("="*80)
        
        result = run_command(f"ip netns exec {ns_name} iptables -L -n -v", check=False)
        if result.returncode == 0:
            print(result.stdout)

