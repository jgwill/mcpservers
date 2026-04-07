"""
AI Studio Playwright Automation Helper

Provides reusable Playwright-based functions for automating Google AI Studio workflows.
Follows patterns from v0-playwright-helper.py for consistency and reliability.

Functions are exposed as MCP tools via the server module.

Module: mcp_server_aistudio.automation
Reference: llms-aistudio-01-workflow-new-project.md
Timing: Critical patterns from llms-aistudio-04-browser-automation-reference.md
"""

import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple, Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from .config import (
    STORAGE_STATE_PATH,
    USER_DATA_DIR,
    GEMINI_IMPLEMENTATION_WAIT,
    DIALOG_LOAD_WAIT,
    VERIFICATION_RETRY_WAIT,
    NAVIGATION_WAIT,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AIStudioAutomation:
    """
    Playwright-based automation for Google AI Studio workflows.

    Provides functions for:
    - Authentication and context management
    - Project creation and naming
    - GitHub integration (create repo, commit, deploy)
    - Local repository setup

    All timing patterns follow llms-aistudio-04-browser-automation-reference.md
    """

    def __init__(
        self,
        storage_state_path: Optional[Path] = None,
        user_data_dir: Optional[str] = None
    ):
        """Initialize automation helper with optional auth state or profile dir."""
        self.storage_state_path = storage_state_path or STORAGE_STATE_PATH
        self.user_data_dir = user_data_dir or USER_DATA_DIR
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def login_aistudio(self) -> Tuple[BrowserContext, Page]:
        """
        Initialize browser context and perform Google authentication.

        Returns:
            Tuple[BrowserContext, Page]: Authenticated context and page

        Process:
        1. Launch browser
        2. Create new context
        3. Navigate to AI Studio
        4. Wait for user to authenticate
        5. Return context/page for caller to save state and close
        """
        logger.info("Starting AI Studio authentication...")

        # Keep playwright instance alive in self
        self.playwright = await async_playwright().start()

        # Launch with persistent context (user-data-dir) for shared profile
        logger.info(f"📁 Using browser profile: {self.user_data_dir}")
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        self.browser = None  # Not used with persistent context

        # Navigate to AI Studio
        await self.page.goto("https://aistudio.google.com/apps?source=start")
        logger.info("📝 Navigated to AI Studio")
        logger.info("👤 Please authenticate in the browser window")
        logger.info("⏳ Waiting for authentication (this may take a few minutes)...")

        # Wait for successful authentication by looking for AI Studio app elements
        # The apps page will have specific elements when logged in
        try:
            # Wait for either:
            # 1. The "New" button (creates new project) - indicates logged in
            # 2. Or an existing app card - indicates logged in
            await self.page.wait_for_selector(
                'button:has-text("New"), [role="link"][href*="/apps/drive"]',
                timeout=300000  # 5 minutes for user to login
            )
            logger.info("✅ Authentication successful!")
        except Exception as e:
            logger.warning(f"Timeout waiting for authentication elements: {e}")
            logger.info("Proceeding anyway - please verify you're logged in")

        return self.context, self.page

    async def create_project_and_send_prompt(
        self,
        prompt: str,
        project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new AI Studio project and send initial prompt to Gemini.

        Automatically handles authentication if not already logged in.

        Args:
            prompt: The implementation prompt to send to Gemini
            project_name: Optional project name (will be auto-generated if not provided)

        Returns:
            Dict: Project URL, status, and metadata

        Process:
        1. Check if authenticated, if not run login flow
        2. Navigate to AI Studio apps page
        3. Click "New" button
        4. Wait for new project to load
        5. Send prompt to Gemini
        6. Extract project URL
        7. Return project details
        """
        logger.info("Creating new AI Studio project...")

        try:
            # Check if we need to authenticate first
            if not self.context or not self.page:
                logger.info("No active session - starting login flow...")
                await self.login_aistudio()
                logger.info("Login flow completed")

            # Verify we're actually logged in by checking the page
            logger.info(f"Checking authentication status at: {self.page.url}")

            # If we're on a login page, wait for user to authenticate
            if "accounts.google.com" in self.page.url or "login" in self.page.url.lower():
                logger.info("👤 Please log in to your Google account in the browser")
                logger.info("⏳ Waiting for authentication to complete...")

                # Wait for navigation away from login page
                try:
                    await self.page.wait_for_url("**/app**", timeout=300000)  # 5 min
                    logger.info("✅ Authentication completed")
                except:
                    # Also accept being on the apps page
                    if "aistudio.google.com" in self.page.url and "accounts.google.com" not in self.page.url:
                        logger.info("✅ Already authenticated")
                    else:
                        return {
                            "status": "error",
                            "error": "Authentication timeout - please try again"
                        }

            # Navigate to apps page
            await self.page.goto("https://aistudio.google.com/apps")
            await asyncio.sleep(NAVIGATION_WAIT)
            logger.info("Navigated to AI Studio apps page")

            # Close terms/privacy dialog if present
            try:
                agree_button = self.page.get_by_role('button', name='Agree')
                if await agree_button.is_visible(timeout=2000):
                    await agree_button.click()
                    logger.info("Clicked 'Agree' on terms dialog")
                    await asyncio.sleep(1)
            except:
                pass

            # Close "Got it" popup if present
            try:
                got_it_button = self.page.get_by_role('button', name='Got it')
                if await got_it_button.is_visible(timeout=2000):
                    await got_it_button.click()
                    logger.info("Closed 'Got it' popup")
                    await asyncio.sleep(1)
            except:
                pass

            # Fill prompt textbox
            logger.info(f"Filling prompt (length: {len(prompt)} chars)...")
            textbox = self.page.get_by_role('textbox', name='Enter a prompt to generate an')
            await textbox.fill(prompt)
            logger.info("Prompt filled")

            # Click "Build" button (becomes enabled after typing)
            build_button = self.page.get_by_role('button', name='Build', exact=True)
            await build_button.click()
            logger.info("Clicked 'Build' - Gemini implementation starting...")

            # Wait for URL to change to temp project
            logger.info("⏳ Waiting for temp project creation...")
            try:
                await self.page.wait_for_url("**/apps/temp/**", timeout=30000)
                logger.info("✅ Temp project created, Gemini implementing...")
            except:
                logger.warning("Didn't navigate to temp project")

            # Poll for completion: wait for "Finished" message or URL change to /apps/drive/
            logger.info("⏳ Waiting for Gemini to finish implementation (may take several minutes)...")
            max_wait = 600  # 10 minutes
            start_time = asyncio.get_event_loop().time()

            while (asyncio.get_event_loop().time() - start_time) < max_wait:
                current_url = self.page.url

                # CHECK FOR ERRORS FIRST
                try:
                    error_text = await self.page.get_by_text("An internal error occurred").is_visible(timeout=1000)
                    if error_text:
                        logger.error("❌ AIStudio internal error detected")
                        return {
                            "status": "error",
                            "error": "AIStudio internal error occurred during implementation",
                            "app_url": current_url
                        }
                except:
                    pass

                # Check if URL changed to permanent project
                if "/apps/drive/" in current_url:
                    logger.info("✅ URL changed to permanent project")
                    break

                # Check for "Finished" status text
                try:
                    if await self.page.get_by_text("Finished").is_visible(timeout=1000):
                        logger.info("✅ Gemini finished implementation")
                        await asyncio.sleep(3)  # Wait for URL to update
                        break
                except:
                    pass

                # Log progress every 30 seconds
                elapsed = int(asyncio.get_event_loop().time() - start_time)
                if elapsed % 30 == 0 and elapsed > 0:
                    logger.info(f"⏳ Still waiting... ({elapsed}s elapsed)")

                await asyncio.sleep(5)

            # Extract final project URL
            app_url = self.page.url
            if "/apps/drive/" in app_url:
                logger.info(f"📝 Project URL: {app_url}")
            else:
                logger.warning(f"⚠️  Implementation may not be complete. URL: {app_url}")

            # Optionally rename project if project_name provided
            if project_name:
                try:
                    # Look for project name field (usually at the top)
                    name_input = self.page.locator('input[placeholder*="name" i], input[aria-label*="name" i]').first
                    if await name_input.is_visible(timeout=3000):
                        await name_input.fill(project_name)
                        logger.info(f"Set project name to: {project_name}")
                except Exception as e:
                    logger.warning(f"Could not set project name: {e}")

            return {
                "status": "success",
                "app_url": app_url,
                "prompt_sent": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                "created_at": datetime.now().isoformat(),
                "next_step": "wait_for_implementation"
            }

        except Exception as e:
            logger.error(f"Error creating project: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def open_github_panel(self, context: BrowserContext, app_url: str) -> Page:
        """
        Navigate to AI Studio app and click 'Save to GitHub' button.

        Args:
            context: Authenticated Playwright context
            app_url: Full URL to AI Studio project (e.g.,
                    https://aistudio.google.com/apps/drive/[PROJECT-ID]?source=start)

        Returns:
            Page: Page object with GitHub panel visible

        Timing:
        - Navigation wait: 3 seconds
        - Dialog load wait: 8-10 seconds
        """
        logger.info(f"Opening GitHub panel for app: {app_url}")

        page = await context.new_page()
        await page.goto(app_url)
        await asyncio.sleep(NAVIGATION_WAIT)

        # Click "Save to GitHub" button
        save_to_github_btn = page.locator('button', has_text="Save to GitHub")
        await save_to_github_btn.click()
        logger.info("Clicked 'Save to GitHub' button")

        # Wait for GitHub panel to fully load
        logger.info(f"Waiting {DIALOG_LOAD_WAIT} seconds for GitHub dialog to render...")
        await asyncio.sleep(DIALOG_LOAD_WAIT)

        # Verify GitHub dialog is ready
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
        """
        Fill in GitHub repository creation form and click Create.

        Args:
            page: Playwright page with GitHub panel visible
            repo_name: Repository name (e.g., 178ca256-...-visioning-circle-companion)
            description: Repository description
            visibility: "private" or "public" (default: "private")

        Returns:
            Dict: Status and metadata about created repository

        Process:
        1. Fill repository name field
        2. Fill description field
        3. Set visibility (private/public)
        4. Click "Create Git repo" button
        5. Wait 5-10 seconds for repository creation
        """
        logger.info(f"Creating GitHub repository: {repo_name}")

        try:
            # Find and fill repository name input
            repo_name_input = page.locator('input[placeholder*="Repository name"]').first
            await repo_name_input.fill(repo_name)
            logger.info(f"Filled repository name: {repo_name}")

            # Find and fill description textarea
            desc_input = page.locator('textarea[placeholder*="description"]').first
            await desc_input.fill(description)
            logger.info(f"Filled description: {description[:50]}...")

            # Set visibility to Private (should be default)
            # Look for private radio button/checkbox and ensure it's selected
            private_option = page.locator('label:has-text("Private")')
            if await private_option.is_visible():
                await private_option.click()
                logger.info("Set visibility to Private")

            # Click "Create Git repo" button
            create_repo_btn = page.locator('button', has_text="Create Git repo")
            await create_repo_btn.click()
            logger.info("Clicked 'Create Git repo' button")

            # Wait for repository creation to complete
            logger.info(f"Waiting {VERIFICATION_RETRY_WAIT * 2} seconds for repo creation...")
            await asyncio.sleep(VERIFICATION_RETRY_WAIT * 2)

            # Verify repository was created (look for success indicator or next step)
            # In AI Studio, after repo creation, should see commit message prompt
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
        """
        Complete the commit workflow after repository creation.

        Args:
            page: Playwright page with commit prompt visible
            commit_message: Custom commit message (or will use default)
            issue_number: GitHub issue number for reference (e.g., 1)

        Returns:
            Dict: Status of commit operation

        Process:
        1. Wait for commit message prompt to appear
        2. Fill commit message textarea
        3. Click "Stage and commit all changes" button
        4. Wait for commit completion
        """
        logger.info(f"Committing to GitHub with message: {commit_message[:50]}...")

        try:
            # Fill commit message
            # The message field may be a textarea in the GitHub panel
            commit_input = page.locator('textarea').first
            await commit_input.fill(commit_message)
            logger.info("Filled commit message")

            # Click "Stage and commit all changes" button
            stage_commit_btn = page.locator('button', has_text="Stage and commit all changes")
            await stage_commit_btn.click()
            logger.info("Clicked 'Stage and commit all changes' button")

            # Wait for commit to process
            await asyncio.sleep(VERIFICATION_RETRY_WAIT)

            # Look for completion indicator (commit dialog disappears or success message)
            try:
                # Wait for the dialog to close or change state
                await page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass  # May timeout but that's okay, we'll check manually

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
        """
        Deploy the generated app to Google Cloud Run.

        Args:
            page: Playwright page in AI Studio
            google_cloud_project: Google Cloud project ID

        Returns:
            Dict: Deployment status and URL

        Process:
        1. Close GitHub dialog
        2. Click "Deploy app" button
        3. Wait for deploy dialog to load
        4. Select Google Cloud project
        5. Click deploy button
        6. Wait for deployment to complete
        7. Capture deployed URL
        """
        logger.info(f"Deploying application to Google Cloud project: {google_cloud_project}")

        try:
            # Close GitHub dialog
            close_btn = page.locator('button[aria-label*="Close"]').first
            if await close_btn.is_visible():
                await close_btn.click()
                logger.info("Closed GitHub dialog")

            await asyncio.sleep(VERIFICATION_RETRY_WAIT)

            # Click "Deploy app" button
            deploy_btn = page.locator('button[aria-label="Deploy app"]')
            await deploy_btn.click()
            logger.info("Clicked 'Deploy app' button")

            # Wait for deploy dialog to load
            logger.info(f"Waiting {DIALOG_LOAD_WAIT} seconds for deploy dialog...")
            await asyncio.sleep(DIALOG_LOAD_WAIT)

            # Select Google Cloud project from dropdown
            project_selector = page.locator('[role="combobox"]').first
            if await project_selector.is_visible():
                await project_selector.click()
                await asyncio.sleep(1)

                # Find and click project option
                project_option = page.locator(f'option:has-text("{google_cloud_project}")')
                if await project_option.is_visible():
                    await project_option.click()
                    logger.info(f"Selected Google Cloud project: {google_cloud_project}")

            # Click deploy/redeploy button
            redeploy_btn = page.locator('button', has_text="Redeploy").first
            if await redeploy_btn.is_visible():
                await redeploy_btn.click()
                logger.info("Clicked 'Redeploy' button - deployment started")

            # Wait for deployment to complete
            # Typically takes 30 seconds to 2 minutes
            logger.info("Waiting for deployment to complete (this may take 1-2 minutes)...")
            await asyncio.sleep(60)  # Wait at least 1 minute

            # Try to extract deployed URL from page
            deployed_url = None
            page_text = await page.text_content('body')

            # Look for deployed URL pattern (https://[name].run.app)
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
        """
        Git clone the created repository to local development environment.

        Args:
            repo_url: GitHub repository URL (https or git@)
            local_path: Local directory to clone into
            branch: Branch to clone (default: "main")

        Returns:
            Dict: Clone status and path

        Uses: subprocess for git operations
        """
        logger.info(f"Cloning repository: {repo_url}")

        try:
            # Ensure local path exists
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Clone repository
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

            # Verify clone
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
        """
        Verify that Gemini implementation is complete.

        Critical timing pattern from llms-aistudio-04-browser-automation-reference.md:
        - Minimum wait: 90 seconds
        - Typical: 2-5 minutes
        - Check every 30 seconds until Stop button disappears

        Args:
            page: Playwright page with Gemini processing
            timeout_seconds: Maximum wait time (default: 5 minutes)

        Returns:
            Dict: Completion status and duration
        """
        logger.info(f"Waiting for Gemini implementation (min {GEMINI_IMPLEMENTATION_WAIT}s)...")

        # Initial wait (critical!)
        await asyncio.sleep(GEMINI_IMPLEMENTATION_WAIT)
        logger.info(f"Initial {GEMINI_IMPLEMENTATION_WAIT}s wait complete")

        start_time = datetime.now()
        elapsed = 0

        while elapsed < timeout_seconds:
            try:
                # Check for Stop button (indicates still processing)
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

                # Still processing, wait and check again
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

    async def cleanup(self):
        """Close browser and clean up resources."""
        if self.context:
            await self.context.close()
            logger.info("Closed browser context")
        if self.browser:
            await self.browser.close()
            logger.info("Closed browser")


# Standalone functions for MCP tool wrapping
async def aistudio_create_github_repo(
    app_url: str,
    repo_name: str,
    description: str,
    use_existing_auth: bool = True
) -> Dict[str, Any]:
    """
    Standalone function: Create GitHub repository for AI Studio project.

    This function can be wrapped as an MCP tool.

    Args:
        app_url: Full URL to AI Studio project
        repo_name: Repository name
        description: Repository description
        use_existing_auth: Use saved authentication state

    Returns:
        Dict: Repository creation status
    """
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
    """
    Standalone function: Commit to GitHub and deploy to Cloud Run.

    This function can be wrapped as an MCP tool.

    Args:
        app_url: Full URL to AI Studio project
        commit_message: Commit message
        google_cloud_project: Google Cloud project ID
        issue_number: Optional GitHub issue number

    Returns:
        Dict: Combined commit and deployment status
    """
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

            # Commit
            commit_result = await automation.commit_to_github(
                page, commit_message, issue_number
            )

            # Deploy
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


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "login":
        # Run authentication
        async def run_login():
            automation = AIStudioAutomation()
            context, page = await automation.login_aistudio()
            await context.close()
            await page.context.browser.close()

        asyncio.run(run_login())
    else:
        print("AI Studio Playwright Automation Helper")
        print("Usage: python aistudio-playwright-helper.py [login|...]")
        print("\nRun 'python aistudio-playwright-helper.py login' to authenticate")
