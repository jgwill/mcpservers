"""
Configuration constants for AI Studio MCP Server.
"""
from pathlib import Path

# Storage paths
STORAGE_STATE_PATH = Path.home() / ".playwright" / "aistudio_auth_state.json"
STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Critical timing patterns (from llms-aistudio-04-browser-automation-reference.md)
GEMINI_IMPLEMENTATION_WAIT = 90  # Seconds - Gemini implementation minimum
DIALOG_LOAD_WAIT = 8  # Seconds - GitHub/Deploy dialog rendering
VERIFICATION_RETRY_WAIT = 3  # Seconds - Between verification checks
NAVIGATION_WAIT = 3  # Seconds - Page navigation settle time

# Documentation base path
DOCS_PATH = Path(__file__).parent.parent.parent / "docs"
