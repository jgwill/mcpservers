"""
v0 Deployer MCP Server - Main entry point
"""

import asyncio
from .server import main

if __name__ == "__main__":
    asyncio.run(main())
