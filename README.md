# Hillhorn

Smart memory and AI assistant for Cursor with DeepSeek MCP Gateway.

## Capabilities

### MCP Tools (Hillhorn)

| Tool | Description |
|------|-------------|
| `hillhorn_get_context` | Project context: SOUL.md, USER.md, MEMORY.md + memory search |
| `hillhorn_search` | Semantic search in memory (kind_filter, recency_boost) |
| `hillhorn_add_turn` | Save fact or dialog turn to memory |
| `hillhorn_index_file` | Index file content for search |
| `hillhorn_consult_agent` | Call planner, coder, reviewer, chat (DeepSeek) |
| `hillhorn_consult_with_memory` | Same with project memory as context |

### Features

- **NWF Memory** - Semantic storage with embeddings (add/search sync)
- **DeepSeek Gateway** - Single entry for agents (planner, reviewer, chat)
- **Retry** - Auto-retry on ConnectError (2 attempts)
- **API cost tracking** - Usage in `data/deepseek_usage.json`, `scripts/cost_report.ps1`
- **Diagnostics** - `scripts/diagnose.ps1` (Gateway, ports, activity)
- **Call history** - `data/hillhorn_calls.jsonl`, extension "Hillhorn: Show History"
- **VS Code extension** - Status bar, call count, history command

### Quick Start

```powershell
# Install
.\scripts\install_hillhorn_to_cursor.ps1

# Run (Gateway + NWF Adapter)
.\scripts\start_all_background.ps1

# Diagnose
.\scripts\diagnose.ps1

# Cost report
.\scripts\cost_report.ps1 day
```

### Requirements

- Python 3.10+
- DEEPSEEK_API_KEY in `.env`
- Cursor with MCP (Hillhorn configured)

### License

MIT - see [LICENSE](LICENSE)
