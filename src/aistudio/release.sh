#!/bin/bash

# mcp-server-aistudio Release Script
# Prepares distribution and publishes to PyPI

set -e  # Exit on any error

echo "🚀 mcp-server-aistudio Release Script Starting..."

# Clean previous builds
echo "🧹 Cleaning previous builds..."
hatch clean

# Bump version
echo "📈 Bumping version..."
# Version bumping should be done manually before running this script: hatch version <part>

# Build distribution
echo "🔨 Building distribution..."
hatch build

# Upload to PyPI
echo "📦 Publishing to PyPI..."
hatch publish

# Get current version and create git tag
echo "🏷️ Creating git tag..."
VERSION=$(hatch version)
git add pyproject.toml
git commit -m "v${VERSION}" || echo "No changes to commit"
git tag "aistudio-v${VERSION}"

echo "✅ Release complete!"
echo "📋 Version: v${VERSION}"
echo "📋 Next steps:"
echo "   - Push changes: git push origin main"
echo "   - Push tag: git push origin v${VERSION}"
echo "   - Verify package on PyPI: https://pypi.org/project/mcp-server-aistudio/"
echo "   - Test installation: pip install mcp-server-aistudio"
