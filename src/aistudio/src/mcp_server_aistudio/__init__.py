"""
AI Studio MCP Server

A Model Context Protocol server for Google AI Studio automation.
"""

import logging

logger = logging.getLogger(__name__)

# Import main from server module - it's a regular function, not async
from .server import main
from .setup import ensure_playwright_setup

__version__ = "0.1.0"
__all__ = ["main"]


def _check_setup():
    """Check if setup is complete, run if needed."""
    try:
        # Quietly ensure playwright is ready
        ensure_playwright_setup()
    except Exception as e:
        logger.warning(f"Setup check failed: {e}")
        logger.warning("Run 'aistudio-mcp setup' to complete installation")


# Run setup check on import (only when used as MCP server)
_check_setup()
