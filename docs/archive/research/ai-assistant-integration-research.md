# AI Assistant Integration Research: Beyond MCP

**Research Date**: 2026-01-15
**Status**: Research Complete
**Scope**: ACP, OpenCode, JetBrains/IntelliJ, VS Code, Cross-Platform Integration

---

## Executive Summary

HuskyCat currently integrates with Claude Code via MCP (Model Context Protocol). This research explores how HuskyCat could expand to support:

1. **Agent Client Protocol (ACP)** - JetBrains, Zed, and broader IDE integration
2. **OpenCode** - Open-source Claude Code alternative (75+ LLM providers)
3. **JetBrains/IntelliJ AI Assistant** - Native IDE integration with ACP support
4. **VS Code Extensions** - LSP-based AI coding assistant patterns
5. **Standardization Landscape** - Agentic AI Foundation (AAIF) protocols

**Key Finding**: The AI coding assistant ecosystem is converging on **open protocols** (MCP, ACP, A2A) under the Linux Foundation's Agentic AI Foundation (AAIF). HuskyCat should implement **ACP support** to integrate with JetBrains IDEs and position itself as a **protocol-agnostic validation platform**.

---

## 1. Protocol Landscape

### 1.1 Model Context Protocol (MCP)

**Current Status**: HuskyCat implements MCP 2024-11-05 ✅

**What MCP Does**:
- Connects AI assistants to **external data sources and tools**
- Anthropic describes it as the "USB-C port for AI"
- Handles tool orchestration, RAG, embeddings, and context management
- JSON-RPC 2.0 protocol over stdio

**Adoption**:
- Industry standard for connecting AI to data/tools (2025)
- Donated to Linux Foundation's AAIF (Dec 2025)
- Supported by: Claude Code, Cursor, AWS, Google Cloud, Azure

**HuskyCat Implementation**:
- `src/huskycat/mcp_server.py` - stdio JSON-RPC server
- Exposes validators as MCP tools
- Container-backed execution for consistency

**Strength**: Tool-to-model connection (validation tools → AI)

---

### 1.2 Agent Client Protocol (ACP) - NEW OPPORTUNITY 🎯

**Status**: Emerging standard, JetBrains partnership (Oct 2025)

**What ACP Does**:
- Connects **AI coding agents to IDEs/editors**
- Like LSP (Language Server Protocol) but for AI agents
- REST-based, uses standard HTTP patterns (not JSON-RPC)
- Enables agent-to-editor communication (open files, suggest edits, run tests)

**Key Difference from MCP**:
| Aspect | MCP | ACP |
|--------|-----|-----|
| **Focus** | AI ↔ Data/Tools | AI Agent ↔ IDE |
| **Creator** | Anthropic | IBM + Zed |
| **Protocol** | JSON-RPC (specialized SDK) | REST (familiar HTTP) |
| **Purpose** | Context management | Agent orchestration |
| **Layer** | Tools/data wiring | Agent-to-agent, agent-to-editor |

**Adoption**:
- **JetBrains**: Native ACP support in AI Assistant (25.3 RC) - IntelliJ, PyCharm, WebStorm, etc.
- **Zed**: Co-developer of ACP specification
- **Google**: Built ACP-compatible Gemini CLI
- **Block (Square)**: Native ACP in goose agent
- **Anthropic**: Claude via Zed SDK adapter

**Critical for HuskyCat**:
> "ACP separates agents from editors. Agents implement one protocol and work everywhere. Editors adopt one protocol and support every agent."

**Integration Model**:
```
JetBrains IDEs (millions of users)
    ↓ ACP protocol (REST)
HuskyCat ACP Server
    ↓ Internal API
HuskyCat Validation Engine
```

**How JetBrains Uses ACP**:
1. User needs an **ACP-compatible agent executable** (HuskyCat binary)
2. User creates **acp.json configuration** (tells IDE where HuskyCat is)
3. Agent becomes available in AI Chat
4. IDE mediates agent's access to code/terminals/tools
5. IDE shows planned changes as **diffs** user must approve

**Benefits for HuskyCat**:
- ✅ Access to **millions of JetBrains users**
- ✅ Works across IntelliJ IDEA, PyCharm, WebStorm, GoLand, PhpStorm, RubyMine, RustRover
- ✅ No vendor lock-in (also works in Zed, potentially Neovim/Emacs)
- ✅ Familiar REST architecture (easier than JSON-RPC for many developers)

