"""
v0 Deployer MCP Server

A comprehensive Model Context Protocol server for v0.dev deployment automation.
Provides tools, resources, and prompts for Vercel deployment workflows.

Components:
- Tools: 5 automation functions (login, git_pull, publish, view_app, deploy)
- Resources: All documentation accessible via MCP resources
- Prompts: Pre-configured workflows for common tasks
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    Prompt,
    PromptArgument,
    PromptMessage,
    GetPromptResult,
)

from .automation import (
    v0_login,
    v0_git_pull,
    v0_publish,
    v0_view_app,
    v0_deploy,
)
from .config import DOCS_PATH

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server
app = Server("v0deployer")


# ============================================================================
# RESOURCES - Documentation accessible via MCP
# ============================================================================

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List all available documentation resources."""
    resources = []

    doc_files = {
        "deployment-workflow": "deployment-workflow.md",
        "agent-collaboration": "agent-collaboration.md",
        "build-integrity": "build-integrity.md",
    }

    for key, filename in doc_files.items():
        file_path = DOCS_PATH / filename
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            description = content[:500].split('\n')[0] if content else f"Documentation: {key}"

            resources.append(
                Resource(
                    uri=f"v0://docs/{key}",
                    name=f"v0 Deployer: {key.replace('-', ' ').title()}",
                    mimeType="text/markdown",
                    description=description,
                )
            )

    return resources


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read documentation resource content."""
    if not uri.startswith("v0://docs/"):
        raise ValueError(f"Unknown resource: {uri}")

    doc_key = uri.replace("v0://docs/", "")

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

@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List all available workflow prompts."""
    return [
        Prompt(
            name="deploy-to-vercel",
            description="Complete deployment workflow: pull changes from Git, publish to Vercel, and optionally view the deployed app",
            arguments=[
                PromptArgument(
                    name="v0_chat_url",
                    description="URL to the v0.dev chat/project page (e.g., https://v0.app/chat/PROJECT_ID)",
                    required=True,
                ),
                PromptArgument(
                    name="production_url",
                    description="URL to the production application (e.g., https://myapp.vercel.app)",
                    required=True,
                ),
                PromptArgument(
                    name="view_after_deploy",
                    description="Whether to open the production app after deployment (true/false)",
                    required=False,
                ),
            ],
        ),
        Prompt(
            name="update-from-git",
            description="Pull latest changes from Git repository into v0.dev editor",
            arguments=[
                PromptArgument(
                    name="v0_chat_url",
                    description="URL to the v0.dev chat/project page",
                    required=True,
                ),
            ],
        ),
        Prompt(
            name="test-deployment",
            description="Test and verify a deployed Vercel application",
            arguments=[
                PromptArgument(
                    name="production_url",
                    description="URL to the production application to test",
                    required=True,
                ),
            ],
        ),
        Prompt(
            name="troubleshoot-deployment",
            description="Debug common v0.dev and Vercel deployment issues",
            arguments=[
                PromptArgument(
                    name="issue_description",
                    description="Description of the deployment issue",
                    required=True,
                ),
            ],
        ),
    ]


