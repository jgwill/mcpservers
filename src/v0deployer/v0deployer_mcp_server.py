#!/usr/bin/env python3
"""
v0 Deployer MCP Server - Standalone Version

Uses FastMCP for simplicity. Can be run directly without installation.
Provides tools and resources for v0.dev deployment automation.

Usage:
    python v0deployer_mcp_server.py

Or in .mcp.json:
{
  "mcpServers": {
    "v0deployer": {
      "command": "python",
      "args": ["/path/to/v0deployer_mcp_server.py"]
    }
  }
}
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: mcp package not found. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration constants
SCRIPT_DIR = Path(__file__).parent
STORAGE_STATE_PATH = SCRIPT_DIR / "v0_auth_state.json"
DOCS_PATH = Path(__file__).parent / "docs"

# Timing patterns for v0.dev UI
DROPDOWN_WAIT = 1  # Seconds
SYNC_WAIT = 120  # Seconds
PUBLISH_WAIT = 180  # Seconds
VIEW_APP_WAIT = 60  # Seconds

# Create FastMCP server
mcp = FastMCP(name="v0deployer")


# ============================================================================
# AUTOMATION HELPERS
# ============================================================================

class V0Automation:
    """Playwright-based automation for v0.dev deployment workflows."""

    def __init__(self, storage_state_path: Optional[Path] = None):
        self.storage_state_path = storage_state_path or STORAGE_STATE_PATH
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def login_v0(self) -> Dict[str, Any]:
        """Initialize browser context and perform v0.dev authentication."""
        logger.info("Starting v0.dev login process...")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context()
                page = await context.new_page()

                logger.info("Navigating to v0.app...")
                await page.goto("https://v0.app")

                logger.info("*****************************************************************")
                logger.info("BROWSER OPENED. PLEASE LOG IN MANUALLY (e.g., using your Passkey).")
                logger.info("The script will wait for 2 minutes for you to complete the login.")
                logger.info("*****************************************************************")

                try:
                    await page.get_by_role("link", name="Projects").wait_for(state="visible", timeout=120000)
                    logger.info("Login successful!")
                    logger.info(f"Saving authentication state to {self.storage_state_path}...")
                    await context.storage_state(path=str(self.storage_state_path))
                    logger.info("Authentication state saved successfully.")

                    await browser.close()

                    return {
                        "status": "success",
                        "message": f"Authenticated to v0.dev. Session saved to {self.storage_state_path}",
                        "storage_state_path": str(self.storage_state_path)
                    }

                except TimeoutError:
                    await browser.close()
                    return {
                        "status": "error",
                        "error": "Login was not completed within the 2-minute time limit."
                    }

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def git_pull_changes(self, context: BrowserContext, v0_chat_url: str) -> Dict[str, Any]:
        """Automate the git pull process using an authenticated context."""
        page = await context.new_page()
        try:
            logger.info(f"Navigating to {v0_chat_url} for git pull...")
            await page.goto(v0_chat_url)
            await page.get_by_role("button", name="Synced to main").wait_for(state="visible", timeout=60000)

            logger.info("Clicking 'Synced to main' button...")
            await page.get_by_role("button", name="Synced to main").click()

            logger.info("Clicking 'Pull Changes' button...")
            await page.get_by_role("button", name="Pull Changes").click()

            await page.get_by_text("Syncing Changes").wait_for(state="hidden", timeout=SYNC_WAIT * 1000)
            logger.info("Git pull changes completed successfully.")

            return {
                "status": "success",
                "message": "Git pull completed successfully"
            }

        except Exception as e:
            logger.error(f"Git pull failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
        finally:
            await page.close()

    async def publish_changes(self, context: BrowserContext, v0_chat_url: str) -> Dict[str, Any]:
        """Automate the publish process using an authenticated context."""
        page = await context.new_page()
        try:
            logger.info(f"Navigating to {v0_chat_url} for publishing...")
            await page.goto(v0_chat_url)
            await page.get_by_role("button", name="Publish").wait_for(state="visible", timeout=60000)

            logger.info("Clicking 'Publish' dropdown button...")
            await page.get_by_role("button", name="Publish").click()
            await page.wait_for_timeout(DROPDOWN_WAIT * 1000)

            publish_changes_option = page.get_by_text("Publish Changes")
            update_option = page.get_by_role("button", name="Update")

            if await publish_changes_option.is_visible():
                logger.info("'Publish Changes' option is visible. Clicking it...")
                await publish_changes_option.click()
                await page.get_by_text("Publishing...").wait_for(state="visible", timeout=60000)
                logger.info("Publishing in progress...")
                await page.get_by_text("Publishing...").wait_for(state="hidden", timeout=PUBLISH_WAIT * 1000)
                logger.info("Publishing completed successfully.")

                return {
                    "status": "success",
                    "message": "Changes published successfully"
                }

            elif await update_option.is_visible():
                logger.info("'Update' button is visible, which means changes are already published.")
                return {
                    "status": "success",
                    "message": "Changes already published (Update button visible)"
                }

            else:
                await page.screenshot(path="publish_error_snapshot.png")
                return {
                    "status": "error",
                    "error": "Could not find 'Publish Changes' or 'Update' in the publish dropdown. See publish_error_snapshot.png"
                }

        except Exception as e:
            logger.error(f"Publish failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
        finally:
            await page.close()

    async def view_app(self, context: BrowserContext, production_url: str, wait_seconds: int = VIEW_APP_WAIT) -> Dict[str, Any]:
        """Opens the production URL in a new tab."""
        page = await context.new_page()
        try:
            logger.info(f"Opening production app at {production_url}...")
            await page.goto(production_url)
            logger.info(f"App opened. Browser will remain open for {wait_seconds} seconds.")
            await page.wait_for_timeout(wait_seconds * 1000)

            return {
                "status": "success",
                "message": f"Viewed app at {production_url}"
            }

        except Exception as e:
            logger.error(f"View app failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
        finally:
            await page.close()


# Standalone helper functions
async def do_v0_login() -> Dict[str, Any]:
    """Standalone function: Authenticate to v0.dev and save session state."""
    automation = V0Automation()
    return await automation.login_v0()


async def do_v0_git_pull(v0_chat_url: str) -> Dict[str, Any]:
    """Standalone function: Pull changes from Git in v0.dev."""
    automation = V0Automation()

    if not STORAGE_STATE_PATH.exists():
        return {"status": "error", "error": "Not authenticated. Run v0_login first."}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(storage_state=str(STORAGE_STATE_PATH))

            result = await automation.git_pull_changes(context, v0_chat_url)

            await context.close()
            await browser.close()
            return result

    except Exception as e:
        logger.error(f"Error in v0_git_pull: {e}")
        return {"status": "error", "error": str(e)}


async def do_v0_publish(v0_chat_url: str) -> Dict[str, Any]:
    """Standalone function: Publish changes to Vercel from v0.dev."""
    automation = V0Automation()

    if not STORAGE_STATE_PATH.exists():
        return {"status": "error", "error": "Not authenticated. Run v0_login first."}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(storage_state=str(STORAGE_STATE_PATH))

            result = await automation.publish_changes(context, v0_chat_url)

            await context.close()
            await browser.close()
            return result

    except Exception as e:
        logger.error(f"Error in v0_publish: {e}")
        return {"status": "error", "error": str(e)}


async def do_v0_view_app(production_url: str, wait_seconds: int = VIEW_APP_WAIT) -> Dict[str, Any]:
    """Standalone function: View production application in browser."""
    automation = V0Automation()

    if not STORAGE_STATE_PATH.exists():
        return {"status": "error", "error": "Not authenticated. Run v0_login first."}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(storage_state=str(STORAGE_STATE_PATH))

            result = await automation.view_app(context, production_url, wait_seconds)

            await context.close()
            await browser.close()
            return result

    except Exception as e:
        logger.error(f"Error in v0_view_app: {e}")
        return {"status": "error", "error": str(e)}


async def do_v0_deploy(v0_chat_url: str, production_url: str, view: bool = False) -> Dict[str, Any]:
    """Standalone function: Complete deployment workflow (git pull + publish + optional view)."""
    automation = V0Automation()

    if not STORAGE_STATE_PATH.exists():
        return {"status": "error", "error": "Not authenticated. Run v0_login first."}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(storage_state=str(STORAGE_STATE_PATH))

            logger.info("--- Starting Deployment ---")

            logger.info("\nStep 1: Pulling Git Changes...")
            pull_result = await automation.git_pull_changes(context, v0_chat_url)

            if pull_result["status"] != "success":
                await context.close()
                await browser.close()
                return pull_result

            logger.info("\nStep 2: Publishing Changes...")
            publish_result = await automation.publish_changes(context, v0_chat_url)

            if publish_result["status"] != "success":
                await context.close()
                await browser.close()
                return publish_result

            view_result = None
            if view:
                logger.info("\nStep 3: Opening Production App...")
                view_result = await automation.view_app(context, production_url)

            logger.info("--- Deployment Finished ---")

            await context.close()
            await browser.close()

            return {
                "status": "success",
                "pull": pull_result,
                "publish": publish_result,
                "view": view_result
            }

    except Exception as e:
        logger.error(f"Error in v0_deploy: {e}")
        return {"status": "error", "error": str(e)}


# ============================================================================
# MCP TOOLS
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
async def v0_view_app(production_url: str, wait_seconds: int = VIEW_APP_WAIT) -> dict:
    """Open production application in browser for testing."""
    logger.info(f"Viewing app: {production_url}")
    return await do_v0_view_app(production_url, wait_seconds)


@mcp.tool()
async def v0_deploy(v0_chat_url: str, production_url: str, view: bool = False) -> dict:
    """Complete deployment workflow: pull from Git, publish to Vercel, and optionally view app."""
    logger.info("Running complete deployment workflow...")
    return await do_v0_deploy(v0_chat_url, production_url, view)


# ============================================================================
# MCP RESOURCES (Documentation)
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
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("v0 Deployer MCP Server - Starting...")
    logger.info("=" * 60)
    logger.info("Available tools:")
    logger.info("  - v0_login")
    logger.info("  - v0_git_pull")
    logger.info("  - v0_publish")
    logger.info("  - v0_view_app")
    logger.info("  - v0_deploy")
    logger.info("Available resources:")
    logger.info("  - v0://docs/deployment-workflow")
    logger.info("  - v0://docs/agent-collaboration")
    logger.info("  - v0://docs/build-integrity")
    logger.info("=" * 60)
    mcp.run()
