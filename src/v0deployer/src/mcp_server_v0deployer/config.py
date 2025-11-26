"""
Configuration constants for v0 Deployer MCP Server.
"""
import os
from pathlib import Path

# Storage paths
SCRIPT_DIR = Path(__file__).parent
STORAGE_STATE_PATH = SCRIPT_DIR / "v0_auth_state.json"

# The config file for v0 deployment (v0_config.json)
# Expected in the Current Working Directory when running
CONFIG_PATH = Path.cwd() / "v0_config.json"

# Timing patterns for v0.dev UI
DROPDOWN_WAIT = 1  # Seconds - Wait for dropdown menus to appear
SYNC_WAIT = 120  # Seconds - Wait for "Syncing Changes" to complete
PUBLISH_WAIT = 180  # Seconds - Wait for "Publishing..." to complete
VIEW_APP_WAIT = 60  # Seconds - Keep browser open when viewing app

# Documentation base path
DOCS_PATH = Path(__file__).parent.parent.parent / "docs"
