# AIStudio MCP Implementation Status - 2025-12-11

## 🎯 Original Goal
Test and improve the AIStudio MCP by building a **Goal Tracker** prototype through the full workflow:
1. Login to AIStudio
2. Create project with prompt
3. Wait for Gemini implementation
4. Create GitHub repository
5. Deploy to Cloud Run
6. Clone repository locally

## ✅ What We Accomplished

### 1. Configuration & Authentication
- **Fixed hardcoded profile paths** → Now uses required `AISTUDIO_USER_DATA_DIR` env var
- **Separated browser profiles** to avoid conflicts:
  - AIStudio MCP: `/src/home/mia/.config/jgwillwright/profiles/aistudio_dev`
  - Playwright MCP: `/src/home/mia/.config/jgwillwright/profiles/miadefault`
- **Automatic login detection** in `create_project_and_send_prompt()` method

### 2. UI Flow Discovery (Using Playwright MCP)
Successfully observed and documented the complete AIStudio project creation flow:

**Flow:**
```
1. Navigate to https://aistudio.google.com/apps
2. Close popup: "Agree" (terms dialog)
3. Close popup: "Got it" (if present)
4. Fill textbox: get_by_role('textbox', name='Enter a prompt to generate an')
5. Click "Build": get_by_role('button', name='Build', exact=True)
6. URL changes: /apps → /apps/temp/X
7. Gemini implements (status: "Running for Xs", "Propelling")
8. URL changes: /apps/temp/X → /apps/drive/[ID] (permanent)
9. Status: "Ran for Xs" (past tense), message "Finished"
```

**Test case: "Universal Hello"**
- Successfully created via Playwright MCP
- Implementation time: ~84 seconds
- Final URL: `https://aistudio.google.com/apps/drive/1Q5NMoaAE9ZmlMu2OaQn6tRu_WRrH5Q_D`
- Status: ✅ Working app

### 3. Code Updates

**Updated files:**
- `/a/src/mcps/src/aistudio/src/mcp_server_aistudio/config.py`
  - Removed hardcoded default profile path
  - Made `AISTUDIO_USER_DATA_DIR` required

- `/a/src/mcps/src/aistudio/src/mcp_server_aistudio/automation.py`
  - Removed "Click New" step (not needed)
  - Updated to correct selectors from Playwright observation
  - Added automatic login handling in `create_project_and_send_prompt()`
  - Added polling for completion (checks "Finished" text + URL change)
  - Added error detection for "An internal error occurred"
  - Extended timeout to 10 minutes with progress logging

- `/a/src/mcps/src/aistudio/src/mcp_server_aistudio/server.py`
  - Fixed `async_playwright` import order bug

- `/a/src/mcps/src/aistudio/src/mcp_server_aistudio/cli.py`
  - Simplified `cmd_create_project()` to rely on automation method

## ❌ Current Blocker

### AIStudio Internal Error
When testing **Goal Tracker** creation (the actual target project), AIStudio returned:
```
Error: An internal error occurred.
```

**Symptoms:**
- Simple prompts work ("Hello World" → 84s → success)
- Complex prompts fail ("Goal Tracker" → internal error)
- URL stays at `/apps/temp/1` instead of changing to `/apps/drive/...`
- Error appears during Gemini implementation phase

**Not yet investigated:**
- Whether error is consistent or intermittent
- Whether simpler Goal Tracker prompt would work
- Whether retrying helps
- What specific AIStudio quota/limit was hit

## 🔧 Current Code State

### Working Flow (automation.py lines ~174-260)
```python
# 1. Navigate + close popups
await page.goto("https://aistudio.google.com/apps")
# Close "Agree", "Got it" if present

# 2. Fill prompt + click Build
textbox = page.get_by_role('textbox', name='Enter a prompt to generate an')
await textbox.fill(prompt)
build_button = page.get_by_role('button', name='Build', exact=True)
await build_button.click()

# 3. Poll for completion (10 min max)
while not_done:
    # Check for error first
    if "An internal error occurred" visible:
        return error

    # Check if done
    if url contains "/apps/drive/":
        break
    if "Finished" text visible:
        break

    await asyncio.sleep(5)
```

