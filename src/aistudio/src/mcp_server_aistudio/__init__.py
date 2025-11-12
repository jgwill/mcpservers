"""
AI Studio MCP Server

A Model Context Protocol server for Google AI Studio automation.
"""

# Import main from server module - it's a regular function, not async
from .server import main

__version__ = "0.1.0"
__all__ = ["main"]
