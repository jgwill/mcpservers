#!/usr/bin/env python3
"""
AI Studio MCP Server

A comprehensive Model Context Protocol server for Google AI Studio automation.
Uses FastMCP for simplicity and reliability.

Provides tools, resources, and prompts for end-to-end development workflows.
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
    AIStudioAutomation,
    aistudio_create_github_repo,
    aistudio_commit_and_deploy,
)
from .config import STORAGE_STATE_PATH, DOCS_PATH

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP(name="aistudio")


# ============================================================================
# TOOLS - Automation functions
# ============================================================================

@mcp.tool()
async def aistudio_login() -> dict:
    """Authenticate to Google AI Studio and save session state."""
    logger.info("Starting AI Studio authentication...")
    automation = AIStudioAutomation()
    try:
        context, page = await automation.login_aistudio()

        # With persistent context, profile is auto-saved
        # No need to save storage_state separately
        logger.info(f"✅ Session persisted in browser profile: {automation.user_data_dir}")

        # Clean up
        await context.close()
        if automation.browser:
            await automation.browser.close()
        await automation.playwright.stop()

        return {
            "status": "success",
            "message": f"Authenticated to AI Studio. Profile saved to {automation.user_data_dir}",
            "user_data_dir": str(automation.user_data_dir)
        }
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        # Try to cleanup on error
        try:
            if automation.context:
                await automation.context.close()
            if automation.browser:
                await automation.browser.close()
            if automation.playwright:
                await automation.playwright.stop()
        except:
            pass
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
async def aistudio_create_project(
    prompt: str,
    project_name: Optional[str] = None
) -> dict:
    """Create new AI Studio project and send initial prompt to Gemini."""
    logger.info(f"Creating new AI Studio project: {project_name or '(auto-generated)'}")
    try:
        automation = AIStudioAutomation()

        # Use existing persistent context (from previous login)
        # Launch persistent context
        automation.playwright = await asyncio.get_event_loop().run_in_executor(
            None, lambda: asyncio.run(async_playwright().start())
        )
        # Actually, we need to properly start playwright
        from playwright.async_api import async_playwright
        automation.playwright = await async_playwright().start()

        logger.info(f"📁 Using browser profile: {automation.user_data_dir}")
        automation.context = await automation.playwright.chromium.launch_persistent_context(
            user_data_dir=automation.user_data_dir,
            headless=False
        )
        automation.page = automation.context.pages[0] if automation.context.pages else await automation.context.new_page()

        # Create project and send prompt
        result = await automation.create_project_and_send_prompt(
            prompt=prompt,
            project_name=project_name
        )

        # Keep context open for subsequent operations (wait_for_implementation, etc.)
        # Don't close yet
        logger.info(f"Project creation result: {result}")
        logger.info("⚠️  Browser context kept open - close manually or use cleanup command")

        return result
    except Exception as e:
        logger.error(f"Project creation failed: {e}")
        # Try to cleanup on error
        try:
            if automation.context:
                await automation.context.close()
            if automation.playwright:
                await automation.playwright.stop()
        except:
            pass
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
        from playwright.async_api import async_playwright

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
# RESOURCES - Documentation accessible via MCP
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
        "legacy-workflow-new-project": "legacy-workflow-new-project.md",
        "legacy-workflow": "legacy-workflow.md",
        "legacy-ai-features-exploration": "legacy-ai-features-exploration.md",
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
async def create_new_project(
    project_name: str,
    project_description: str,
    google_cloud_project: str
) -> str:
    """Complete workflow for creating a brand new AI Studio project from scratch."""
    return f"""# Create New AI Studio Project: {project_name}

## Project Overview
**Name**: {project_name}
**Description**: {project_description}
**Target Platform**: Google Cloud Run ({google_cloud_project})

## Workflow Steps

### Phase 1: Authentication
1. Use `aistudio_login` tool to authenticate to Google AI Studio
2. Verify authentication state is saved

### Phase 2: Project Creation & Implementation
1. Navigate to AI Studio and create new project
2. Draft implementation prompt using RISE framework
3. Send prompt to Gemini for implementation
4. Use `aistudio_wait_for_implementation` tool (minimum 90 seconds)

### Phase 3: Repository Setup
1. Edit project name with UUID prefix for traceability
2. Use `aistudio_create_repo` tool

### Phase 4: Deployment
1. Use `aistudio_commit_and_deploy` tool

### Phase 5: Local Setup
1. Use `aistudio_clone_repository` tool

## Reference Documentation
- Read aistudio://docs/workflow-new-project for detailed guidance
"""


@mcp.prompt()
async def enhance_existing_project(
    app_url: str,
    enhancement_description: str,
    google_cloud_project: str
) -> str:
    """Workflow for enhancing an existing AI Studio project."""
    return f"""# Enhance Existing AI Studio Project

## Enhancement Details
**Project URL**: {app_url}
**Enhancement**: {enhancement_description}
**Deployment Target**: {google_cloud_project}

## Workflow Steps
1. Navigate to project and describe enhancement to Gemini
2. Use `aistudio_wait_for_implementation` tool
3. Use `aistudio_commit_and_deploy` tool
4. Verify deployed application
"""


def main():
    """Main entry point for the server - this is a regular function, not async."""
    logger.info("AI Studio MCP Server starting...")
    logger.info("Available tools: aistudio_login, aistudio_create_project, aistudio_create_repo, aistudio_commit_and_deploy, aistudio_clone_repository, aistudio_wait_for_implementation")
    logger.info("Available resources: Documentation via aistudio://docs/*")
    logger.info("Available prompts: create-new-project, enhance-existing-project")
    mcp.run()


if __name__ == "__main__":
    main()
