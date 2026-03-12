# Hillhorn Chat

VS Code extension for AI chat powered by Hillhorn (DeepSeek + NWF-JEPA).

## Requirements

- DeepSeek Gateway running at `http://localhost:8001` (or configure `hillhorn.gatewayUrl`)

## Usage

1. Start the Gateway: `uvicorn deepseek_gateway:app --port 8001`
2. Click the Hillhorn icon in the Activity Bar
3. Type your message and press Send

## Configuration

- `hillhorn.gatewayUrl` - Gateway URL (default: http://localhost:8001)
- `hillhorn.workspaceId` - Workspace ID for NWF memory
- `hillhorn.agentType` - Default agent: chat, coder, planner, reviewer, architect, documenter
- `hillhorn.autoAgent` - Auto-select agent from memory

## Development

```bash
npm install
npm run compile
```

Then F5 in VS Code to launch Extension Development Host.
