"""
Setup utilities for AI Studio MCP Server

Handles automatic installation and configuration of dependencies.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


def check_playwright_browsers() -> bool:
    """Check if Playwright browsers are installed."""
    # Check for chromium browser directory
    playwright_dir = Path.home() / ".cache" / "ms-playwright"
    chromium_dirs = list(playwright_dir.glob("chromium-*"))

    if not chromium_dirs:
        return False

    # Check if chromium executable exists
    for chromium_dir in chromium_dirs:
        chrome_path = chromium_dir / "chrome-linux" / "chrome"
        if chrome_path.exists():
            return True

    return False


def install_playwright_browsers() -> Tuple[bool, str]:
    """
    Install Playwright browsers automatically.

    Returns:
        Tuple of (success: bool, message: str)
    """
    logger.info("Installing Playwright browsers...")

    try:
        # Try python -m playwright install chromium
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes max
        )

        if result.returncode == 0:
            logger.info("Playwright browsers installed successfully")
            return True, "Playwright browsers installed successfully"
        else:
            error_msg = result.stderr or result.stdout
            logger.error(f"Playwright install failed: {error_msg}")
            return False, f"Failed to install browsers: {error_msg}"

    except subprocess.TimeoutExpired:
        msg = "Playwright install timed out after 5 minutes"
        logger.error(msg)
        return False, msg
    except Exception as e:
        msg = f"Error installing Playwright browsers: {e}"
        logger.error(msg)
        return False, msg


def ensure_playwright_setup() -> bool:
    """
    Ensure Playwright browsers are installed, installing them if necessary.

    Returns:
        bool: True if browsers are available, False otherwise
    """
    if check_playwright_browsers():
        logger.debug("Playwright browsers already installed")
        return True

    logger.warning("Playwright browsers not found, installing...")
    print("📦 First-time setup: Installing Playwright browsers...")
    print("This may take a few minutes...")

    success, message = install_playwright_browsers()

    if success:
        print("✅ Playwright browsers installed successfully!")
        return True
    else:
        print(f"❌ Failed to install Playwright browsers: {message}")
        print("\nPlease install manually:")
        print(f"  {sys.executable} -m playwright install chromium")
        return False


def verify_dependencies() -> Tuple[bool, list[str]]:
    """
    Verify all required dependencies are available.

    Returns:
        Tuple of (all_ok: bool, missing: list[str])
    """
    missing = []

    # Check for playwright
    try:
        import playwright
    except ImportError:
        missing.append("playwright>=1.40.0")

    # Check for mcp
    try:
        import mcp
    except ImportError:
        missing.append("mcp>=1.0.0")

    return (len(missing) == 0, missing)
