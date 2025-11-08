# v0 Deployer MCP Server

A comprehensive Model Context Protocol server for v0.dev deployment automation using Playwright. This server provides **tools**, **resources**, and **prompts** for seamless Vercel deployment workflows.

## Features

### 🛠️ Tools (5 deployment functions)
- **v0_login** - Authenticate to v0.dev
- **v0_git_pull** - Pull latest changes from Git into v0.dev
- **v0_publish** - Publish changes to Vercel
- **v0_view_app** - Open and test production application
- **v0_deploy** - Complete deployment workflow (pull + publish + view)

### 📚 Resources (3 documentation files)
All documentation accessible via MCP resources protocol:
- `v0://docs/deployment-workflow` - Complete deployment guide with UI patterns
- `v0://docs/agent-collaboration` - LLM collaboration framework for v0.dev
- `v0://docs/build-integrity` - Production build best practices

### 💬 Prompts (4 workflow templates)
- **deploy-to-vercel** - Full deployment workflow
- **update-from-git** - Pull latest Git changes
- **test-deployment** - Verify deployed application
- **troubleshoot-deployment** - Debug deployment issues

## Installation

### Using uv (recommended)

```bash
# No installation needed - use uvx directly
uvx mcp-server-v0deployer
```

### Using pip

```bash
pip install mcp-server-v0deployer
```

### From source

```bash
cd src/v0deployer
uv pip install -e .
```

## Prerequisites

1. **Playwright**: Install and setup browsers
```bash
playwright install chromium
```

2. **v0.dev Account**: Access to v0.dev projects

3. **Vercel Account**: Projects deployed on Vercel

## Configuration

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "v0deployer": {
      "command": "uvx",
      "args": ["mcp-server-v0deployer"]
    }
  }
}
```

### VS Code / Claude Code

Add to `.mcp.json`:

```json
{
  "mcpServers": {
    "v0deployer": {
      "command": "uvx",
      "args": ["mcp-server-v0deployer"]
    }
  }
}
```

## Quick Start

### 1. First Time: Authenticate

```
Use the v0_login tool to authenticate and save session
```

This opens a browser where you manually log in to v0.dev. Your session is saved for reuse.

### 2. Complete Deployment

Use the `deploy-to-vercel` prompt:

```
Prompt: deploy-to-vercel
Arguments:
  - v0_chat_url: "https://v0.app/chat/my-project-id"
  - production_url: "https://myapp.vercel.app"
  - view_after_deploy: "true"
```

This will:
1. Pull latest changes from Git into v0.dev
2. Publish changes to Vercel
3. Wait for deployment to complete
4. Open and test the production app

### 3. Access Documentation

All documentation is available as MCP resources:

```
Read resource: v0://docs/deployment-workflow
```

No need to look at external files - everything is accessible through the MCP!

## Critical UI Patterns

### The Dropdown Buttons

v0.dev uses **nested dropdown menus** that are the #1 cause of automation failures.

**GitHub Button** (for Git operations):
```
GitHub Button ▼
├── Pull Changes      ← Must click this to sync repo
├── View Repository
├── Commit History
└── Settings
```

**Publish Button** (for deployment):
```
Publish Button ▼
├── Publish Changes   ← Must click this to deploy
├── View Deployment
├── Open Published App
└── Deployment History
```

⚠️ **Critical**: You must click the button to open the dropdown, then click the nested option. Just clicking the button area won't trigger the action.

## Workflows

### Complete Deployment

**Time**: ~40-60 seconds total

1. **Pull Changes** (2-3 seconds)
   - Tool: `v0_git_pull`
   - Opens GitHub dropdown
   - Clicks "Pull Changes"
   - Waits for sync to complete

2. **Publish to Vercel** (15-20 seconds)
   - Tool: `v0_publish`
   - Opens Publish dropdown
   - Clicks "Publish Changes"
   - Waits for "Publishing..." to complete

3. **Wait for Deployment** (15-20 seconds)
   - Vercel receives push
   - Builds Next.js application
   - Deploys to CDN globally

4. **Test Application** (60 seconds)
   - Tool: `v0_view_app`
   - Opens production URL
   - Allows manual testing

**Reference**: Read `v0://docs/deployment-workflow`