### Test Command
```bash
cd /a/src/mcps/src/aistudio && \
AISTUDIO_USER_DATA_DIR="/src/home/mia/.config/jgwillwright/profiles/aistudio_dev" \
python -m mcp_server_aistudio.cli create-project \
  --prompt-file /a/src/mcps/src/aistudio/samples/goal-tracker-aistudio-251211/prompt.txt \
  --project-name "goal-tracker-test"
```

## 📋 What's Left To Do

### Immediate Next Steps
1. **Debug AIStudio internal error:**
   - Try simpler Goal Tracker prompt
   - Check AIStudio quota/limits
   - Test with different model settings
   - Consider retrying on error

2. **Complete create-project flow:**
   - Get Goal Tracker (or simpler test app) to build successfully
   - Verify final URL extraction works
   - Test project naming

### Full Workflow (Not Yet Started)
3. **Create GitHub repository** (tool: `aistudio_create_repo`)
   - Navigate to project
   - Click "Save to GitHub" button
   - Fill in repo name, description
   - Create repository

4. **Deploy to Cloud Run** (tool: `aistudio_commit_and_deploy`)
   - Click "Deploy app" button
   - Fill in GCP project ID
   - Trigger deployment
   - Wait for deployment to complete

5. **Clone repository locally** (tool: `aistudio_clone_repository`)
   - Extract GitHub repo URL
   - Use git clone
   - Verify files

## 🎓 Key Learnings

### 1. Methodology Improvement
**Before:** Guessing selectors, writing code blind
**After:** Observe with Playwright MCP first, then encode in Python

This saved massive time and frustration.

### 2. Error Detection is Critical
Don't wait 10 minutes for timeouts. Check for:
- Error messages every polling cycle
- Status indicators (past tense "Ran" vs present "Running")
- URL changes as state transitions

### 3. Browser Profile Management
Persistent browser contexts with `user_data_dir` avoid re-login but:
- Need separate profiles for different tools
- Conflicts happen if same profile used twice
- Config should be explicit (no hardcoded defaults)

## 📁 Related Files

**Configuration:**
- `/a/src/.mcp.aistudio-dev.json` - MCP server config with env vars

**Test Data:**
- `/a/src/mcps/src/aistudio/samples/goal-tracker-aistudio-251211/prompt.txt` - Goal Tracker prompt (854 chars)

**Documentation:**
- `/a/src/mcps/src/aistudio/docs/llms-aistudio-04-browser-automation-reference.md` - Original timing patterns

**Logs:**
- `/tmp/claude/tasks/*.output` - Background task outputs

## 🚀 Quick Start for Next Session

```bash
# 1. Check if AIStudio error is still occurring
cd /a/src/mcps/src/aistudio
AISTUDIO_USER_DATA_DIR="/src/home/mia/.config/jgwillwright/profiles/aistudio_dev" \
python -m mcp_server_aistudio.cli create-project \
  --prompt-file samples/goal-tracker-aistudio-251211/prompt.txt

# 2. If error persists, try simpler prompt:
echo "Create a simple todo list app with React and TypeScript" > /tmp/simple-test.txt
AISTUDIO_USER_DATA_DIR="/src/home/mia/.config/jgwillwright/profiles/aistudio_dev" \
python -m mcp_server_aistudio.cli create-project --prompt-file /tmp/simple-test.txt

# 3. Once create-project works, continue with repo creation
```

## 💡 Notes for Future Claude Instances

- User prefers: observe → encode, not guess → fail → retry
- User is results-focused: show working code, minimize explanations
- Error detection should fail fast, not wait for timeouts
- Use Playwright MCP for UI exploration when uncertain about selectors
- Progress logging every 30s helps user track long-running operations

---

**Status:** 🟡 In Progress
**Blocker:** AIStudio internal error on Goal Tracker prompt
**Next:** Debug error or try simpler prompt
**Estimated Time to Complete:** 1-2 hours (assuming error resolves)