**Implementation Effort**: **Medium** (Sprint 9-10)
- Create REST API server (port 8080 or dynamic)
- Map ACP endpoints to validation commands
- Implement ACP discovery/capabilities
- Create acp.json configuration template

---

### 1.3 Agent-to-Agent (A2A) Protocol

**Status**: Merged with ACP under AAIF (Sept 2025)

**What A2A Does**:
- Agent-to-agent communication and coordination
- Cross-platform collaboration
- Task hand-off between agents

**Relevance to HuskyCat**:
- Future consideration for **multi-agent workflows**
- Example: HuskyCat validates → Refactoring agent fixes → HuskyCat re-validates
- Not immediate priority

---

### 1.4 AGENTS.md Standard

**Status**: OpenAI contribution to AAIF (Aug 2025)

**What it Does**:
- Simple markdown file giving AI agents **project-specific guidance**
- Adopted by 60,000+ open-source projects
- Used by: Cursor, Devin, GitHub Copilot, Gemini CLI, VS Code

**Example for HuskyCat**:
```markdown
# AGENTS.md

## Project: HuskyCat

### Validation Standards
- Always run validators before committing
- Use `huskycat validate --staged` pre-commit
- Python: Black, Ruff, MyPy required
- YAML: yamllint with strict config

### Auto-Fix Policy
- Black: Always auto-fix (100% safe)
- Ruff: Auto-fix with review (90% safe)
- Security issues: Suggest only (manual review)
```

**Implementation Effort**: **Trivial** (Sprint 1)
- Create `.agents.md` in HuskyCat repo
- Document validation workflows
- Provide examples for downstream projects

---

## 2. OpenCode: Open-Source Claude Code Alternative

**Status**: Released Dec 2025, rapid maturity

**Key Features**:
- Open-source, provider-agnostic AI coding agent
- Native Terminal UI (TUI) with LSP integration
- Supports **75+ LLM providers** (OpenAI, Anthropic, Google, Ollama, etc.)
- Multi-session capability
- Shareable session links (read-only snapshots)

**Comparison to Claude Code**:
| Feature | Claude Code | OpenCode |
|---------|-------------|----------|
| **Provider** | Anthropic only | 75+ providers |
| **UI** | Terminal | Terminal (themeable TUI) |
| **LSP** | Built-in | Automatic integration |
| **Session Sharing** | No | Yes (unique URLs) |
| **Local Models** | No | Yes (Ollama) |
| **Maturity** | Stable | Fast-moving (bugs possible) |

**MCP Support in OpenCode**:
- OpenCode supports MCP servers
- HuskyCat's existing MCP server works with OpenCode **immediately** ✅

**Integration Path**:
```json
{
  "mcpServers": {
    "huskycat": {
      "command": "/path/to/huskycat",
      "args": ["mcp-server"]
    }
  }
}
```

**Why This Matters**:
- Users locked into Claude Pro ($20/mo) can use OpenCode with their own API keys
- Local model support (Ollama) = fully offline validation workflows
- OpenCode uses sonnet-4 and "could replace Claude Code soon"

**Action**: **Document OpenCode compatibility** (already works via MCP)

---

## 3. JetBrains Ecosystem

### 3.1 JetBrains AI Assistant

**Status**: Production-ready, deeply integrated

**Architecture**:
- Powered by JetBrains AI Service
- Connects to multiple LLMs (OpenAI, Anthropic, Google)
- BYOK (Bring Your Own Key) supported
- Deep IDE integration (code completion, next edit suggestions, AI chat)

**Key Features**:
- **Code Completion**: Single lines and blocks
- **Next Edit Suggestions**: Update related code throughout file
- **AI Chat**: Agent mode for complex tasks (refactoring, test generation)
- **Context Management**: Add files, folders, images, commits to give context

**MCP Integration** (Discovered!):
> "The IntelliJ plugin's AI Assistant uses the same underlying tool architecture as the MCP Server. This means you get consistent, reliable access to your RevenueCat data directly inside your IDE."

**Implication**: JetBrains AI Assistant **already supports MCP-style tool integration**!

