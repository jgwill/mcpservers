# AI Studio MCP Server

A comprehensive Model Context Protocol server for Google AI Studio automation using Playwright. This server provides **tools**, **resources**, and **prompts** for end-to-end development workflows - from project creation through deployment.

## Features

### 🛠️ Tools (5 automation functions)
- **aistudio_login** - Authenticate to Google AI Studio
- **aistudio_create_repo** - Create GitHub repository for project
- **aistudio_commit_and_deploy** - Commit to GitHub and deploy to Cloud Run
- **aistudio_clone_repository** - Clone repository locally
- **aistudio_wait_for_implementation** - Wait for Gemini to complete implementation

### 📚 Resources (12 documentation files)
All documentation accessible via MCP resources protocol:
- `aistudio://docs/start-here` - Quick start and navigation guide
- `aistudio://docs/workflow-new-project` - Complete new project lifecycle
- `aistudio://docs/workflow-existing-project` - Enhancement workflow
- `aistudio://docs/ai-features-catalog` - AI capabilities reference
- `aistudio://docs/browser-automation-reference` - Playwright commands
- `aistudio://docs/llm-decision-guide` - Decision-making framework
- `aistudio://docs/best-practices-antipatterns` - Troubleshooting guide
- `aistudio://docs/mcp-server-setup` - Server configuration
- `aistudio://docs/mcp-quick-reference` - Quick lookup reference
- Plus 3 legacy documentation files

### 💬 Prompts (4 workflow templates)
- **create-new-project** - Full workflow for new projects
- **enhance-existing-project** - Add features/fix bugs
- **add-ai-features** - Integrate AI capabilities
- **troubleshoot-workflow** - Debug issues

## Installation

### Using uv (recommended)

```bash
# No installation needed - use uvx directly
uvx mcp-server-aistudio
```

### Using pip

```bash
pip install mcp-server-aistudio
```

### From source

```bash
cd src/aistudio
uv pip install -e .
```

## Prerequisites

1. **Playwright**: Install and setup browsers
```bash
playwright install chromium
```

2. **Google Account**: Access to Google AI Studio and Google Cloud Platform

3. **GitHub Account**: For repository creation (automated via AI Studio)

## Configuration

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "aistudio": {
      "command": "uvx",
      "args": ["mcp-server-aistudio"]
    }
  }
}
```

### VS Code / Claude Code

Add to `.mcp.json` in your project or global config:

```json
{
  "mcpServers": {
    "aistudio": {
      "command": "uvx",
      "args": ["mcp-server-aistudio"]
    }
  }
}
```

### Alternative: Using pip installation

```json
{
  "mcpServers": {
    "aistudio": {
      "command": "python",
      "args": ["-m", "mcp_server_aistudio"]
    }
  }
}
```

## Quick Start

### 1. First Time: Authenticate

```
Use the aistudio_login tool to authenticate and save session
```

This opens a browser where you manually log in to Google AI Studio. Your session is saved to `~/.playwright/aistudio_auth_state.json`.

### 2. Create a New Project

Use the `create-new-project` prompt:

```
Prompt: create-new-project
Arguments:
  - project_name: "my-ai-app"
  - project_description: "A chatbot for customer support"
  - google_cloud_project: "my-gcp-project-id"
```

This will:
1. Guide you through the complete workflow
2. Create AI Studio project with Gemini implementation
3. Set up GitHub repository
4. Deploy to Google Cloud Run
5. Clone locally for development

### 3. Enhance Existing Project

Use the `enhance-existing-project` prompt:

```
Prompt: enhance-existing-project
Arguments:
  - app_url: "https://aistudio.google.com/apps/drive/abc123"
  - enhancement_description: "Add voice input support"
  - google_cloud_project: "my-gcp-project-id"
```

### 4. Access Documentation

All documentation is available as MCP resources. LLM agents can read them directly:

```
Read resource: aistudio://docs/workflow-new-project
```

No need to look at external files - everything is accessible through the MCP!

## Workflows

### Creating a Brand New Project

**Time**: ~2-3 minutes for full workflow

1. **Authentication** (one-time)
   - Tool: `aistudio_login`

2. **Project Creation**
   - Manually create project in AI Studio
   - Send implementation prompt to Gemini
   - Tool: `aistudio_wait_for_implementation` (90+ seconds)

3. **Repository Setup**
   - Edit project name with UUID prefix
   - Tool: `aistudio_create_repo`

4. **Deployment**
   - Tool: `aistudio_commit_and_deploy`
   - Wait ~60 seconds for deployment

5. **Local Development**
   - Tool: `aistudio_clone_repository`
   - Review and iterate

**Reference**: Read `aistudio://docs/workflow-new-project`

