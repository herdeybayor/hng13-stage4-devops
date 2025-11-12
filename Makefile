.PHONY: help install test demo clean

help:
	@echo "VPC Control - Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install    - Set up vpcctl and dependencies"
	@echo "  test       - Run test scenarios"
	@echo "  demo       - Run a full demonstration"
	@echo "  clean      - Clean up all VPC resources"
	@echo ""

install:
	@echo "Installing vpcctl system-wide..."
	@sudo ./install.sh

uninstall:
	@echo "Uninstalling vpcctl..."
	@sudo ./uninstall.sh

local-setup:
	@echo "Setting up vpcctl for local development..."
	@chmod +x vpcctl
	@chmod +x cleanup.sh
	@chmod +x tests/run_tests.sh
	@chmod +x install.sh
	@chmod +x uninstall.sh
	@mkdir -p /var/lib/vpcctl
	@mkdir -p /var/log/vpcctl
	@echo "✓ Local setup complete!"
	@echo ""
	@echo "Usage: sudo ./vpcctl --help"
	@echo ""
	@echo "To install system-wide: sudo make install"

test:
	@echo "Running test scenarios..."
	@sudo ./tests/run_tests.sh

demo:
	@echo "Running demonstration..."
	@sudo ./tests/run_tests.sh --demo

clean:
	@echo "Cleaning up all resources..."
	@sudo ./cleanup.sh

check-root:
	@if [ "$$(id -u)" -ne 0 ]; then \
		echo "Error: Must run as root. Use 'sudo make <target>'"; \
		exit 1; \
	fi

