"""
Centralized constants for smi-bench configuration.

This module provides single-source-of-truth defaults for configuration values
that are used across multiple modules. Using these constants instead of
hardcoded values ensures consistency and makes configuration changes easier.

Environment variable overrides:
- SMI_DEFAULT_RPC_URL: Override the default Sui RPC endpoint
- SMI_SENDER: Default sender address for transactions
"""

from __future__ import annotations

import os

# Default Sui RPC endpoint
# This is the public mainnet fullnode. For production workloads, consider:
# 1. Using a dedicated RPC provider (e.g., Triton, Shinami)
# 2. Running your own fullnode
# 3. Setting SMI_DEFAULT_RPC_URL environment variable
DEFAULT_RPC_URL = os.environ.get(
    "SMI_DEFAULT_RPC_URL",
    "https://fullnode.mainnet.sui.io:443",
)

# Mock sender address used when no real sender is provided
# This address is used for build-only mode and testing
MOCK_SENDER_ADDRESS = "0x0"

# Default agent for benchmarking
DEFAULT_AGENT = "real-openai-compatible"

# Default simulation mode
DEFAULT_SIMULATION_MODE = "dry-run"

# Default timeout for per-package processing (seconds)
DEFAULT_PER_PACKAGE_TIMEOUT_SECONDS = 300.0

# Default maximum plan attempts per package
DEFAULT_MAX_PLAN_ATTEMPTS = 2

# A2A Protocol version
A2A_PROTOCOL_VERSION = "0.3.0"

# Default ports for A2A agents
DEFAULT_GREEN_AGENT_PORT = 9999
DEFAULT_PURPLE_AGENT_PORT = 9998

# RPC request timeout (seconds)
RPC_REQUEST_TIMEOUT_SECONDS = 30.0

# Health check timeout (seconds)
HEALTH_CHECK_TIMEOUT_SECONDS = 5.0