@app.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """Get a specific workflow prompt with arguments."""
    if arguments is None:
        arguments = {}

    if name == "deploy-to-vercel":
        v0_chat_url = arguments.get("v0_chat_url", "")
        production_url = arguments.get("production_url", "")
        view_after_deploy = arguments.get("view_after_deploy", "false").lower() == "true"

        return GetPromptResult(
            description=f"Deploy v0.dev project to Vercel",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""# Deploy v0.dev Project to Vercel

## Deployment Details
**v0.dev Project**: {v0_chat_url}
**Production URL**: {production_url}
**View After Deploy**: {view_after_deploy}

## Complete Deployment Workflow

### Step 1: Pull Changes from Git
Use `v0_git_pull` tool:
- v0_chat_url: {v0_chat_url}

This syncs your v0.dev workspace with the latest Git commits.

**Critical UI Pattern**:
- Click the "Synced to main" button (this is a dropdown)
- Select "Pull Changes" from the dropdown menu
- Wait for "Syncing Changes" indicator to disappear

### Step 2: Publish to Vercel
Use `v0_publish` tool:
- v0_chat_url: {v0_chat_url}

This commits changes to Git and triggers Vercel deployment.

**Critical UI Pattern**:
- Click the "Publish" button (this is a dropdown)
- Select "Publish Changes" from dropdown
- Wait for "Publishing..." indicator to complete (15-20 seconds)

### Step 3: Wait for Deployment
⏱️ **Timing**: Allow 15-20 seconds minimum after publish completes for Vercel deployment

Vercel deployment timeline:
- Seconds 0-5: Vercel receives push
- Seconds 5-30: Next.js build compiles
- Seconds 30-45: Tests and optimization
- Seconds 45-60: Deployment to CDN
- After 60s: App is live

### Step 4: Verify Deployment
Use `v0_view_app` tool:
- production_url: {production_url}
- wait_seconds: 60

**Testing Checklist**:
- [ ] App loads without errors
- [ ] Core features are functional
- [ ] Mobile responsiveness works
- [ ] No console errors in DevTools

### Alternative: All-in-One Deployment
Use `v0_deploy` tool for the complete workflow:
- v0_chat_url: {v0_chat_url}
- production_url: {production_url}
- view: {view_after_deploy}

This runs all steps in sequence automatically.

## Reference Documentation
- Read `v0://docs/deployment-workflow` for detailed UI patterns
- Read `v0://docs/build-integrity` for production build best practices

## Critical Success Factors
- ✅ Account for nested dropdown menus (GitHub and Publish buttons)
- ✅ Pull changes BEFORE publishing
- ✅ Wait for "Publishing..." to complete before testing
- ✅ Test on both desktop and mobile devices
- ✅ Verify deployment in Vercel dashboard
""",
                    ),
                ),
            ],
        )

    elif name == "update-from-git":
        v0_chat_url = arguments.get("v0_chat_url", "")

        return GetPromptResult(
            description="Pull latest Git changes into v0.dev",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""# Pull Latest Git Changes into v0.dev

## Project URL
{v0_chat_url}

## Workflow

### Step 1: Navigate to v0.dev Project
Open the v0.dev chat/editor at: {v0_chat_url}

### Step 2: Locate GitHub Integration Button
The GitHub button provides Git synchronization options.

**UI Location**: Toolbar/header area
**Visual**: GitHub logo (Octocat icon)
**Critical**: This is a DROPDOWN button, not just an icon

### Step 3: Open GitHub Dropdown
1. Click the GitHub icon/button
2. Dropdown menu appears with Git options
3. "Pull Changes" is nested in this menu

### Step 4: Pull Changes
Use `v0_git_pull` tool:
- v0_chat_url: {v0_chat_url}

**Expected Behavior**:
- Modal or notification confirms pull
- Recent commits from Git are now in v0.dev
- You can see latest code changes

**Timing**: 2-3 seconds for pull to complete

## Common Mistakes

❌ **Mistake**: Clicking GitHub icon but not opening dropdown
✅ **Solution**: Click the button itself to reveal dropdown menu

❌ **Mistake**: Publishing before pulling changes
✅ **Solution**: Always pull first, then publish

❌ **Mistake**: Not waiting for pull to complete
✅ **Solution**: Wait for "Syncing Changes" to disappear

## Reference Documentation
- Read `v0://docs/deployment-workflow` for detailed UI patterns
- Section #02-Step-by-Step: Pulling Changes from Git
""",
                    ),
                ),
            ],
        )

    elif name == "test-deployment":
        production_url = arguments.get("production_url", "")

        return GetPromptResult(
            description=f"Test deployed application at {production_url}",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""# Test Deployed Vercel Application

## Production URL
{production_url}

## Testing Workflow

### Step 1: Open Application
Use `v0_view_app` tool:
- production_url: {production_url}
- wait_seconds: 60

This opens the production app in a browser for inspection.

### Step 2: Desktop Testing Checklist
- [ ] App loads without errors (check DevTools console)
- [ ] Core features are functional
- [ ] Navigation works correctly
- [ ] Forms submit properly
- [ ] API calls succeed
- [ ] Images and assets load

### Step 3: Mobile Testing Checklist
- [ ] Open in mobile browser (iOS Safari, Chrome)
- [ ] Responsive layout works
- [ ] Touch interactions work
- [ ] Mobile-specific features function
- [ ] No horizontal scrolling
- [ ] Text is readable without zoom

### Step 4: Performance Checks
- [ ] Page load time < 3 seconds
- [ ] No layout shift (CLS)
- [ ] Smooth interactions
- [ ] No memory leaks

### Step 5: Error Checking
Open browser DevTools and verify:
- [ ] No console errors
- [ ] No 404 errors for assets
- [ ] No failed API calls
- [ ] No CSP violations

## Common Issues

**App shows old version**
- Deployment may still be in progress
- Wait 15-20 seconds and refresh
- Check Vercel dashboard for deployment status

**Features work in v0 but fail on live app**
- This is the "v0 environment vs. live app" confusion
- Always test the production URL, not v0 editor
- Check environment variables in Vercel

**Mobile-specific failures**
- Test on actual devices, not just responsive mode
- iOS may have Web Speech API limitations
- Check mobile-specific CSS and features

## Build Integrity

Before deployment, ensure:
- `npm run build` succeeds locally
- All TypeScript errors resolved
- All required environment variables set
- API routes correctly configured

Read `v0://docs/build-integrity` for complete pre-flight checklist.

## Reference Documentation
- Read `v0://docs/deployment-workflow` for deployment process
- Section #06-Testing on the Published Application
""",
                    ),
                ),
            ],
        )

    elif name == "troubleshoot-deployment":
        issue_description = arguments.get("issue_description", "")

        return GetPromptResult(
            description=f"Troubleshoot deployment issue",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""# Troubleshoot v0.dev Deployment Issue

## Issue Description
{issue_description}

## Troubleshooting Steps

### Step 1: Identify Issue Category

Read `v0://docs/deployment-workflow` to find matching issue:

**Common Issue Categories**:
1. **Nested UI Elements Not Clicked**
   - GitHub dropdown not opened
   - Publish dropdown not opened
   - Pull Changes not selected

2. **Timing Issues**
   - Testing before deployment completes
   - Publishing before pull completes
   - Not waiting for "Publishing..." indicator

3. **Authentication Issues**
   - Session expired
   - Not logged in to v0.dev
   - Storage state file missing

4. **Build Failures**
   - TypeScript errors
   - Missing dependencies
   - Environment variables not set

5. **Environment Confusion**
   - Testing in v0 editor instead of live app
   - Missing production environment variables
   - API routes not configured

### Step 2: Common Quick Fixes

**GitHub/Publish Button Not Working**
- These are DROPDOWN buttons
- Click the button to open dropdown
- Then click the actual action ("Pull Changes" or "Publish Changes")

**Authentication Failed**
- Run `v0_login` tool again
- Manually log in when browser opens
- Wait for "Projects" link to appear

**Deployment Times Out**
- Increase wait time (Publishing can take 180 seconds)
- Check Vercel dashboard for actual deployment status
- Look for build errors in Vercel logs

**Old Version Showing**
- Clear browser cache
- Wait 15-20 seconds after publish
- Check Vercel dashboard shows latest deployment

**Build Fails on Vercel**
- Read `v0://docs/build-integrity`
- Run `npm run build` locally
- Fix all TypeScript errors
- Verify all exports/imports
- Check React Server/Client boundaries

### Step 3: Apply Solution

Based on issue category, apply recommended fix:
1. Re-run failed workflow step
2. Use correct timing patterns
3. Verify authentication
4. Check build integrity

### Step 4: Verify Fix

After applying solution:
- Re-run the workflow
- Verify it completes successfully
- Test the deployed application
- Check for related issues

## Reference Documentation

**For UI Pattern Issues**:
- Read `v0://docs/deployment-workflow`
- Section #04-Understanding v0.dev UI Hierarchy
- Section #08-Common AI/Automation Mistakes

**For Build Issues**:
- Read `v0://docs/build-integrity`
- Section #3-The Pre-Flight Check
- Section #4-Common Anti-Patterns

**For Agent Collaboration**:
- Read `v0://docs/agent-collaboration`
- Section #7-Learnings from Debugging v0.dev Output
""",
                    ),
                ),
            ],
        )

    else:
        raise ValueError(f"Unknown prompt: {name}")


