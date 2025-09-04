# MCP Integration Solution

## Option 1: Native stdio Support (Recommended)
Add stdio transport to your existing HTTP server:

```typescript
// mcp-server/src/transports/stdio.ts
class StdioTransport {
  constructor(private mcpHandler: MCPHandler) {}
  
  start() {
    process.stdin.on('data', async (data) => {
      const request = JSON.parse(data.toString());
      const response = await this.mcpHandler.handle(request);
      process.stdout.write(JSON.stringify(response) + '\n');
    });
  }
}
```

## Option 2: Use Existing Bridge (Quick Fix)
Install production bridge:
```bash
npm install -g @civic/mcp-bridge-commander
mcp-bridge-commander --http http://localhost:3000/rpc --stdio
```

## Option 3: Hybrid Architecture
Run both protocols simultaneously:
- HTTP for web clients, complex features
- stdio for Claude Code basic tools only

## Why Bridges Fail for Complex Features
- No streaming support (container logs, real-time sync)
- No persistent state (queues, sessions)
- No bidirectional communication (webhooks, SSE)
- Performance degradation (50-100ms added latency)
