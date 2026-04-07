#!/bin/bash
. _env.sh
export SESSION_ID=19d0085d-e9d5-4985-ac1f-0aa4ec956327
export session_id__AIStudioTestsNEnhancements_2512021118
export session_id__AIStudioTestsNEnhancements_2512021118__MCP_CONFIG
export session_id__AIStudioTestsNEnhancements_2512021118__ADD_DIR
claude "you have aistudio MCP configured which links to what you can find in @src/aistudio/ ; in /src/test_mcps/aistudio/ Mia wrote you a report on her test within gemini-cli which might not be fully functional (gemini is more strict).  Though focus on what you can test on your side, pretty sure that what we desire to create here is not fully functional" --mcp-config $session_id__AIStudioTestsNEnhancements_2512021118__MCP_CONFIG --add-dir $session_id__AIStudioTestsNEnhancements_2512021118__ADD_DIR --session-id $session_id__AIStudioTestsNEnhancements_2512021118 --permission-mode plan