**Integration Path for HuskyCat**:
1. Existing MCP server might work via plugin architecture
2. Or: Build JetBrains plugin that wraps HuskyCat as AI Assistant tool
3. Or: Use ACP as the standard integration path (preferred)

---

### 3.2 JetBrains Junie (Agentic AI)

**Status**: Official JetBrains AI coding agent (2025)

**Key Capabilities**:
- **Autonomous agent**: Completes multi-step tasks independently
- **Planning stage**: Creates plan before generating code (dependencies, structure, APIs)
- **Project context**: Analyzes code to find relevant information
- **IDE inspections**: Uses built-in checks to reduce errors
- **Runs tests**: Verifies changes after making them

**Model Support**:
- OpenAI, Anthropic, OpenAI-compatible providers
- BYOK supported (no JetBrains AI subscription required for BYOK)
- Local models **not supported** for Junie

**IDE Compatibility**:
- IntelliJ IDEA, PyCharm, GoLand, PhpStorm, WebStorm, RubyMine, RustRover

**Difference from AI Assistant**:
- AI Assistant: Complements workflow (suggestions, questions)
- Junie: **Autonomous** (explores project, writes code, runs tests, shares results)

**ACP Support**:
> "JetBrains' AI agent Junie coming with ACP support across their entire IDE ecosystem."

**Integration Opportunity**:
- HuskyCat as ACP-compatible agent could appear alongside Junie
- Junie writes code → HuskyCat validates → Report back to user
- Complementary agents in same workflow

---

## 4. VS Code AI Extension Architecture

### 4.1 Extension Host Pattern

**Architecture**:
- Extensions run in isolated **Extension Host** (separate Node.js process)
- Communicates with main UI via well-defined API
- Allows non-blocking operations (parsing, model invocation, analysis)

**Key Components**:
1. **Extension API**: Access to editor state, file buffers, user interactions
2. **LSP Integration**: Query language servers for references, types, diagnostics
3. **Vector Embeddings**: Semantic similarity search for relevant code
4. **Session Management**: Per-project or per-workspace LSP sessions

**AI Extensions Use**:
- GitHub Copilot, Sourcegraph Cody, Cursor, Continue, TabNine, etc.
- All leverage LSP for code context
- Many use vector embeddings for retrieval across large codebases

---

### 4.2 LSP (Language Server Protocol) Integration

**How LSP Works**:
- Standardizes developer tooling (linters, formatters, type checkers) ↔ editors
- JSON-RPC 2.0 over stdin/stdout (like MCP!)
- One server, many clients (VS Code, Neovim, Emacs, Sublime)

**What LSP Provides AI Extensions**:
- Symbol references (find all usages)
- Type information (inferred by language server)
- Diagnostics (linter warnings, type errors)
- Code actions (quick fixes)

**Example**:
```javascript
// AI extension queries LSP for all references to `calculateTotal`
const references = await languageServer.findReferences('calculateTotal');
// Include related code in prompt for better AI suggestions
```

**Relevance to HuskyCat**:
- HuskyCat validators **produce diagnostics** (errors, warnings, suggestions)
- Could expose diagnostics via LSP for IDE integration
- Would enable **real-time inline validation** in editors

---

### 4.3 VS Code AI Extensibility APIs

**Language Model Tools API**:
- Introduced in VS Code 1.90+ (2024)
- Extensions can register **tools** that language models can invoke
- Deep integration with editor (access all VS Code APIs)

**Model Context Protocol (MCP) Tools**:
- VS Code supports MCP tools in agent mode
- MCP tools automatically invoked based on user prompts
- Can run locally or as remote services

**Implementation Pattern**:
```typescript
// VS Code extension using HuskyCat MCP server
import * as vscode from 'vscode';
import { MCPClient } from '@modelcontextprotocol/sdk';

export function activate(context: vscode.ExtensionContext) {
  const huskycatClient = new MCPClient({
    command: 'huskycat',
    args: ['mcp-server']
  });

  // Register validation command
  vscode.commands.registerCommand('huskycat.validate', async () => {
    const result = await huskycatClient.callTool('validate', {
      path: vscode.workspace.rootPath
    });
    // Show results in problems panel
  });
}
```

**Action**: Consider building **VS Code extension** that wraps HuskyCat MCP server

---

