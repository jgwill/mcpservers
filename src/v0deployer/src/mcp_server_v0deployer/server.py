#!/usr/bin/env python3
"""
v0 Deployer MCP Server

A comprehensive Model Context Protocol server for v0.dev deployment automation.
Uses FastMCP for simplicity and reliability.

Provides tools, resources, and prompts for Vercel deployment workflows.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from mcp.server import FastMCP

from .automation import (
    v0_login as do_v0_login,
    v0_git_pull as do_v0_git_pull,
    v0_publish as do_v0_publish,
    v0_view_app as do_v0_view_app,
    v0_deploy as do_v0_deploy,
)
from .config import DOCS_PATH

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP(name="v0deployer")


# ============================================================================
# TOOLS - Deployment functions
# ============================================================================

@mcp.tool()
async def v0_login() -> dict:
    """Authenticate to v0.dev and save session state."""
    logger.info("Starting v0.dev authentication...")
    return await do_v0_login()


@mcp.tool()
async def v0_git_pull(v0_chat_url: str) -> dict:
    """Pull latest changes from Git repository into v0.dev editor."""
    logger.info(f"Pulling Git changes for: {v0_chat_url}")
    return await do_v0_git_pull(v0_chat_url)


@mcp.tool()
async def v0_publish(v0_chat_url: str) -> dict:
    """Publish changes to Vercel from v0.dev."""
    logger.info(f"Publishing to Vercel: {v0_chat_url}")
    return await do_v0_publish(v0_chat_url)


@mcp.tool()
async def v0_view_app(production_url: str, wait_seconds: int = 60) -> dict:
    """Open production application in browser for testing."""
    logger.info(f"Viewing app: {production_url}")
    return await do_v0_view_app(production_url, wait_seconds)


@mcp.tool()
async def v0_deploy(v0_chat_url: str, production_url: str, view: bool = False) -> dict:
    """Complete deployment workflow: pull from Git, publish to Vercel, and optionally view app."""
    logger.info("Running complete deployment workflow...")
    return await do_v0_deploy(v0_chat_url, production_url, view)


# ============================================================================
# RESOURCES - Documentation accessible via MCP
# ============================================================================

@mcp.resource("v0://docs/{doc_key}")
async def get_documentation(doc_key: str) -> str:
    """Get v0 deployer documentation by key."""
    doc_files = {
        "deployment-workflow": "deployment-workflow.md",
        "agent-collaboration": "agent-collaboration.md",
        "build-integrity": "build-integrity.md",
    }

    filename = doc_files.get(doc_key)
    if not filename:
        raise ValueError(f"Unknown document: {doc_key}")

    file_path = DOCS_PATH / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Documentation file not found: {filename}")

    return file_path.read_text(encoding="utf-8")


# ============================================================================
# PROMPTS - Pre-configured workflows
# ============================================================================

@mcp.prompt()
async def deploy_to_vercel(
    v0_chat_url: str,
    production_url: str,
    view_after_deploy: str = "false"
) -> str:
    """Complete deployment workflow for v0.dev to Vercel."""
    view = view_after_deploy.lower() == "true"
    return f"""# Deploy v0.dev Project to Vercel

## Deployment Details
**v0.dev Project**: {v0_chat_url}
**Production URL**: {production_url}
**View After Deploy**: {view}

## Complete Deployment Workflow

### Step 1: Pull Changes from Git
Use `v0_git_pull` tool to sync workspace with latest Git commits.

### Step 2: Publish to Vercel
Use `v0_publish` tool to commit and trigger Vercel deployment.

### Step 3: Wait for Deployment
Allow 15-20 seconds for Vercel deployment to complete.

### Step 4: Verify Deployment
{"Use `v0_view_app` tool to test the production application." if view else "Optionally verify at " + production_url}

## Reference Documentation
- Read v0://docs/deployment-workflow for detailed UI patterns
"""


@mcp.prompt()
async def troubleshoot_deployment(issue_description: str) -> str:
    """Debug common v0.dev and Vercel deployment issues."""
    return f"""# Troubleshoot v0.dev Deployment Issue

## Issue Description
{issue_description}

## Troubleshooting Steps

### Step 1: Identify Issue Category
Read v0://docs/deployment-workflow to find matching issue:
- Nested UI elements not clicked (GitHub/Publish dropdowns)
- Timing issues (testing before deployment completes)
- Authentication issues
- Build failures

### Step 2: Apply Quick Fixes
- **GitHub/Publish buttons**: These are DROPDOWN buttons - click to open, then select action
- **Authentication**: Run `v0_login` again
- **Old version showing**: Wait 15-20 seconds after publish, clear cache
- **Build fails**: Read v0://docs/build-integrity for pre-flight checks

## Reference Documentation
- Read v0://docs/deployment-workflow for complete troubleshooting
- Read v0://docs/build-integrity for production build best practices
"""


def main():
    """Main entry point for the server - this is a regular function, not async."""
    logger.info("v0 Deployer MCP Server starting...")
    logger.info("Available tools: v0_login, v0_git_pull, v0_publish, v0_view_app, v0_deploy")
    logger.info("Available resources: Documentation via v0://docs/*")
    logger.info("Available prompts: deploy-to-vercel, troubleshoot-deployment")
    mcp.run()


if __name__ == "__main__":
    main()
