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
	@echo "Setting up vpcctl..."
	@chmod +x vpcctl
	@chmod +x cleanup.sh
	@chmod +x tests/run_tests.sh
	@mkdir -p /var/lib/vpcctl
	@mkdir -p /var/log/vpcctl
	@echo "✓ Installation complete!"
	@echo ""
	@echo "Usage: sudo ./vpcctl --help"

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