## 5. Cross-Platform Integration Strategies

### 5.1 Protocol-Agnostic Architecture

**Proposed HuskyCat Architecture**:
```
┌─────────────────────────────────────────────────────────────┐
│                    AI ASSISTANT CLIENTS                     │
│  Claude Code │ OpenCode │ JetBrains │ VS Code │ Zed │ Emacs│
└───────┬────────────┬────────────┬────────┬─────────┬────────┘
        │            │            │        │         │
        v            v            v        v         v
    ┌───────┐   ┌───────┐   ┌────────┐  ┌────┐  ┌────┐
    │  MCP  │   │  MCP  │   │  ACP   │  │LSP │  │ACP │
    │ stdio │   │ stdio │   │  REST  │  │RPC │  │REST│
    └───┬───┘   └───┬───┘   └────┬───┘  └─┬──┘  └─┬──┘
        │           │            │        │       │
        └───────────┴────────────┴────────┴───────┘
                            │
                ┌───────────v────────────┐
                │  PROTOCOL ROUTER       │
                │  (detect & dispatch)   │
                └───────────┬────────────┘
                            │
                ┌───────────v────────────┐
                │  VALIDATION ENGINE     │
                │  (unified logic)       │
                └────────────────────────┘
```

**Benefits**:
- Single validation engine
- Multiple frontend protocols
- Protocol detection at entry point
- Minimal duplication

---

### 5.2 Implementation Roadmap

#### Phase 1: Foundation (Sprint 1-2)
- ✅ MCP server (complete)
- [ ] Create protocol abstraction layer
- [ ] Document protocol requirements

#### Phase 2: ACP Support (Sprint 3-4)
- [ ] Implement REST API server
- [ ] Map ACP endpoints to commands
- [ ] Create acp.json template
- [ ] Test with JetBrains AI Assistant

#### Phase 3: LSP Integration (Sprint 5-6)
- [ ] Implement LSP server (diagnostics only)
- [ ] Real-time validation on file save
- [ ] Publish diagnostics to editors
- [ ] Support quick fixes (auto-fixes)

#### Phase 4: VS Code Extension (Sprint 7-8)
- [ ] Build VS Code extension wrapper
- [ ] Integrate with problems panel
- [ ] Add commands palette integration
- [ ] Publish to marketplace

#### Phase 5: Documentation (Sprint 9)
- [ ] Update docs with all integration methods
- [ ] Create AGENTS.md standard file
- [ ] Write integration guides for each platform
- [ ] Create demo videos

---

### 5.3 Protocol Comparison Matrix

| Protocol | Transport | Use Case | Complexity | Adoption | HuskyCat Status |
|----------|-----------|----------|------------|----------|-----------------|
| **MCP** | stdio JSON-RPC | AI ↔ Tools | Medium | High (AAIF) | ✅ Implemented |
| **ACP** | HTTP REST | Agent ↔ IDE | Low | Growing (JetBrains) | 🎯 Planned |
| **LSP** | stdio JSON-RPC | Tool ↔ Editor | Medium | Very High | 📋 Future |
| **A2A** | HTTP/gRPC | Agent ↔ Agent | High | Early | ⏳ Watch |

---

## 6. Standardization Landscape (2025-2026)

### 6.1 Agentic AI Foundation (AAIF)

**Formed**: December 9, 2025
**Governance**: Linux Foundation
**Founding Projects**:
1. **MCP** (Anthropic) - Tool/data connection standard
2. **goose** (Block/Square) - Open-source AI agent
3. **AGENTS.md** (OpenAI) - Project guidance standard

**Founding Members**:
- OpenAI, Anthropic, Google, Microsoft, AWS, Bloomberg, Cloudflare

**Mission**:
> "Provide neutral stewardship for open, interoperable infrastructure as agentic AI systems move from experimentation into real-world production."

**Key Trends**:
- **Convergence on open protocols** (vs proprietary APIs)
- **Linux Foundation governance** (neutral, community-driven)
- **Cross-vendor collaboration** (OpenAI + Anthropic + Google)

