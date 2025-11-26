#!/usr/bin/env python3
"""
AI Studio MCP Server - Standalone Version

Uses FastMCP for simplicity. Can be run directly without installation.
Provides tools, resources, and prompts for Google AI Studio automation.

Usage:
    python aistudio_mcp_server.py

Or in .mcp.json:
{
  "mcpServers": {
    "aistudio": {
      "command": "python",
      "args": ["/path/to/aistudio_mcp_server.py"]
    }
  }
}
"""

import asyncio
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple, Any

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: mcp package not found. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration constants
STORAGE_STATE_PATH = Path.home() / ".playwright" / "aistudio_auth_state.json"
STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

DOCS_PATH = Path(__file__).parent / "docs"

# Critical timing patterns
GEMINI_IMPLEMENTATION_WAIT = 90  # Seconds
DIALOG_LOAD_WAIT = 8  # Seconds
VERIFICATION_RETRY_WAIT = 3  # Seconds
NAVIGATION_WAIT = 3  # Seconds

# Create FastMCP server
mcp = FastMCP(name="aistudio")


# ============================================================================
# AUTOMATION HELPERS
# ============================================================================

class AIStudioAutomation:
    """Playwright-based automation for Google AI Studio workflows."""

    def __init__(self, storage_state_path: Optional[Path] = None):
        self.storage_state_path = storage_state_path or STORAGE_STATE_PATH
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def login_aistudio(self) -> Tuple[BrowserContext, Page]:
        """Initialize browser context and perform Google authentication."""
        logger.info("Starting AI Studio authentication...")

        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=False)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

            await self.page.goto("https://aistudio.google.com/apps?source=start")
            logger.info("Navigate to AI Studio start page. Please authenticate if needed.")

            await self.page.wait_for_load_state("networkidle", timeout=30000)

            await self.context.storage_state(path=str(self.storage_state_path))
            logger.info(f"Authentication successful. State saved to {self.storage_state_path}")

            return self.context, self.page

    async def open_github_panel(self, context: BrowserContext, app_url: str) -> Page:
        """Navigate to AI Studio app and click 'Save to GitHub' button."""
        logger.info(f"Opening GitHub panel for app: {app_url}")

        page = await context.new_page()
        await page.goto(app_url)
        await asyncio.sleep(NAVIGATION_WAIT)

        save_to_github_btn = page.locator('button', has_text="Save to GitHub")
        await save_to_github_btn.click()
        logger.info("Clicked 'Save to GitHub' button")

        logger.info(f"Waiting {DIALOG_LOAD_WAIT} seconds for GitHub dialog to render...")
        await asyncio.sleep(DIALOG_LOAD_WAIT)

        stage_commit_btn = page.locator('button', has_text="Stage and commit all changes")
        is_ready = await stage_commit_btn.is_visible()

        if not is_ready:
            logger.warning("GitHub dialog not fully loaded, waiting additional time...")
            await asyncio.sleep(VERIFICATION_RETRY_WAIT)

        logger.info("GitHub panel ready")
        return page

    async def create_github_repo(
        self,
        page: Page,
        repo_name: str,
        description: str,
        visibility: str = "private"
    ) -> Dict[str, Any]:
        """Fill in GitHub repository creation form and click Create."""
        logger.info(f"Creating GitHub repository: {repo_name}")

        try:
            repo_name_input = page.locator('input[placeholder*="Repository name"]').first
            await repo_name_input.fill(repo_name)
            logger.info(f"Filled repository name: {repo_name}")

            desc_input = page.locator('textarea[placeholder*="description"]').first
            await desc_input.fill(description)
            logger.info(f"Filled description: {description[:50]}...")

            private_option = page.locator('label:has-text("Private")')
            if await private_option.is_visible():
                await private_option.click()
                logger.info("Set visibility to Private")

            create_repo_btn = page.locator('button', has_text="Create Git repo")
            await create_repo_btn.click()
            logger.info("Clicked 'Create Git repo' button")

            logger.info(f"Waiting {VERIFICATION_RETRY_WAIT * 2} seconds for repo creation...")
            await asyncio.sleep(VERIFICATION_RETRY_WAIT * 2)

            commit_label = page.locator('text=Commit message').first
            is_ready = await commit_label.is_visible()

            return {
                "status": "success" if is_ready else "pending",
                "repo_name": repo_name,
                "created_at": datetime.now().isoformat(),
                "next_step": "commit_message" if is_ready else "verify_creation"
            }

        except Exception as e:
            logger.error(f"Error creating GitHub repository: {e}")
            return {
                "status": "error",
                "repo_name": repo_name,
                "error": str(e)
            }

    async def commit_to_github(
        self,
        page: Page,
        commit_message: str,
        issue_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Complete the commit workflow after repository creation."""
        logger.info(f"Committing to GitHub with message: {commit_message[:50]}...")

        try:
            commit_input = page.locator('textarea').first
            await commit_input.fill(commit_message)
            logger.info("Filled commit message")

            stage_commit_btn = page.locator('button', has_text="Stage and commit all changes")
            await stage_commit_btn.click()
            logger.info("Clicked 'Stage and commit all changes' button")

            await asyncio.sleep(VERIFICATION_RETRY_WAIT)

            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass

            logger.info("Commit completed")

            return {
                "status": "success",
                "message": commit_message,
                "issue_number": issue_number,
                "committed_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error committing to GitHub: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def deploy_to_cloud_run(
        self,
        page: Page,
        google_cloud_project: str
    ) -> Dict[str, Any]:
        """Deploy the generated app to Google Cloud Run."""
        logger.info(f"Deploying application to Google Cloud project: {google_cloud_project}")

        try:
            close_btn = page.locator('button[aria-label*="Close"]').first
            if await close_btn.is_visible():
                await close_btn.click()
                logger.info("Closed GitHub dialog")

            await asyncio.sleep(VERIFICATION_RETRY_WAIT)

            deploy_btn = page.locator('button[aria-label="Deploy app"]')
            await deploy_btn.click()
            logger.info("Clicked 'Deploy app' button")

            logger.info(f"Waiting {DIALOG_LOAD_WAIT} seconds for deploy dialog...")
            await asyncio.sleep(DIALOG_LOAD_WAIT)

            project_selector = page.locator('[role="combobox"]').first
            if await project_selector.is_visible():
                await project_selector.click()
                await asyncio.sleep(1)

                project_option = page.locator(f'option:has-text("{google_cloud_project}")')
                if await project_option.is_visible():
                    await project_option.click()
                    logger.info(f"Selected Google Cloud project: {google_cloud_project}")

            redeploy_btn = page.locator('button', has_text="Redeploy").first
            if await redeploy_btn.is_visible():
                await redeploy_btn.click()
                logger.info("Clicked 'Redeploy' button - deployment started")

            logger.info("Waiting for deployment to complete (this may take 1-2 minutes)...")
            await asyncio.sleep(60)

            deployed_url = None
            page_text = await page.text_content('body')

            import re
            url_pattern = r'https://[a-zA-Z0-9\-]+\.run\.app/?'
            matches = re.findall(url_pattern, page_text or '')
            if matches:
                deployed_url = matches[0]
                logger.info(f"Deployed URL: {deployed_url}")

            return {
                "status": "success",
                "project": google_cloud_project,
                "deployed_url": deployed_url,
                "deployed_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error deploying to Cloud Run: {e}")
            return {
                "status": "error",
                "project": google_cloud_project,
                "error": str(e)
            }

    async def clone_repository_locally(
        self,
        repo_url: str,
        local_path: Path,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """Git clone the created repository to local development environment."""
        logger.info(f"Cloning repository: {repo_url}")

        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)

            result = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", branch, repo_url, str(local_path)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                logger.error(f"Git clone failed: {result.stderr}")
                return {
                    "status": "error",
                    "repo_url": repo_url,
                    "error": result.stderr
                }

            logger.info(f"Repository cloned to: {local_path}")

            if (local_path / ".git").exists():
                return {
                    "status": "success",
                    "repo_url": repo_url,
                    "local_path": str(local_path),
                    "branch": branch,
                    "cloned_at": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "repo_url": repo_url,
                    "error": "Clone succeeded but .git directory not found"
                }

        except subprocess.TimeoutExpired:
            logger.error("Git clone timed out")
            return {
                "status": "error",
                "repo_url": repo_url,
                "error": "Clone operation timed out"
            }
        except Exception as e:
            logger.error(f"Error cloning repository: {e}")
            return {
                "status": "error",
                "repo_url": repo_url,
                "error": str(e)
            }

    async def wait_for_gemini_implementation(
        self,
        page: Page,
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """Verify that Gemini implementation is complete."""
        logger.info(f"Waiting for Gemini implementation (min {GEMINI_IMPLEMENTATION_WAIT}s)...")

        await asyncio.sleep(GEMINI_IMPLEMENTATION_WAIT)
        logger.info(f"Initial {GEMINI_IMPLEMENTATION_WAIT}s wait complete")

        start_time = datetime.now()
        elapsed = 0

        while elapsed < timeout_seconds:
            try:
                stop_btn = page.locator('button[aria-label*="Stop"]').first
                is_processing = await stop_btn.is_visible()

                if not is_processing:
                    duration = (datetime.now() - start_time).total_seconds()
                    logger.info(f"Implementation complete! Total wait time: {duration:.1f}s")

                    return {
                        "status": "complete",
                        "duration_seconds": duration,
                        "completed_at": datetime.now().isoformat()
                    }

                logger.info(f"Still processing... ({elapsed:.0f}s elapsed)")
                await asyncio.sleep(VERIFICATION_RETRY_WAIT)
                elapsed = (datetime.now() - start_time).total_seconds()

            except Exception as e:
                logger.warning(f"Error checking completion status: {e}")
                await asyncio.sleep(VERIFICATION_RETRY_WAIT)
                elapsed = (datetime.now() - start_time).total_seconds()

        logger.error(f"Implementation wait timeout after {timeout_seconds}s")
        return {
            "status": "timeout",
            "duration_seconds": timeout_seconds,
            "error": f"Implementation did not complete within {timeout_seconds} seconds"
        }


# Standalone helper functions
async def aistudio_create_github_repo(
    app_url: str,
    repo_name: str,
    description: str,
    use_existing_auth: bool = True
) -> Dict[str, Any]:
    """Standalone function: Create GitHub repository for AI Studio project."""
    automation = AIStudioAutomation()

    try:
        if use_existing_auth and STORAGE_STATE_PATH.exists():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context(
                    storage_state=str(STORAGE_STATE_PATH)
                )
                page = await automation.open_github_panel(context, app_url)
                result = await automation.create_github_repo(page, repo_name, description)
                await context.close()
                await browser.close()
                return result
        else:
            logger.error("No saved authentication state. Run login first.")
            return {"status": "error", "error": "Not authenticated"}

    except Exception as e:
        logger.error(f"Error in aistudio_create_github_repo: {e}")
        return {"status": "error", "error": str(e)}


async def aistudio_commit_and_deploy(
    app_url: str,
    commit_message: str,
    google_cloud_project: str,
    issue_number: Optional[int] = None
) -> Dict[str, Any]:
    """Standalone function: Commit to GitHub and deploy to Cloud Run."""
    automation = AIStudioAutomation()

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                storage_state=str(STORAGE_STATE_PATH)
            )
            page = await context.new_page()
            await page.goto(app_url)
            await asyncio.sleep(NAVIGATION_WAIT)

            commit_result = await automation.commit_to_github(
                page, commit_message, issue_number
            )

            deploy_result = await automation.deploy_to_cloud_run(
                page, google_cloud_project
            )

            await context.close()
            await browser.close()

            return {
                "status": "success",
                "commit": commit_result,
                "deployment": deploy_result
            }

    except Exception as e:
        logger.error(f"Error in aistudio_commit_and_deploy: {e}")
        return {"status": "error", "error": str(e)}


# ============================================================================
# MCP TOOLS
# ============================================================================

@mcp.tool()
async def aistudio_login() -> dict:
    """Authenticate to Google AI Studio and save session state."""
    logger.info("Starting AI Studio authentication...")
    try:
        automation = AIStudioAutomation()
        context, page = await automation.login_aistudio()

        await context.storage_state(path=str(STORAGE_STATE_PATH))
        await context.close()
        await page.context.browser.close()

        return {
            "status": "success",
            "message": f"Authenticated to AI Studio. Session saved to {STORAGE_STATE_PATH}",
            "storage_state_path": str(STORAGE_STATE_PATH)
        }
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
async def aistudio_create_repo(
    app_url: str,
    repo_name: str,
    description: str,
    visibility: str = "private"
) -> dict:
    """Create GitHub repository for AI Studio project."""
    logger.info(f"Creating repository: {repo_name}")
    try:
        result = await aistudio_create_github_repo(
            app_url=app_url,
            repo_name=repo_name,
            description=description,
            use_existing_auth=True
        )
        logger.info(f"Repository creation result: {result}")
        return result
    except Exception as e:
        logger.error(f"Repository creation failed: {e}")
        return {
            "status": "error",
            "repo_name": repo_name,
            "error": str(e)
        }


@mcp.tool()
async def aistudio_commit_and_deploy(
    app_url: str,
    commit_message: str,
    google_cloud_project: str,
    issue_number: Optional[int] = None
) -> dict:
    """Commit to GitHub and deploy to Cloud Run."""
    logger.info(f"Committing and deploying to {google_cloud_project}")
    try:
        result = await aistudio_commit_and_deploy(
            app_url=app_url,
            commit_message=commit_message,
            google_cloud_project=google_cloud_project,
            issue_number=issue_number
        )
        logger.info(f"Commit and deploy result: {result}")
        return result
    except Exception as e:
        logger.error(f"Commit and deploy failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
async def aistudio_clone_repository(
    repo_url: str,
    local_path: str,
    branch: str = "main"
) -> dict:
    """Clone GitHub repository locally."""
    logger.info(f"Cloning {repo_url} to {local_path}")
    try:
        automation = AIStudioAutomation()
        result = await automation.clone_repository_locally(
            repo_url=repo_url,
            local_path=Path(local_path),
            branch=branch
        )
        logger.info(f"Clone result: {result}")
        return result
    except Exception as e:
        logger.error(f"Clone failed: {e}")
        return {
            "status": "error",
            "repo_url": repo_url,
            "error": str(e)
        }


@mcp.tool()
async def aistudio_wait_for_implementation(
    app_url: str,
    timeout_seconds: int = 300
) -> dict:
    """Wait for Gemini implementation to complete."""
    logger.info(f"Waiting for implementation (max {timeout_seconds}s)")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                storage_state=str(STORAGE_STATE_PATH)
            )
            page = await context.new_page()
            await page.goto(app_url)

            automation = AIStudioAutomation()
            result = await automation.wait_for_gemini_implementation(
                page=page,
                timeout_seconds=timeout_seconds
            )

            await context.close()
            await browser.close()

            logger.info(f"Implementation wait result: {result}")
            return result
    except Exception as e:
        logger.error(f"Wait for implementation failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================================================
# MCP RESOURCES (Documentation)
# ============================================================================

@mcp.resource("aistudio://docs/{doc_key}")
async def get_documentation(doc_key: str) -> str:
    """Get AI Studio documentation by key."""
    doc_files = {
        "start-here": "00-start-here.md",
        "workflow-new-project": "01-workflow-new-project.md",
        "workflow-existing-project": "02-workflow-existing-project.md",
        "ai-features-catalog": "03-ai-features-catalog.md",
        "browser-automation-reference": "04-browser-automation-reference.md",
        "llm-decision-guide": "05-llm-decision-guide.md",
        "best-practices-antipatterns": "06-best-practices-antipatterns.md",
        "mcp-server-setup": "07-mcp-server-setup.md",
        "mcp-quick-reference": "08-mcp-quick-reference.md",
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
    logger.info("AI Studio MCP Server - Starting...")
    logger.info("=" * 60)
    logger.info("Available tools:")
    logger.info("  - aistudio_login")
    logger.info("  - aistudio_create_repo")
    logger.info("  - aistudio_commit_and_deploy")
    logger.info("  - aistudio_clone_repository")
    logger.info("  - aistudio_wait_for_implementation")
    logger.info("Available resources:")
    logger.info("  - aistudio://docs/start-here")
    logger.info("  - aistudio://docs/workflow-new-project")
    logger.info("  - aistudio://docs/* (see docs/ folder)")
    logger.info("=" * 60)
    mcp.run()
