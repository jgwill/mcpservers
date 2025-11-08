"""
v0.dev Playwright Automation Helper

Provides reusable Playwright-based functions for automating v0.dev deployment workflows.
Converted from standalone script to MCP-compatible module.

Functions are exposed as MCP tools via the server module.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError

from .config import (
    STORAGE_STATE_PATH,
    CONFIG_PATH,
    DROPDOWN_WAIT,
    SYNC_WAIT,
    PUBLISH_WAIT,
    VIEW_APP_WAIT,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Loads the configuration from the JSON file in the CWD."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")

    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


class V0Automation:
    """
    Playwright-based automation for v0.dev deployment workflows.

    Provides functions for:
    - Authentication and context management
    - Git pull from v0.dev
    - Publishing changes to Vercel
    - Viewing deployed applications

    All timing patterns follow v0.dev UI requirements.
    """

    def __init__(self, storage_state_path: Optional[Path] = None):
        """Initialize automation helper with optional auth state."""
        self.storage_state_path = storage_state_path or STORAGE_STATE_PATH
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def login_v0(self) -> Dict[str, Any]:
        """
        Initialize browser context and perform v0.dev authentication.

        Opens a browser for manual login and saves the session state for reuse.

        Returns:
            Dict: Status of authentication
        """
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
        """
        Automate the git pull process using an authenticated context.

        Args:
            context: Authenticated Playwright context
            v0_chat_url: URL to the v0.dev chat/project page

        Returns:
            Dict: Status of git pull operation
        """
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
        """
        Automate the publish process using an authenticated context.

        CRITICAL: The "Publish" button is a dropdown menu, not a single action.

        Args:
            context: Authenticated Playwright context
            v0_chat_url: URL to the v0.dev chat/project page

        Returns:
            Dict: Status of publish operation
        """
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
        """
        Opens the production URL in a new tab.

        Args:
            context: Authenticated Playwright context
            production_url: URL to the production application
            wait_seconds: How long to keep browser open (default: 60 seconds)

        Returns:
            Dict: Status of view operation
        """
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


# Standalone functions for MCP tool wrapping
async def v0_login() -> Dict[str, Any]:
    """
    Standalone function: Authenticate to v0.dev and save session state.

    This function can be wrapped as an MCP tool.

    Returns:
        Dict: Authentication status
    """
    automation = V0Automation()
    return await automation.login_v0()


async def v0_git_pull(v0_chat_url: str) -> Dict[str, Any]:
    """
    Standalone function: Pull changes from Git in v0.dev.

    Args:
        v0_chat_url: URL to the v0.dev chat/project page

    Returns:
        Dict: Git pull status
    """
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


async def v0_publish(v0_chat_url: str) -> Dict[str, Any]:
    """
    Standalone function: Publish changes to Vercel from v0.dev.

    Args:
        v0_chat_url: URL to the v0.dev chat/project page

    Returns:
        Dict: Publish status
    """
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


async def v0_view_app(production_url: str, wait_seconds: int = VIEW_APP_WAIT) -> Dict[str, Any]:
    """
    Standalone function: View production application in browser.

    Args:
        production_url: URL to the production application
        wait_seconds: How long to keep browser open

    Returns:
        Dict: View status
    """
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


async def v0_deploy(v0_chat_url: str, production_url: str, view: bool = False) -> Dict[str, Any]:
    """
    Standalone function: Complete deployment workflow (git pull + publish + optional view).

    Args:
        v0_chat_url: URL to the v0.dev chat/project page
        production_url: URL to the production application
        view: Whether to open and view the production app

    Returns:
        Dict: Combined deployment status
    """
    automation = V0Automation()

    if not STORAGE_STATE_PATH.exists():
        return {"status": "error", "error": "Not authenticated. Run v0_login first."}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(storage_state=str(STORAGE_STATE_PATH))

            logger.info("--- Starting Deployment ---")

            # Step 1: Pull changes
            logger.info("\nStep 1: Pulling Git Changes...")
            pull_result = await automation.git_pull_changes(context, v0_chat_url)

            if pull_result["status"] != "success":
                await context.close()
                await browser.close()
                return pull_result

            # Step 2: Publish
            logger.info("\nStep 2: Publishing Changes...")
            publish_result = await automation.publish_changes(context, v0_chat_url)

            if publish_result["status"] != "success":
                await context.close()
                await browser.close()
                return publish_result

            # Step 3: View app (optional)
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
