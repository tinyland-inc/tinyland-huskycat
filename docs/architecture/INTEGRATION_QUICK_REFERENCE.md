# AI Assistant Integration - Quick Reference

**Last Updated**: 2026-01-15

---

## What Works Today ✅

### Claude Code (via MCP)
```bash
# Already implemented
huskycat mcp-server
```
**Configuration**: Add to `~/.claude/config.json`

### OpenCode (via MCP)
```bash
# Same MCP server, 75+ LLM providers
huskycat mcp-server
```
**Works with**: OpenAI, Anthropic, Google, Ollama (local), 70+ more

---

## What's Next 🎯

### JetBrains (via ACP) - **HIGH PRIORITY**
```bash
# Sprint 3-4 - NEW
huskycat acp-server
```
**Access to**: Millions of JetBrains users (IntelliJ, PyCharm, WebStorm, etc.)
**Protocol**: REST (simpler than JSON-RPC)
**Configuration**: `acp.json` in project root

### Real-Time Validation (via LSP) - Future
```bash
# Sprint 5-6
huskycat lsp-server
```
**Access to**: Any editor (VS Code, Neovim, Emacs, Sublime, Zed)
**Features**: Inline errors, quick fixes, hover diagnostics

---

## Protocol Comparison

| Protocol | Use Case | Status | IDEs/Editors |
|----------|----------|--------|--------------|
| **MCP** | AI ↔ Tools | ✅ Live | Claude Code, OpenCode |
| **ACP** | Agent ↔ IDE | 🎯 Sprint 3-4 | JetBrains (IntelliJ, PyCharm, etc.) |
| **LSP** | Real-time validation | 📋 Sprint 5-6 | VS Code, Neovim, Emacs, Zed |

---

## Key Findings from Research

### 1. The Ecosystem is Standardizing
- **AAIF** (Linux Foundation): MCP, AGENTS.md, A2A
- **ACP** (IBM + Zed): JetBrains adoption (25.3 RC)
- **60,000+ projects** use AGENTS.md standard

### 2. ACP is the Critical Gap
> "ACP separates agents from editors. Agents implement one protocol and work everywhere."

**Why Critical**:
- JetBrains has **millions of users**
- REST API is simpler than JSON-RPC
- Works in: IntelliJ IDEA, PyCharm, WebStorm, GoLand, PhpStorm, RubyMine, RustRover

### 3. Multi-Protocol = Competitive Advantage
**HuskyCat positioning**: "Protocol-agnostic validation agent"
- MCP ✅ (Claude Code, OpenCode)
- ACP 🎯 (JetBrains, Zed)
- LSP 📋 (VS Code, Neovim, Emacs)

---

## Implementation Priorities

### Sprint 1-2: Quick Wins (This Week)
- [ ] Create `.agents.md` (industry standard)
- [ ] Document OpenCode compatibility
- [ ] Test with multiple LLM providers

### Sprint 3-4: ACP Server (**CRITICAL**)
- [ ] Implement REST API (`acp_server.py`)
- [ ] Create `acp.json` template
- [ ] Write JetBrains integration guide
- [ ] Test with PyCharm/IntelliJ

### Sprint 5-6: LSP Server
- [ ] Implement diagnostics (`lsp_server.py`)
- [ ] Test with VS Code, Neovim
- [ ] Real-time validation on save

---

## Code Snippets

### MCP Server (Current)
```python
# src/huskycat/mcp_server.py
# JSON-RPC 2.0 over stdio
server = MCPServer()
server.run()
```

### ACP Server (Sprint 3-4)
```python
# src/huskycat/acp_server.py
# REST API on port 8080
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/agent', methods=['GET'])
def get_agent_info():
    return jsonify({
        "name": "HuskyCat",
        "capabilities": ["validate", "fix", "security"]
    })

@app.route('/validate', methods=['POST'])
def validate():
    # Validation logic
    return jsonify({"status": "success", "results": [...]})

app.run(port=8080)
```

### LSP Server (Sprint 5-6)
```python
# src/huskycat/lsp_server.py
# Language Server Protocol
from pygls.server import LanguageServer

server = LanguageServer('huskycat-lsp', 'v2.0')

@server.feature(TEXT_DOCUMENT_DID_SAVE)
def did_save(ls, params):
    # Validate and publish diagnostics
    ls.publish_diagnostics(uri, diagnostics)
```

---

## Resources

### Full Documentation
- [Comprehensive Research](ai-assistant-integration-research.md) - 2000+ lines, all findings
- [Implementation Roadmap](INTEGRATION_ROADMAP.md) - Sprint plans, code examples

### External Links
- [ACP Specification](https://agentcommunicationprotocol.dev/)
- [JetBrains ACP Guide](https://www.jetbrains.com/help/ai-assistant/acp.html)
- [OpenCode](https://apidog.com/blog/opencode/)
- [AAIF Announcement](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation)

---

## Quick Decision Matrix

**Question**: Should we implement ACP?
**Answer**: **YES - High Priority** (Sprint 3-4)

**Reasons**:
1. ✅ Access to millions of JetBrains users
2. ✅ REST is simpler than JSON-RPC
3. ✅ 2-3 days implementation effort
4. ✅ Competitive positioning (protocol-agnostic)

**Question**: What about LSP?
**Answer**: **YES - Medium Priority** (Sprint 5-6)

**Reasons**:
1. ✅ Real-time validation in any editor
2. ✅ Inline error highlighting
3. ✅ Quick fixes (auto-fix inline)
4. ⚠️ 3-4 days implementation effort

**Question**: Do we need a VS Code extension?
**Answer**: **MAYBE - Lower Priority** (Sprint 7-8)

**Reasons**:
1. ✅ Better UX than raw LSP/MCP
2. ✅ Marketplace visibility
3. ⚠️ 5-7 days implementation effort
4. ⚠️ LSP + MCP already work in VS Code

---

## Success Metrics

**By Q1 2026**:
- ✅ MCP stable (Claude Code, OpenCode)
- 🎯 ACP GA (JetBrains)
- 📋 LSP beta (VS Code, Neovim)

**By Q2 2026**:
- 📊 10,000+ MAU across platforms
- 🌟 Featured in JetBrains marketplace
- 📈 100+ projects using AGENTS.md

---

## Contact

**Questions?** See [full research document](ai-assistant-integration-research.md) for:
- Protocol specifications
- Architecture diagrams
- Code examples
- Testing strategies
- 30+ sources cited
