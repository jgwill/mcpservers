"""
CLI interface for AI Studio MCP Server

Provides command-line access to all MCP tools without requiring MCP client.
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from .automation import AIStudioAutomation, aistudio_create_github_repo, aistudio_commit_and_deploy
from .config import STORAGE_STATE_PATH
from .setup import ensure_playwright_setup, verify_dependencies

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_result(result: dict):
    """Pretty print result as JSON."""
    print(json.dumps(result, indent=2))


async def cmd_login(args):
    """Login to AI Studio."""
    logger.info("Starting AI Studio authentication...")
    automation = AIStudioAutomation()

    try:
        context, page = await automation.login_aistudio()
        await context.storage_state(path=str(STORAGE_STATE_PATH))
        await context.close()
        await page.context.browser.close()

        result = {
            "status": "success",
            "message": f"Authenticated successfully. Session saved to {STORAGE_STATE_PATH}",
            "storage_state_path": str(STORAGE_STATE_PATH)
        }
        print_result(result)
        return 0

    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        result = {"status": "error", "error": str(e)}
        print_result(result)
        return 1


async def cmd_create_project(args):
    """Create new AI Studio project (handles login automatically if needed)."""
    logger.info(f"Creating project with prompt from: {args.prompt_file}")

    try:
        # Read prompt from file
        prompt_file = Path(args.prompt_file)
        if not prompt_file.exists():
            logger.error(f"Prompt file not found: {args.prompt_file}")
            return 1

        prompt = prompt_file.read_text(encoding="utf-8")
        logger.info(f"Read prompt ({len(prompt)} chars)")

        # Initialize automation (it will handle login automatically)
        automation = AIStudioAutomation()

        # Create project and send prompt (login handled internally)
        result = await automation.create_project_and_send_prompt(
            prompt=prompt,
            project_name=args.project_name
        )

        print_result(result)

        if result.get("status") == "success":
            print(f"\n📝 Project URL: {result.get('app_url')}")
            print("⚠️  Browser window left open for you to monitor Gemini implementation")
            print("💡 Use 'aistudio-mcp wait' to wait for completion, or close browser when done")

        return 0 if result.get("status") == "success" else 1

    except Exception as e:
        logger.error(f"Project creation failed: {e}")
        result = {"status": "error", "error": str(e)}
        print_result(result)
        return 1


async def cmd_create_repo(args):
    """Create GitHub repository."""
    logger.info(f"Creating repository: {args.repo_name}")

    try:
        result = await aistudio_create_github_repo(
            app_url=args.app_url,
            repo_name=args.repo_name,
            description=args.description,
            use_existing_auth=True
        )
        print_result(result)
        return 0 if result.get("status") == "success" else 1

    except Exception as e:
        logger.error(f"Repository creation failed: {e}")
        result = {"status": "error", "error": str(e)}
        print_result(result)
        return 1


async def cmd_commit_deploy(args):
    """Commit and deploy to Cloud Run."""
    logger.info(f"Committing and deploying to {args.google_cloud_project}")

    try:
        result = await aistudio_commit_and_deploy(
            app_url=args.app_url,
            commit_message=args.commit_message,
            google_cloud_project=args.google_cloud_project,
            issue_number=args.issue_number
        )
        print_result(result)
        return 0 if result.get("status") == "success" else 1

    except Exception as e:
        logger.error(f"Commit and deploy failed: {e}")
        result = {"status": "error", "error": str(e)}
        print_result(result)
        return 1


async def cmd_clone(args):
    """Clone repository locally."""
    logger.info(f"Cloning {args.repo_url} to {args.local_path}")

    try:
        automation = AIStudioAutomation()
        result = await automation.clone_repository_locally(
            repo_url=args.repo_url,
            local_path=Path(args.local_path),
            branch=args.branch
        )
        print_result(result)
        return 0 if result.get("status") == "success" else 1

    except Exception as e:
        logger.error(f"Clone failed: {e}")
        result = {"status": "error", "error": str(e)}
        print_result(result)
        return 1


async def cmd_wait_implementation(args):
    """Wait for Gemini implementation."""
    logger.info(f"Waiting for implementation (max {args.timeout}s)")

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(storage_state=str(STORAGE_STATE_PATH))
            page = await context.new_page()
            await page.goto(args.app_url)

            automation = AIStudioAutomation()
            result = await automation.wait_for_gemini_implementation(
                page=page,
                timeout_seconds=args.timeout
            )

            await context.close()
            await browser.close()

            print_result(result)
            return 0 if result.get("status") == "success" else 1

    except Exception as e:
        logger.error(f"Wait failed: {e}")
        result = {"status": "error", "error": str(e)}
        print_result(result)
        return 1


def cmd_setup(args):
    """Run setup and verify installation."""
    print("🔍 Checking dependencies...")

    # Check Python packages
    deps_ok, missing = verify_dependencies()
    if not deps_ok:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print("\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        return 1

    print("✅ All Python dependencies installed")

    # Check/install Playwright browsers
    print("\n🌐 Checking Playwright browsers...")
    if ensure_playwright_setup():
        print("✅ Playwright browsers ready")
        print(f"\n✅ Setup complete! Authentication state will be saved to:")
        print(f"   {STORAGE_STATE_PATH}")
        return 0
    else:
        print("❌ Playwright setup failed")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="aistudio-mcp",
        description="AI Studio MCP Server - Command-line interface for Google AI Studio automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run setup (first time)
  aistudio-mcp setup

  # Login to AI Studio
  aistudio-mcp login

  # Create new project with prompt
  aistudio-mcp create-project \\
    --prompt-file "./prompt.txt" \\
    --project-name "goal-tracker"

  # Create GitHub repository
  aistudio-mcp create-repo \\
    --app-url "https://aistudio.google.com/apps/drive/abc123" \\
    --repo-name "my-project" \\
    --description "My AI Studio project"

  # Commit and deploy
  aistudio-mcp commit-deploy \\
    --app-url "https://aistudio.google.com/apps/drive/abc123" \\
    --commit-message "Add feature X" \\
    --google-cloud-project "my-gcp-project"

  # Clone repository
  aistudio-mcp clone \\
    --repo-url "https://github.com/user/repo.git" \\
    --local-path "./my-project"

  # Wait for Gemini implementation
  aistudio-mcp wait \\
    --app-url "https://aistudio.google.com/apps/drive/abc123" \\
    --timeout 300

For more documentation, see: /a/src/mcps/src/aistudio/docs/
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    parser_setup = subparsers.add_parser("setup", help="Run first-time setup")
    parser_setup.set_defaults(func=cmd_setup)

    # Login command
    parser_login = subparsers.add_parser("login", help="Authenticate to AI Studio")
    parser_login.set_defaults(func=cmd_login)

    # Create project command
    parser_project = subparsers.add_parser("create-project", help="Create new AI Studio project and send prompt")
    parser_project.add_argument("--prompt-file", required=True, help="Path to file containing prompt for Gemini")
    parser_project.add_argument("--project-name", help="Optional project name (auto-generated if not provided)")
    parser_project.set_defaults(func=cmd_create_project)

    # Create repo command
    parser_create = subparsers.add_parser("create-repo", help="Create GitHub repository")
    parser_create.add_argument("--app-url", required=True, help="AI Studio app URL")
    parser_create.add_argument("--repo-name", required=True, help="Repository name")
    parser_create.add_argument("--description", required=True, help="Repository description")
    parser_create.set_defaults(func=cmd_create_repo)

    # Commit and deploy command
    parser_commit = subparsers.add_parser("commit-deploy", help="Commit to GitHub and deploy to Cloud Run")
    parser_commit.add_argument("--app-url", required=True, help="AI Studio app URL")
    parser_commit.add_argument("--commit-message", required=True, help="Commit message")
    parser_commit.add_argument("--google-cloud-project", required=True, help="GCP project ID")
    parser_commit.add_argument("--issue-number", type=int, help="GitHub issue number (optional)")
    parser_commit.set_defaults(func=cmd_commit_deploy)

    # Clone command
    parser_clone = subparsers.add_parser("clone", help="Clone repository locally")
    parser_clone.add_argument("--repo-url", required=True, help="GitHub repository URL")
    parser_clone.add_argument("--local-path", required=True, help="Local path to clone to")
    parser_clone.add_argument("--branch", default="main", help="Branch to clone (default: main)")
    parser_clone.set_defaults(func=cmd_clone)

    # Wait command
    parser_wait = subparsers.add_parser("wait", help="Wait for Gemini implementation")
    parser_wait.add_argument("--app-url", required=True, help="AI Studio app URL")
    parser_wait.add_argument("--timeout", type=int, default=300, help="Timeout in seconds (default: 300)")
    parser_wait.set_defaults(func=cmd_wait_implementation)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Run setup check before any command except 'setup'
    if args.command != "setup":
        if not ensure_playwright_setup():
            print("\n❌ Playwright browsers not installed. Run: aistudio-mcp setup")
            return 1

    # Execute command
    if asyncio.iscoroutinefunction(args.func):
        return asyncio.run(args.func(args))
    else:
        return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