# ============================================================================
# TOOLS - Automation functions
# ============================================================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available automation tools."""
    return [
        Tool(
            name="v0_login",
            description="Authenticate to v0.dev and save session state for reuse. Opens browser for manual login (e.g., Passkey), then saves authentication state.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="v0_git_pull",
            description="Pull latest changes from Git repository into v0.dev editor. CRITICAL: The GitHub button is a dropdown - click it to reveal 'Pull Changes' option.",
            inputSchema={
                "type": "object",
                "properties": {
                    "v0_chat_url": {
                        "type": "string",
                        "description": "URL to the v0.dev chat/project page (e.g., https://v0.app/chat/PROJECT_ID)",
                    },
                },
                "required": ["v0_chat_url"],
            },
        ),
        Tool(
            name="v0_publish",
            description="Publish changes to Vercel from v0.dev. CRITICAL: The Publish button is a dropdown - click to open, then select 'Publish Changes'. Triggers Git commit and Vercel deployment. Wait 15-20 seconds for deployment to complete.",
            inputSchema={
                "type": "object",
                "properties": {
                    "v0_chat_url": {
                        "type": "string",
                        "description": "URL to the v0.dev chat/project page",
                    },
                },
                "required": ["v0_chat_url"],
            },
        ),
        Tool(
            name="v0_view_app",
            description="Open production application in browser for testing. Keeps browser open for specified duration to allow manual inspection.",
            inputSchema={
                "type": "object",
                "properties": {
                    "production_url": {
                        "type": "string",
                        "description": "URL to the production application (e.g., https://myapp.vercel.app)",
                    },
                    "wait_seconds": {
                        "type": "integer",
                        "description": "How long to keep browser open (default: 60 seconds)",
                        "default": 60,
                    },
                },
                "required": ["production_url"],
            },
        ),
        Tool(
            name="v0_deploy",
            description="Complete deployment workflow: pull from Git, publish to Vercel, and optionally view app. Runs all steps in sequence. Total time: ~40-60 seconds.",
            inputSchema={
                "type": "object",
                "properties": {
                    "v0_chat_url": {
                        "type": "string",
                        "description": "URL to the v0.dev chat/project page",
                    },
                    "production_url": {
                        "type": "string",
                        "description": "URL to the production application",
                    },
                    "view": {
                        "type": "boolean",
                        "description": "Whether to open and view the production app after deployment",
                        "default": False,
                    },
                },
                "required": ["v0_chat_url", "production_url"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute automation tool."""
    try:
        if name == "v0_login":
            logger.info("Starting v0.dev authentication...")
            result = await v0_login()

        elif name == "v0_git_pull":
            logger.info(f"Pulling Git changes for: {arguments.get('v0_chat_url')}")
            result = await v0_git_pull(arguments["v0_chat_url"])

        elif name == "v0_publish":
            logger.info(f"Publishing to Vercel: {arguments.get('v0_chat_url')}")
            result = await v0_publish(arguments["v0_chat_url"])

        elif name == "v0_view_app":
            logger.info(f"Viewing app: {arguments.get('production_url')}")
            result = await v0_view_app(
                arguments["production_url"],
                arguments.get("wait_seconds", 60)
            )

        elif name == "v0_deploy":
            logger.info("Running complete deployment workflow...")
            result = await v0_deploy(
                arguments["v0_chat_url"],
                arguments["production_url"],
                arguments.get("view", False)
            )

        else:
            result = {"status": "error", "error": f"Unknown tool: {name}"}

        import json
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        import json
        error_result = {"status": "error", "error": str(e)}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]


async def main():
    """Main entry point for the server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        logger.info("v0 Deployer MCP Server starting...")
        logger.info("Available tools: v0_login, v0_git_pull, v0_publish, v0_view_app, v0_deploy")
        logger.info("Available resources: 3 documentation files via v0://docs/*")
        logger.info("Available prompts: deploy-to-vercel, update-from-git, test-deployment, troubleshoot-deployment")
        await app.run(read_stream, write_stream, app.create_initialization_options())