**Impact on HuskyCat**:
- MCP now a **neutral standard** (not just Anthropic's)
- AAIF ensures long-term protocol stability
- Multi-protocol support becomes competitive advantage

---

### 6.2 Industry Adoption Trends

**By End of 2025**:
- 85% of developers regularly use AI coding tools
- MCP = "industry standard for connecting AI to data/tools"
- 60,000+ projects adopted AGENTS.md

**Gartner Prediction**:
- 40% of enterprise apps will embed AI agents by end of 2026
- Up from <5% in 2025

**Protocol Convergence**:
> "The impact parallels the early web: just as HTTP enabled any browser to access any server, these protocols enable any agent to use any tool or collaborate with any other agent."

---

## 7. HuskyCat Integration Recommendations

### 7.1 Immediate Actions (Sprint 1-2)

1. **Create AGENTS.md** - Trivial effort, broad compatibility
   ```markdown
   # .agents.md
   ## Validation Standards
   - Run `huskycat validate --staged` before every commit
   - Python: Black + Ruff + MyPy required
   - Auto-fix: Use `--fix` for safe changes only
   ```

2. **Document OpenCode Compatibility** - Already works via MCP
   - Add to README and docs
   - Test with OpenCode + various LLM providers
   - Promote as "works with 75+ LLMs"

3. **Research ACP Implementation** - Start architecture planning
   - Review ACP specification
   - Design REST API endpoints
   - Create acp.json template

---

### 7.2 High-Priority Integrations (Sprint 3-6)

#### Priority 1: ACP Server (Sprint 3-4)

**Rationale**:
- Access to **millions of JetBrains users**
- REST is simpler than JSON-RPC for many developers
- ACP is gaining momentum (JetBrains partnership)

**Implementation**:
```python
# src/huskycat/acp_server.py

from flask import Flask, jsonify, request
from .unified_validation import ValidationEngine

app = Flask(__name__)
engine = ValidationEngine()

@app.route('/agent', methods=['GET'])
def get_agent_info():
    """ACP discovery endpoint"""
    return jsonify({
        "name": "HuskyCat",
        "description": "Code validation and auto-fix agent",
        "version": "2.0.0",
        "capabilities": ["validate", "fix", "report"],
        "status": "ready"
    })

@app.route('/validate', methods=['POST'])
def validate():
    """Validate files"""
    data = request.get_json()
    path = data.get('path', '.')
    fix = data.get('fix', False)

    results = engine.validate_directory(Path(path))
    return jsonify({
        "summary": engine.get_summary(results),
        "results": results
    })

if __name__ == '__main__':
    app.run(port=8080)
```

**Configuration** (acp.json):
```json
{
  "name": "HuskyCat",
  "version": "1.0.0",
  "executable": {
    "command": "huskycat",
    "args": ["acp-server"]
  },
  "capabilities": [
    "validate_code",
    "auto_fix",
    "security_scan"
  ]
}
```

---

#### Priority 2: LSP Diagnostics (Sprint 5-6)

**Rationale**:
- Real-time validation in **any editor** (VS Code, Neovim, Emacs, Sublime)
- Inline error highlighting
- Quick fixes (auto-fix actions)

**Implementation**:
```python
# src/huskycat/lsp_server.py

from pygls.server import LanguageServer
from lsprotocol import types

server = LanguageServer('huskycat-lsp', 'v1')

@server.feature(types.TEXT_DOCUMENT_DID_SAVE)
def did_save(ls: LanguageServer, params: types.DidSaveTextDocumentParams):
    """Validate on file save"""
    uri = params.text_document.uri
    path = Path(uri.replace('file://', ''))

    results = engine.validate_file(path)

    # Convert to LSP diagnostics
    diagnostics = []
    for result in results:
        for error in result.errors:
            diagnostics.append(types.Diagnostic(
                range=types.Range(...),
                severity=types.DiagnosticSeverity.Error,
                source='huskycat',
                message=error
            ))

    ls.publish_diagnostics(uri, diagnostics)

@server.feature(types.TEXT_DOCUMENT_CODE_ACTION)
def code_action(ls: LanguageServer, params: types.CodeActionParams):
    """Provide auto-fix actions"""
    # Return quick fixes as code actions
    actions = []
    if result.can_fix:
        actions.append(types.CodeAction(
            title=f"Fix with {result.tool}",
            kind=types.CodeActionKind.QuickFix,
            command=types.Command(
                title="Apply fix",
                command="huskycat.fix",
                arguments=[params.text_document.uri]
            )
        ))
    return actions
```

---

### 7.3 Medium-Priority Integrations (Sprint 7-9)

#### Priority 3: VS Code Extension

**Why**:
- Largest editor user base
- Native problems panel integration
- Marketplace distribution

**Implementation**:
- Wrap existing MCP/LSP servers
- Add commands to command palette
- Integrate with test explorer
- Provide hover diagnostics with fix suggestions

---

#### Priority 4: Enhanced MCP Tools

**Add new tools**:
```python
@mcp_tool("huskycat_suggest_fixes")
def suggest_fixes(path: str) -> List[dict]:
    """Get AI-friendly fix suggestions"""
    # Return structured suggestions for AI to reason about
    pass

@mcp_tool("huskycat_explain_error")
def explain_error(file: str, line: int, error: str) -> str:
    """Explain validation error in detail"""
    # Provide context and examples for AI
    pass

@mcp_tool("huskycat_configure")
def configure(tool: str, config: dict) -> bool:
    """Configure validator behavior"""
    # Allow AI to adjust validation rules
    pass
```

---

### 7.4 Long-Term Vision (2026+)

#### Multi-Agent Workflows (A2A)

**Scenario**: HuskyCat coordinates with other agents
```
User request
    ↓
Junie (JetBrains) → Writes code
    ↓
HuskyCat (ACP) → Validates code
    ↓ (if errors)
Junie (JetBrains) → Fixes issues
    ↓
HuskyCat (ACP) → Re-validates
    ↓ (if pass)
Git Agent → Commits changes
```

**Protocols Needed**:
- ACP (for IDE communication)
- A2A (for agent-to-agent coordination)
- MCP (for tool/data access)

---

## 8. Competitive Positioning

### 8.1 Unique Value Proposition

**HuskyCat's Differentiation**:
1. ✅ **Multi-protocol support** (MCP, ACP, LSP)
2. ✅ **Container-backed validation** (consistent toolchain)
3. ✅ **Binary + container execution** (flexible deployment)
4. ✅ **Auto-fix framework** (beyond just detection)
5. ✅ **5 product modes** (Git Hooks, CI, CLI, Pipeline, MCP)

**vs GitHub Copilot**:
- Copilot: Code generation only
- HuskyCat: Validation + auto-fix + security scanning

**vs Cursor/Continue**:
- Cursor/Continue: Full IDE replacements
- HuskyCat: Specialized validation agent, works with any IDE

**vs Pre-commit Hooks**:
- Pre-commit: Git-specific, manual configuration
- HuskyCat: Multi-platform, AI-assisted, auto-discovery

---

### 8.2 Market Positioning Statement

> "HuskyCat is a **protocol-agnostic code validation agent** that works with any AI coding assistant (Claude Code, OpenCode, JetBrains Junie, GitHub Copilot) and any IDE (VS Code, JetBrains, Zed, Neovim, Emacs). Unlike tools that only detect issues, HuskyCat **fixes them** with confidence-tiered auto-corrections. Deploy as binary, container, or MCP/ACP/LSP server."

---

## 9. Technical Specifications

### 9.1 ACP Server Specification

**Endpoints**:
```
GET  /agent              - Agent discovery
POST /validate           - Validate code
POST /fix                - Apply auto-fixes
POST /suggest            - Generate fix suggestions
GET  /capabilities       - List validator tools
POST /configure          - Update configuration
GET  /status             - Health check
```

**Request/Response Format**:
```json
// POST /validate
{
  "path": "src/main.py",
  "fix": false,
  "tools": ["black", "mypy", "ruff"]
}

// Response
{
  "status": "success",
  "results": [...],
  "summary": {...},
  "duration_ms": 142
}
```

---

### 9.2 LSP Server Specification

**Capabilities**:
- `textDocument/didSave` - Validate on save
- `textDocument/publishDiagnostics` - Send errors/warnings
- `textDocument/codeAction` - Provide quick fixes
- `workspace/executeCommand` - Apply fixes

**Diagnostics Format**:
```json
{
  "uri": "file:///src/main.py",
  "diagnostics": [
    {
      "range": {
        "start": {"line": 10, "character": 0},
        "end": {"line": 10, "character": 50}
      },
      "severity": 1,
      "source": "huskycat-mypy",
      "message": "Function is missing a return type annotation",
      "code": "no-untyped-def"
    }
  ]
}
```

---

## 10. Research Sources

### Protocol Specifications
- [Agent Communication Protocol (ACP) - Official Site](https://agentcommunicationprotocol.dev/introduction/welcome)
- [ACP GitHub Repository](https://github.com/i-am-bee/acp)
- [A Survey of Agent Interoperability Protocols (arXiv)](https://arxiv.org/html/2505.02279v1)
- [MCP, A2A, ACP Comparison](https://akka.io/blog/mcp-a2a-acp-what-does-it-all-mean)

### JetBrains Integration
- [JetBrains AI Assistant - ACP Documentation](https://www.jetbrains.com/help/ai-assistant/acp.html)
- [Bring Your Own AI Agent to JetBrains IDEs](https://blog.jetbrains.com/ai/2025/12/bring-your-own-ai-agent-to-jetbrains-ides/)
- [JetBrains × Zed: ACP Collaboration](https://blog.jetbrains.com/ai/2025/10/jetbrains-zed-open-interoperability-for-ai-coding-agents-in-your-ide/)
- [JetBrains Junie AI Agent](https://www.jetbrains.com/junie/)

### OpenCode
- [OpenCode Official Site](https://apidog.com/blog/opencode/)
- [OpenCode vs Claude Code Comparison](https://www.builder.io/blog/opencode-vs-claude-code)
- [Comparing Claude Code vs OpenCode (Testing Different Models)](https://www.andreagrandi.it/posts/comparing-claude-code-vs-opencode-testing-different-models/)

### VS Code Integration
- [How AI Extensions in VS Code Understand Code Context](https://www.gocodeo.com/post/how-ai-extensions-in-vscode-understand-code-context-under-the-hood)
- [AI Extensibility in VS Code](https://code.visualstudio.com/api/extension-guides/ai/ai-extensibility-overview)
- [Language Server Extension Guide](https://code.visualstudio.com/api/language-extensions/language-server-extension-guide)

### Standardization
- [Linux Foundation Announces Agentic AI Foundation (AAIF)](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation)
- [OpenAI Co-founds Agentic AI Foundation](https://openai.com/index/agentic-ai-foundation/)
- [My Predictions for MCP and AI-Assisted Coding in 2026](https://dev.to/blackgirlbytes/my-predictions-for-mcp-and-ai-assisted-coding-in-2026-16bm)

---

## 11. Conclusion

### Key Takeaways

1. **Protocol Convergence**: The AI coding assistant ecosystem is converging on **open standards** (MCP, ACP, AGENTS.md) under Linux Foundation governance.

2. **ACP is Critical**: JetBrains (millions of users) has adopted ACP. HuskyCat should implement ACP to unlock this market.

3. **OpenCode Works Now**: HuskyCat's MCP server already works with OpenCode, providing access to 75+ LLM providers.

4. **Multi-Protocol Strategy**: HuskyCat should support MCP (current), ACP (high priority), and LSP (future) to be truly platform-agnostic.

5. **Beyond Detection**: HuskyCat's auto-fix framework is a **competitive advantage** over detection-only tools.

### Recommended Sprint Priorities

| Sprint | Priority | Protocol | Effort | Impact |
|--------|----------|----------|--------|--------|
| 1-2 | HIGH | AGENTS.md + OpenCode docs | Trivial | Medium |
| 3-4 | **CRITICAL** | **ACP Server** | **Medium** | **Very High** |
| 5-6 | HIGH | LSP Server | Medium | High |
| 7-8 | MEDIUM | VS Code Extension | High | Medium |
| 9 | LOW | Enhanced MCP Tools | Low | Low |

### Success Metrics

**By Q2 2026**:
- ✅ MCP server stable (Claude Code, OpenCode)
- 🎯 ACP server GA (JetBrains IDEs)
- 📋 LSP server beta (VS Code, Neovim, etc.)
- 📊 10,000+ monthly active users across all platforms
- 🌟 Featured in JetBrains marketplace
- 📚 AGENTS.md adopted by 100+ projects

---

**Research Complete**: 2026-01-15
**Next Step**: Create ACP implementation plan (Sprint 3-4)
**Confidence**: High - All protocols have clear specifications and active communities
