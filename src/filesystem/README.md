# jgwill-mcp-server-filesystem

Fork of [@modelcontextprotocol/server-filesystem](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem) that **merges** command-line directories with client roots instead of replacing them.

## Installation

```bash
npm install -g jgwill-mcp-server-filesystem
```

Or use directly with npx:

```bash
npx jgwill-mcp-server-filesystem /path/to/dir1 /path/to/dir2
```

## Key Difference from Original

The original MCP filesystem server **replaces** command-line directories when a client provides roots via the MCP Roots protocol. This fork **merges** them instead, ensuring your configured directories are always available alongside client-provided roots.

This fixes a common issue where tools like Claude Code would override your carefully configured directory list with just the current working directory.

## Features

- Read/write files
- Create/list/delete directories
- Move files/directories
- Search files
- Get file metadata
- **Merged directory access** - command-line args + client roots (deduplicated)

## Directory Access Control

The server uses a flexible directory access control system. Directories can be specified via command-line arguments and/or dynamically via [Roots](https://modelcontextprotocol.io/docs/learn/client-concepts#roots).

### Method 1: Command-line Arguments
Specify allowed directories when starting the server:
```bash
jgwill-mcp-server-filesystem /path/to/dir1 /path/to/dir2
```

### Method 2: MCP Roots
MCP clients that support [Roots](https://modelcontextprotocol.io/docs/learn/client-concepts#roots) can dynamically add directories.

**Important difference from original**: Client roots are **merged** with command-line directories (deduplicated), not replaced.

### How It Works

1. **Server Startup** - Server starts with directories from command-line arguments
2. **Client Connection** - Client connects and sends capabilities
3. **Roots Protocol Handling** (if client supports roots)
   - Server requests roots from client
   - Server **merges** client roots with command-line directories
   - Duplicates are removed
4. **Access Control** - All operations restricted to merged allowed directories

## API

### Tools

- **read_text_file** - Read file contents as text (supports head/tail)
- **read_media_file** - Read image/audio files as base64
- **read_multiple_files** - Read multiple files simultaneously
- **write_file** - Create or overwrite files
- **edit_file** - Make selective edits with diff preview
- **create_directory** - Create directories (recursive)
- **list_directory** - List directory contents
- **list_directory_with_sizes** - List with file sizes and sorting
- **move_file** - Move or rename files/directories
- **search_files** - Recursive glob pattern search
- **directory_tree** - Get JSON tree structure
- **get_file_info** - Get file/directory metadata
- **list_allowed_directories** - List all accessible directories

## Usage with Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "jgwill-mcp-server-filesystem",
        "/Users/username/Desktop",
        "/path/to/other/allowed/dir"
      ]
    }
  }
}
```

## Usage with Claude Code

Add to your MCP config (e.g., `.gemini/settings.json`):

```json
{
  "mcpServers": {
    "filesystem_mcp": {
      "command": "npx",
      "args": [
        "-y",
        "jgwill-mcp-server-filesystem",
        "/src",
        "/workspace",
        "/home/user/projects"
      ]
    }
  }
}
```

Then launch Claude Code with:
```bash
claude --mcp-config .gemini/settings.json
```

## Usage with VS Code

Add to your VS Code MCP configuration:

```json
{
  "servers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "jgwill-mcp-server-filesystem",
        "${workspaceFolder}"
      ]
    }
  }
}
```

## Build from Source

```bash
git clone https://github.com/jgwill/mcps.git
cd mcps/src/filesystem
npm install
npm run build
```

## License

MIT License - see LICENSE file for details.

## Credits

Based on [@modelcontextprotocol/server-filesystem](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem) by Anthropic.
