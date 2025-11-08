"""
AI Studio MCP Server

A comprehensive Model Context Protocol server for Google AI Studio automation.
Provides tools, resources, and prompts for end-to-end development workflows.

Components:
- Tools: 5 automation functions (login, create_repo, commit_deploy, clone, wait)
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
    ImageContent,
    EmbeddedResource,
    Prompt,
    PromptArgument,
    PromptMessage,
    GetPromptResult,
)

from .automation import (
    AIStudioAutomation,
    aistudio_create_github_repo,
    aistudio_commit_and_deploy,
)
from .config import STORAGE_STATE_PATH, DOCS_PATH

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server
app = Server("aistudio")


# ============================================================================
# RESOURCES - Documentation accessible via MCP
# ============================================================================

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List all available documentation resources."""
    resources = []

    # Main documentation files
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

    for key, filename in doc_files.items():
        file_path = DOCS_PATH / filename
        if file_path.exists():
            # Read first 500 chars for description
            content = file_path.read_text(encoding="utf-8")
            description = content[:500].split('\n')[0] if content else f"Documentation: {key}"

            resources.append(
                Resource(
                    uri=f"aistudio://docs/{key}",
                    name=f"AI Studio: {key.replace('-', ' ').title()}",
                    mimeType="text/markdown",
                    description=description,
                )
            )

    return resources


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read documentation resource content."""
    if not uri.startswith("aistudio://docs/"):
        raise ValueError(f"Unknown resource: {uri}")

    # Extract doc key from URI
    doc_key = uri.replace("aistudio://docs/", "")

    # Map to filename
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

@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List all available workflow prompts."""
    return [
        Prompt(
            name="create-new-project",
            description="Complete workflow for creating a brand new AI Studio project from scratch, including authentication, project creation, GitHub setup, and deployment",
            arguments=[
                PromptArgument(
                    name="project_name",
                    description="Name for the AI Studio project (will be prefixed with UUID)",
                    required=True,
                ),
                PromptArgument(
                    name="project_description",
                    description="Description of what the project should do",
                    required=True,
                ),
                PromptArgument(
                    name="google_cloud_project",
                    description="Google Cloud Project ID for deployment",
                    required=True,
                ),
            ],
        ),
        Prompt(
            name="enhance-existing-project",
            description="Workflow for enhancing an existing AI Studio project with new features or bug fixes",
            arguments=[
                PromptArgument(
                    name="app_url",
                    description="URL to the AI Studio project edit page",
                    required=True,
                ),
                PromptArgument(
                    name="enhancement_description",
                    description="Description of the enhancement or fix to implement",
                    required=True,
                ),
                PromptArgument(
                    name="google_cloud_project",
                    description="Google Cloud Project ID for deployment",
                    required=True,
                ),
            ],
        ),
        Prompt(
            name="add-ai-features",
            description="Add AI capabilities (voice, chatbot, TTS, etc.) to an AI Studio project",
            arguments=[
                PromptArgument(
                    name="app_url",
                    description="URL to the AI Studio project edit page",
                    required=True,
                ),
                PromptArgument(
                    name="features",
                    description="Comma-separated list of AI features to add (e.g., 'voice-input,chatbot,text-to-speech')",
                    required=True,
                ),
            ],
        ),
        Prompt(
            name="troubleshoot-workflow",
            description="Debug and fix common AI Studio workflow issues",
            arguments=[
                PromptArgument(
                    name="issue_description",
                    description="Description of the issue you're experiencing",
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

    if name == "create-new-project":
        project_name = arguments.get("project_name", "")
        project_description = arguments.get("project_description", "")
        google_cloud_project = arguments.get("google_cloud_project", "")

        return GetPromptResult(
            description=f"Create new AI Studio project: {project_name}",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""# Create New AI Studio Project: {project_name}

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
2. Draft implementation prompt using RISE framework:
   - **Result**: What the application should accomplish
   - **Implementation**: Key features and technologies
   - **Success Criteria**: How to verify it works
   - **Environment**: Deployment target (Cloud Run)

3. Send prompt to Gemini for implementation
4. Use `aistudio_wait_for_implementation` tool (minimum 90 seconds)
5. Verify implementation is complete

### Phase 3: Repository Setup
1. Edit project name with UUID prefix for traceability
2. Use `aistudio_create_repo` tool:
   - repo_name: [UUID]-{project_name}
   - description: {project_description}
   - visibility: private

### Phase 4: Deployment
1. Use `aistudio_commit_and_deploy` tool:
   - commit_message: "Initial implementation: {project_description}"
   - google_cloud_project: {google_cloud_project}

### Phase 5: Local Setup
1. Use `aistudio_clone_repository` tool to clone locally
2. Review code structure and implementation
3. Create CLAUDE.md documentation file

### Phase 6: Iteration
1. Test deployed application
2. Identify any issues or enhancements
3. Use "enhance-existing-project" prompt for iterations

## Reference Documentation
- Read `aistudio://docs/workflow-new-project` for detailed guidance
- Read `aistudio://docs/best-practices-antipatterns` to avoid common mistakes
- Read `aistudio://docs/browser-automation-reference` for timing patterns

## Critical Success Factors
- ✅ Wait minimum 90 seconds for Gemini implementation
- ✅ Use UUID prefix for project name traceability
- ✅ Verify each phase completes before proceeding
- ✅ Test deployed application before marking complete
""",
                    ),
                ),
            ],
        )

    elif name == "enhance-existing-project":
        app_url = arguments.get("app_url", "")
        enhancement_description = arguments.get("enhancement_description", "")
        google_cloud_project = arguments.get("google_cloud_project", "")

        return GetPromptResult(
            description=f"Enhance AI Studio project with: {enhancement_description}",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""# Enhance Existing AI Studio Project

## Enhancement Details
**Project URL**: {app_url}
**Enhancement**: {enhancement_description}
**Deployment Target**: {google_cloud_project}

## Workflow Steps

### Step 1: Navigate to Project
1. Open AI Studio project at: {app_url}
2. Review current implementation

### Step 2: Request Enhancement
1. Craft enhancement prompt describing desired changes
2. Send to Gemini for implementation
3. Use `aistudio_wait_for_implementation` tool (minimum 90 seconds)

### Step 3: Commit Changes
1. Use `aistudio_commit_and_deploy` tool:
   - app_url: {app_url}
   - commit_message: "Enhancement: {enhancement_description}"
   - google_cloud_project: {google_cloud_project}

### Step 4: Verification
1. Wait for deployment to complete (~60 seconds)
2. Test deployed application
3. Verify enhancement is working as expected

## Reference Documentation
- Read `aistudio://docs/workflow-existing-project` for detailed guidance
- Read `aistudio://docs/best-practices-antipatterns` for common pitfalls

## Tips
- Be specific in enhancement descriptions
- Test thoroughly before marking complete
- Use issue tracking for larger features
""",
                    ),
                ),
            ],
        )

    elif name == "add-ai-features":
        app_url = arguments.get("app_url", "")
        features = arguments.get("features", "")

        return GetPromptResult(
            description=f"Add AI features to project: {features}",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""# Add AI Features to AI Studio Project

## Feature Request
**Project URL**: {app_url}
**Features to Add**: {features}

## Workflow Steps

### Step 1: Understand Available Features
Read `aistudio://docs/ai-features-catalog` to understand:
- Voice input/output capabilities
- Chatbot integration patterns
- Text-to-speech options
- Image/video processing
- Maps and location services
- Search integration

### Step 2: Craft Feature Prompt
Based on requested features ({features}), create implementation prompt:
1. Specify which AI capabilities to integrate
2. Define user experience for each feature
3. Include graceful degradation (e.g., iOS fallbacks)
4. Plan responsive UI placement

### Step 3: Implement Features
1. Navigate to {app_url}
2. Send feature implementation prompt to Gemini
3. Use `aistudio_wait_for_implementation` tool
4. Verify features are implemented

### Step 4: Deploy and Test
1. Commit and deploy changes
2. Test on desktop AND mobile devices
3. Verify iOS fallbacks work correctly
4. Ensure features don't obscure content

## Reference Documentation
- Read `aistudio://docs/ai-features-catalog` for complete feature catalog
- Read `aistudio://docs/llm-decision-guide` for decision-making guidance

## Feature-Specific Notes
- **Voice Input**: Requires Web Speech API (not supported on iOS)
- **Chatbots**: Need context awareness (current page, user intent)
- **TTS**: Should be optional and controllable by user
- **Multi-Feature**: Plan UI carefully to avoid clutter
""",
                    ),
                ),
            ],
        )

    elif name == "troubleshoot-workflow":
        issue_description = arguments.get("issue_description", "")

        return GetPromptResult(
            description=f"Troubleshoot issue: {issue_description}",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""# Troubleshoot AI Studio Workflow Issue

## Issue Description
{issue_description}

## Troubleshooting Steps

### Step 1: Identify Issue Category
Read `aistudio://docs/best-practices-antipatterns` to find matching issue:
- Timing-related issues (waiting too long/short)
- Dialog state problems (GitHub/Deploy dialogs)
- Element selection failures
- Authentication issues
- Deployment failures

### Step 2: Apply Recommended Solution
Each anti-pattern in the documentation includes:
- Symptoms of the issue
- Root cause explanation
- Step-by-step fix
- Prevention strategy

### Step 3: Verify Fix
After applying solution:
1. Re-run the failed workflow step
2. Verify it completes successfully
3. Continue with remaining workflow

### Step 4: Update Documentation
If you discover a new issue pattern:
1. Document the symptoms
2. Note the root cause
3. Describe the solution
4. Share for future reference

## Common Quick Fixes

**Authentication Issues**
- Run `aistudio_login` tool again
- Check STORAGE_STATE_PATH exists
- Verify browser allows cookies/storage

**Timing Issues**
- Increase wait time for Gemini implementation (90s minimum)
- Add 8-10s wait for dialog rendering
- Use verification retry patterns

**Element Not Found**
- Read `aistudio://docs/browser-automation-reference`
- Try alternative selectors
- Add navigation wait time

**Deployment Failures**
- Check Google Cloud project permissions
- Verify project ID is correct
- Review Cloud Run logs

## Reference Documentation
- Read `aistudio://docs/best-practices-antipatterns` for complete troubleshooting guide
- Read `aistudio://docs/browser-automation-reference` for timing patterns
- Read `aistudio://docs/mcp-quick-reference` for quick lookups
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
            name="aistudio_login",
            description="Authenticate to Google AI Studio and save session state for reuse. Opens browser for manual login, then saves authentication state to ~/.playwright/aistudio_auth_state.json",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="aistudio_create_repo",
            description="Create GitHub repository for AI Studio project. Requires authenticated session. Opens GitHub dialog, fills in repository details, and creates the repo.",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_url": {
                        "type": "string",
                        "description": "Full URL to AI Studio project edit page (e.g., https://aistudio.google.com/apps/drive/[PROJECT-ID])",
                    },
                    "repo_name": {
                        "type": "string",
                        "description": "Repository name (should include UUID prefix for traceability)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Repository description",
                    },
                    "visibility": {
                        "type": "string",
                        "description": "Repository visibility: 'private' or 'public'",
                        "enum": ["private", "public"],
                        "default": "private",
                    },
                },
                "required": ["app_url", "repo_name", "description"],
            },
        ),
        Tool(
            name="aistudio_commit_and_deploy",
            description="Commit changes to GitHub and deploy to Google Cloud Run. Handles both commit and deployment in sequence. Wait ~60 seconds after calling for deployment to complete.",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_url": {
                        "type": "string",
                        "description": "Full URL to AI Studio project edit page",
                    },
                    "commit_message": {
                        "type": "string",
                        "description": "Git commit message describing the changes",
                    },
                    "google_cloud_project": {
                        "type": "string",
                        "description": "Google Cloud Project ID for deployment",
                    },
                    "issue_number": {
                        "type": "integer",
                        "description": "Optional GitHub issue number to reference in commit",
                    },
                },
                "required": ["app_url", "commit_message", "google_cloud_project"],
            },
        ),
        Tool(
            name="aistudio_clone_repository",
            description="Clone GitHub repository to local development environment. Uses git clone with depth=1 for faster cloning.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "GitHub repository URL (https or git@)",
                    },
                    "local_path": {
                        "type": "string",
                        "description": "Local directory path to clone into",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch to clone",
                        "default": "main",
                    },
                },
                "required": ["repo_url", "local_path"],
            },
        ),
        Tool(
            name="aistudio_wait_for_implementation",
            description="Wait for Gemini implementation to complete. CRITICAL: Minimum wait is 90 seconds. Polls for Stop button disappearance to verify completion. Typical duration: 2-5 minutes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_url": {
                        "type": "string",
                        "description": "URL to AI Studio project edit page",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Maximum wait time in seconds",
                        "default": 300,
                    },
                },
                "required": ["app_url"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute automation tool."""
    try:
        if name == "aistudio_login":
            logger.info("Starting AI Studio authentication...")
            automation = AIStudioAutomation()
            context, page = await automation.login_aistudio()
            await context.storage_state(path=str(STORAGE_STATE_PATH))
            await context.close()
            await page.context.browser.close()

            result = {
                "status": "success",
                "message": f"Authenticated to AI Studio. Session saved to {STORAGE_STATE_PATH}",
                "storage_state_path": str(STORAGE_STATE_PATH),
            }

        elif name == "aistudio_create_repo":
            logger.info(f"Creating repository: {arguments.get('repo_name')}")
            result = await aistudio_create_github_repo(
                app_url=arguments["app_url"],
                repo_name=arguments["repo_name"],
                description=arguments["description"],
                use_existing_auth=True,
            )

        elif name == "aistudio_commit_and_deploy":
            logger.info("Committing and deploying...")
            result = await aistudio_commit_and_deploy(
                app_url=arguments["app_url"],
                commit_message=arguments["commit_message"],
                google_cloud_project=arguments["google_cloud_project"],
                issue_number=arguments.get("issue_number"),
            )

        elif name == "aistudio_clone_repository":
            logger.info(f"Cloning repository: {arguments.get('repo_url')}")
            automation = AIStudioAutomation()
            result = await automation.clone_repository_locally(
                repo_url=arguments["repo_url"],
                local_path=Path(arguments["local_path"]),
                branch=arguments.get("branch", "main"),
            )

        elif name == "aistudio_wait_for_implementation":
            logger.info("Waiting for Gemini implementation...")
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context(storage_state=str(STORAGE_STATE_PATH))
                page = await context.new_page()
                await page.goto(arguments["app_url"])

                automation = AIStudioAutomation()
                result = await automation.wait_for_gemini_implementation(
                    page=page,
                    timeout_seconds=arguments.get("timeout_seconds", 300),
                )

                await context.close()
                await browser.close()

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
    # Import here to avoid issues with event loops
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        logger.info("AI Studio MCP Server starting...")
        logger.info("Available tools: aistudio_login, aistudio_create_repo, aistudio_commit_and_deploy, aistudio_clone_repository, aistudio_wait_for_implementation")
        logger.info("Available resources: 12 documentation files via aistudio://docs/*")
        logger.info("Available prompts: create-new-project, enhance-existing-project, add-ai-features, troubleshoot-workflow")
        await app.run(read_stream, write_stream, app.create_initialization_options())