### Update from Git Only

**Time**: ~5 seconds

Use when you've made changes directly in the Git repository and want to sync them to v0.dev:

```
Tool: v0_git_pull
Arguments:
  - v0_chat_url: "https://v0.app/chat/my-project"
```

**Reference**: Use `update-from-git` prompt

### Test Deployed App

**Time**: Varies

Use when you want to verify a deployment without making changes:

```
Tool: v0_view_app
Arguments:
  - production_url: "https://myapp.vercel.app"
  - wait_seconds: 120
```

**Reference**: Use `test-deployment` prompt

## Critical Timing Patterns

⏱️ **Dropdown Wait**: 1 second for dropdown menus to appear
⏱️ **Sync Wait**: Up to 120 seconds for Git pull to complete
⏱️ **Publish Wait**: Up to 180 seconds for publishing to complete
⏱️ **Deployment Wait**: 15-20 seconds for Vercel deployment
⏱️ **View App Wait**: 60 seconds default for manual testing

**Source**: All timing patterns documented in `v0://docs/deployment-workflow`

## Troubleshooting

### Common Issues

**"Not connected to browser" errors**
- Browser connection is unstable
- Re-run the tool
- Check Playwright installation

**"Pull Changes" button not found**
- GitHub button is a dropdown - click it first
- Wait 1 second for dropdown to appear
- Then click "Pull Changes"

**"Publish Changes" button not found**
- Publish button is a dropdown - click it first
- Wait 1 second for dropdown to appear
- Then click "Publish Changes"

**Old version showing on production**
- Wait 15-20 seconds after publish
- Clear browser cache
- Check Vercel dashboard for deployment status

**Build fails on Vercel**
- Read `v0://docs/build-integrity`
- Run `npm run build` locally
- Fix all TypeScript errors
- Verify environment variables

### Use Troubleshooting Prompt

```
Prompt: troubleshoot-deployment
Arguments:
  - issue_description: "Describe your issue here"
```

This guides you through debugging with references to documentation.

## Development

### Project Structure

```
src/v0deployer/
├── src/mcp_server_v0deployer/
│   ├── __init__.py       # Package exports
│   ├── __main__.py       # Entry point
│   ├── server.py         # MCP server (tools, resources, prompts)
│   ├── automation.py     # Playwright automation (V0Automation class)
│   └── config.py         # Configuration constants
├── docs/                 # Documentation (exposed as MCP resources)
│   ├── deployment-workflow.md
│   ├── agent-collaboration.md
│   └── build-integrity.md
├── pyproject.toml
├── README.md
└── LICENSE
```

### Running Tests

```bash
cd src/v0deployer
uv run pytest
```

### Running Locally

```bash
cd src/v0deployer
uv run mcp-server-v0deployer
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please ensure:
1. All documentation is updated
2. New tools have corresponding documentation resources
3. Timing patterns follow established guidelines
4. Tests pass

## Related Documentation

The MCP server exposes these as resources, but they're also available in `docs/`:

- **Deployment Workflow**: Complete guide with UI patterns and timing
- **Agent Collaboration**: Framework for LLM collaboration with v0.dev
- **Build Integrity**: Pre-flight checks for production builds

## Tips for LLM Agents

When using this MCP server in an automated workflow:

1. **Account for nested dropdowns**: Both GitHub and Publish buttons use dropdown menus
2. **Use the right timing**: Don't test immediately after publish - wait 15-20 seconds
3. **Pull before publish**: Always execute `v0_git_pull` before `v0_publish`
4. **Test on production URL**: Don't confuse v0.dev editor with live app
5. **Read the documentation resources**: All guidance is available via `v0://docs/*`

## Support

For issues, questions, or contributions:
- Create an issue in the repository
- Read `v0://docs/deployment-workflow` for troubleshooting
- Use the `troubleshoot-deployment` prompt for guided debugging

---

**Version**: 0.1.0
**Status**: Alpha
**MCP SDK**: 1.0.0+
**Python**: 3.10+
**Playwright**: 1.40+