### Enhancing Existing Project

**Time**: ~10-15 minutes per enhancement

1. Navigate to existing project URL
2. Describe enhancement to Gemini
3. Tool: `aistudio_wait_for_implementation`
4. Tool: `aistudio_commit_and_deploy`
5. Verify deployed application

**Reference**: Read `aistudio://docs/workflow-existing-project`

### Adding AI Features

**Time**: Varies (5-15 minutes)

1. **Explore Features**
   - Read `aistudio://docs/ai-features-catalog`
   - Available: voice, chatbots, TTS, images, video, maps, search

2. **Plan Implementation**
   - Read `aistudio://docs/llm-decision-guide`
   - Craft feature-specific prompt

3. **Implement & Deploy**
   - Send prompt to Gemini
   - Wait for implementation
   - Deploy and verify

**Reference**: Use `add-ai-features` prompt

## Critical Timing Patterns

⏱️ **Gemini Implementation**: Minimum 90 seconds, typical 2-5 minutes
⏱️ **Dialog Loading**: 8-10 seconds for GitHub/Deploy dialogs
⏱️ **Deployment**: ~60 seconds for Cloud Run deployment
⏱️ **Verification**: 3 seconds between retry checks

**Source**: All timing patterns documented in `aistudio://docs/browser-automation-reference`

## Troubleshooting

### Common Issues

**Authentication Fails**
- Delete `~/.playwright/aistudio_auth_state.json`
- Run `aistudio_login` again
- Ensure browser allows cookies

**Implementation Times Out**
- Increase `timeout_seconds` parameter
- Verify Gemini prompt is clear
- Check browser is still open

**Repository Creation Fails**
- Verify GitHub integration in AI Studio
- Check repository name uniqueness
- Ensure you have GitHub permissions

**Deployment Fails**
- Verify Google Cloud project ID
- Check Cloud Run permissions
- Review project quotas

### Use Troubleshooting Prompt

```
Prompt: troubleshoot-workflow
Arguments:
  - issue_description: "Describe your issue here"
```

This will guide you through debugging with references to:
- `aistudio://docs/best-practices-antipatterns`
- `aistudio://docs/browser-automation-reference`

## Development

### Project Structure

```
src/aistudio/
├── src/mcp_server_aistudio/
│   ├── __init__.py          # Package exports
│   ├── __main__.py          # Entry point
│   ├── server.py            # MCP server (tools, resources, prompts)
│   ├── automation.py        # Playwright automation (AIStudioAutomation class)
│   └── config.py            # Configuration constants
├── docs/                    # Documentation (exposed as MCP resources)
│   ├── 00-start-here.md
│   ├── 01-workflow-new-project.md
│   ├── 02-workflow-existing-project.md
│   ├── 03-ai-features-catalog.md
│   ├── 04-browser-automation-reference.md
│   ├── 05-llm-decision-guide.md
│   ├── 06-best-practices-antipatterns.md
│   ├── 07-mcp-server-setup.md
│   └── 08-mcp-quick-reference.md
├── pyproject.toml
├── README.md
└── LICENSE
```

### Running Tests

```bash
cd src/aistudio
uv run pytest
```

### Running Locally

```bash
cd src/aistudio
uv run mcp-server-aistudio
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

- **Start Here**: Complete navigation guide
- **Workflows**: New project and enhancement workflows
- **AI Features**: Catalog of AI capabilities
- **Browser Automation**: Playwright command reference
- **Best Practices**: Anti-patterns and solutions
- **MCP Setup**: Server configuration guide

## Support

For issues, questions, or contributions:
- Create an issue in the repository
- Read `aistudio://docs/best-practices-antipatterns` for troubleshooting
- Use the `troubleshoot-workflow` prompt for guided debugging

---

**Version**: 0.1.0
**Status**: Alpha
**MCP SDK**: 1.0.0+
**Python**: 3.10+
**Playwright**: 1.40+
