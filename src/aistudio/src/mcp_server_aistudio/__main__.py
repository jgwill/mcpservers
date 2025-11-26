"""
AI Studio MCP Server - Main entry point
"""

from .server import main

if __name__ == "__main__":
    # main() is a regular function that calls mcp.run(), not async
    main()
