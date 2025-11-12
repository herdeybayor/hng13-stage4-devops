# Contributing to VPC Control

Hey! Thanks for checking out this project. I built this for the HNG13 Stage 4 DevOps challenge and learned a ton about Linux networking in the process.

## Development Notes

If you want to contribute or just understand how this works, here are some things I learned the hard way:

### Network Namespaces

These were tricky at first. The key insight is that each namespace is basically its own isolated network stack. Think of it like a mini-VM but just for networking.

### Interface Naming

Linux has a 15-character limit on interface names (IFNAMSIZ). I originally tried longer names and got cryptic errors. Now I use short hashes to keep names unique but under the limit.

### Bridge Setup

The bridge acts as the VPC router. I initially forgot to assign it an IP address and couldn't figure out why subnets couldn't talk to each other. Face-palm moment when I realized bridges need IPs too!

## Issues I Had to Debug

1. **Connectivity between subnets** - Needed the `onlink` flag in routing. Spent 2 hours on this one.
2. **Cleanup getting stuck** - Python processes weren't dying properly. Had to use `ip netns pids` instead of just `pkill`.
3. **NAT not working** - Forgot to enable IP forwarding on the host. Classic mistake.

## Testing

Run the test suite:

```bash
sudo make test
```

Or just run the demo to see everything in action:

```bash
sudo ./examples/demo.sh
```

## Code Style

I tried to keep things simple and readable. Some of the error handling could be better, but it works for the demo scenarios.

If you find bugs or have improvements, feel free to open an issue or PR!

## Author

Built by Sherifdeen Adebayo ([@herdeybayor](https://github.com/herdeybayor)) for HNG13 DevOps Challenge.

Still learning! Hit me up if you have questions or suggestions.
