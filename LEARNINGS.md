# What I Learned Building VPC Control

## Background

I took on this project for HNG13 Stage 4 without really knowing much about network namespaces or Linux bridges. Here's what I figured out along the way.

## Key Concepts That Clicked

### Network Namespaces

At first, I thought these were like containers. They're not. They're more focused - just isolated network stacks. Each namespace has:

- Its own interfaces
- Its own routing table
- Its own iptables rules

### veth Pairs

These are like virtual ethernet cables. You create them in pairs - whatever you send into one end comes out the other. Perfect for connecting namespaces to bridges.

### Linux Bridges

The bridge is basically a virtual switch. I connect all the veth interfaces to it, and it handles the packet forwarding between subnets.

## Problems I Hit

### 1. Subnets Couldn't Talk to Each Other

**Problem**: Created VPC, added subnets, but ping between them failed with "Network unreachable".

**Solution**: The bridge needs an IP address! I gave it the first IP in the VPC CIDR range (10.0.0.1 for a 10.0.0.0/16 VPC). Then added the `onlink` flag to routes so namespaces could reach the gateway.

```python
# This was the fix
run_command(f"ip addr add {bridge_ip}/16 dev {bridge_name}")
run_command(f"ip netns exec {ns_name} ip route add default via {gateway_ip} dev eth0 onlink")
```

### 2. Interface Name Too Long Error

**Error**: `"name" not a valid ifname`

**Cause**: Linux interface names max out at 15 chars. I was using `veth-demo-vpc-public` (19 chars).

**Solution**: Used MD5 hash to shorten names: `veth-a38dc5` (11 chars). Still unique, but short enough.

### 3. Cleanup Getting Killed

**Problem**: When deleting VPCs, the Python HTTP servers wouldn't die and the whole cleanup process would hang.

**Solution**: More aggressive process killing:

```bash
ip netns pids {namespace} | xargs -r kill -9
```

### 4. NAT Not Working

**Problem**: Public subnets couldn't reach the internet even with NAT configured.

**Cause**: Forgot to enable IP forwarding on the host system.

**Fix**:

```bash
sysctl -w net.ipv4.ip_forward=1
```

## Cool Tricks I Discovered

### 1. Resolve Symlinks for Installation

When installing system-wide, `__file__` gives you the symlink path. Use `os.path.realpath()` to get the actual location:

```python
script_path = os.path.realpath(__file__)  # Resolves /usr/local/bin/vpcctl -> /opt/vpcctl/vpcctl
```

### 2. State Management

Storing VPC state as JSON in `/var/lib/vpcctl/state.json` made it easy to:

- Track what's created
- Enable cleanup without memory
- Debug issues

### 3. Demo Script

The `examples/demo.sh` saved me tons of time testing. Instead of manually running 20 commands, one script does it all.

## Resources That Helped

- `man ip-netns` - Network namespace documentation
- `man iptables` - Firewall rules
- Trial and error (lots of it!)
- Checking routes with `ip netns exec {ns} ip route`
- Watching packets with `tcpdump` in namespaces

## What I'd Do Differently

1. **Better error messages** - Some errors are too generic
2. **Dry run mode** - Would be nice to see what commands will run before actually running them
3. **Status command** - Show health of VPCs, check connectivity automatically
4. **Config file** - Instead of just state, store user preferences

## Conclusion

This was a challenging project but I learned a ton about Linux networking. Building your own VPC really makes you appreciate what cloud providers do!

The key insight: VPCs aren't magic. They're just clever use of Linux networking primitives that have been around for years.

---

Sherifdeen Adebayo  
November 2024
