# HuskyCat AI Assistant Integration Roadmap

**Status**: Research Complete → Ready for Implementation
**Date**: 2026-01-15
**Based On**: [AI Assistant Integration Research](ai-assistant-integration-research.md)

---

## Executive Summary

HuskyCat currently supports **Claude Code via MCP**. Research shows the AI coding assistant ecosystem is converging on **open protocols** under the Linux Foundation's Agentic AI Foundation (AAIF).

**Critical Opportunity**: Implement **ACP (Agent Client Protocol)** to integrate with **JetBrains IDEs** (IntelliJ, PyCharm, WebStorm, etc.) - potentially reaching **millions of users**.

---

## Current Status

### ✅ What Works Today

1. **MCP Server** (Sprint 0 - Complete)
   - JSON-RPC 2.0 over stdio
   - Exposes validators as MCP tools
   - Works with: **Claude Code**, **OpenCode** (75+ LLM providers)
   - Container-backed execution
   - Implementation: `src/huskycat/mcp_server.py`

2. **OpenCode Compatibility** (Automatic)
   - HuskyCat MCP server works with OpenCode **immediately**
   - Access to: OpenAI, Anthropic, Google, Ollama (local), 70+ more
   - No code changes needed - just documentation

3. **5 Product Modes** (Sprint 0 - Complete)
   - Git Hooks, CI, CLI, Pipeline, MCP
   - Mode detection and adapters
   - Implementation: `src/huskycat/core/mode_detector.py`

---

## Critical Gap: JetBrains Ecosystem

### The Opportunity

**JetBrains AI Assistant** (IntelliJ IDEA, PyCharm, WebStorm, GoLand, PhpStorm, RubyMine, RustRover):
- Supports **ACP (Agent Client Protocol)** as of version 25.3 RC (Dec 2025)
- Millions of active users
- Native integration with AI Chat and agent mode

**Quote from JetBrains**:
> "ACP defines a standard communication interface, so any compatible agent can be added and used right away."

### What is ACP?

**Agent Client Protocol** (ACP):
- Connects **AI coding agents ↔ IDEs** (like LSP for language servers)
- REST-based (familiar HTTP patterns, not JSON-RPC)
- Co-developed by **IBM + Zed**, adopted by **JetBrains**
- Enables agents to: open files, suggest edits, run tests, report results

**Key Difference from MCP**:
| Protocol | Purpose | Transport | Connects |
|----------|---------|-----------|----------|
| **MCP** | AI ↔ Tools/Data | JSON-RPC stdio | Claude ↔ HuskyCat |
| **ACP** | Agent ↔ IDE | REST HTTP | JetBrains ↔ HuskyCat |

---

## Implementation Roadmap

### Phase 1: Quick Wins (Sprint 1-2) 🏃

**Effort**: Trivial | **Impact**: Medium | **Status**: 📋 Ready

#### 1.1 Create AGENTS.md Standard
```markdown
# .agents.md in HuskyCat repo
## Project: HuskyCat Validation Agent

### Validation Standards
- Always run `huskycat validate --staged` before commits
- Python: Black (formatting), Ruff (linting), MyPy (types) required
- YAML: yamllint with strict config
- Security: Bandit for Python, hadolint for Dockerfiles

### Auto-Fix Policy
- Black: Always auto-fix (100% safe)
- Ruff: Auto-fix with `--fix` flag (90% safe)
- Security issues: Suggest only, require manual review

### Usage Examples
bash
# Pre-commit validation
huskycat validate --staged

# Full project validation with auto-fix
huskycat validate --fix src/

# Security scan only
huskycat validate --tools=bandit,gitleaks .
```

**Adoption**: 60,000+ open-source projects use AGENTS.md (Cursor, Devin, GitHub Copilot, Gemini CLI, VS Code)

#### 1.2 Document OpenCode Compatibility
- Add to README: "Works with 75+ LLM providers via OpenCode"
- Create `docs/integrations/opencode.md` guide
- Test with OpenCode + various providers (OpenAI, Anthropic, Ollama)
- Blog post: "HuskyCat + OpenCode: Validation for Any LLM"

**Impact**: Access to users who want local models or alternative LLM providers

---

### Phase 2: ACP Server (Sprint 3-4) 🎯 **CRITICAL**

**Effort**: Medium (2-3 days) | **Impact**: Very High | **Status**: 🎯 High Priority

#### 2.1 Implementation Overview

**New File**: `src/huskycat/acp_server.py`

```python
from flask import Flask, jsonify, request
from pathlib import Path
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
        "capabilities": [
            "validate_python",
            "validate_javascript",
            "validate_yaml",
            "auto_fix",
            "security_scan"
        ],
        "status": "ready",
        "executionMode": "container-backed"
    })

@app.route('/validate', methods=['POST'])
def validate():
    """Validate files"""
    data = request.get_json()
    path = data.get('path', '.')
    fix = data.get('fix', False)
    tools = data.get('tools', None)  # Optional tool filter

    # Use existing validation engine
    engine.auto_fix = fix
    if Path(path).is_file():
        results = engine.validate_file(Path(path))
        validation_results = {str(path): results} if results else {}
    else:
        validation_results = engine.validate_directory(Path(path))

    summary = engine.get_summary(validation_results)

    return jsonify({
        "status": "success",
        "summary": summary,
        "results": {
            filepath: [r.to_dict() for r in file_results]
            for filepath, file_results in validation_results.items()
        },
        "duration_ms": sum(r.duration_ms for results in validation_results.values() for r in results)
    })

@app.route('/fix', methods=['POST'])
def fix():
    """Apply auto-fixes"""
    data = request.get_json()
    path = data.get('path', '.')
    confidence = data.get('confidence', 'likely')  # safe, likely, uncertain

    # Use auto-fix framework (Sprint 8)
    orchestrator = FixOrchestrator(ProductMode.ACP)
    report = orchestrator.fix_files(
        [Path(path)],
        dry_run=False,
        confidence_threshold=FixConfidence[confidence.upper()]
    )

    return jsonify({
        "status": "success",
        "fixed": [f.to_dict() for f in report.fixed],
        "suggestions": [s.to_dict() for s in report.suggestions],
        "files_modified": len(report.fixed)
    })

@app.route('/suggest', methods=['POST'])
def suggest():
    """Get fix suggestions without applying"""
    # Similar to /fix but with dry_run=True
    pass

@app.route('/capabilities', methods=['GET'])
def capabilities():
    """List available validator tools"""
    return jsonify({
        "validators": [
            {"name": v.name, "language": v.language, "can_fix": v.supports_autofix}
            for v in engine.validators
        ]
    })

@app.route('/status', methods=['GET'])
def status():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "container_available": engine._detect_container_available(),
        "validators_loaded": len(engine.validators)
    })

def main():
    app.run(host='127.0.0.1', port=8080, debug=False)

if __name__ == '__main__':
    main()
```

#### 2.2 CLI Entry Point

Add to `src/huskycat/__main__.py`:
```python
def main():
    # ... existing code ...

    if command == "acp-server":
        from .acp_server import main as acp_main
        acp_main()
        return
```

#### 2.3 ACP Configuration Template

**New File**: `acp.json.template`
```json
{
  "name": "HuskyCat",
  "version": "2.0.0",
  "description": "Code validation and auto-fix agent with container-backed toolchain",
  "executable": {
    "command": "/path/to/huskycat",
    "args": ["acp-server"]
  },
  "capabilities": [
    "validate_code",
    "auto_fix",
    "security_scan",
    "format_code"
  ],
  "supported_languages": [
    "python",
    "javascript",
    "typescript",
    "yaml",
    "dockerfile",
    "shell"
  ],
  "configuration": {
    "port": 8080,
    "host": "127.0.0.1",
    "log_level": "INFO"
  }
}
```

#### 2.4 JetBrains Integration Guide

**New File**: `docs/integrations/jetbrains.md`
```markdown
# JetBrains Integration (IntelliJ, PyCharm, WebStorm, etc.)

## Requirements
- JetBrains AI Assistant 25.3 RC or later
- HuskyCat 2.0+ installed

## Setup Steps

1. **Install HuskyCat**:
   bash
   curl -fsSL https://huskycat.io/install | bash


2. **Configure ACP**:
   - Open JetBrains IDE
   - Go to Settings → AI Assistant → Agent Client Protocol
   - Click "Add Agent"
   - Browse to `acp.json` (or create from template)
   - Verify agent appears as "HuskyCat" in list

3. **Verify Installation**:
   - Open AI Chat in IDE
   - Type: "HuskyCat, validate this file"
   - Agent should respond with validation results

## Usage Examples

### Pre-Commit Validation
```
HuskyCat, validate my staged files before I commit.
```

### Auto-Fix Issues
```
Run HuskyCat with auto-fix on src/main.py
```

### Security Scan
```
HuskyCat, scan this project for security issues.
```

### Custom Tool Selection
```
HuskyCat, run only Black and MyPy on this file.
```

## Troubleshooting

**Agent not appearing?**
- Verify HuskyCat is in PATH: `which huskycat`
- Check acp.json path is correct
- Restart IDE

**Validation failing?**
- Ensure container runtime available (podman/docker)
- Check logs: `huskycat status`
```

#### 2.5 Testing Plan

**Unit Tests**: `tests/test_acp_server.py`
```python
import pytest
from src.huskycat.acp_server import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_agent_discovery(client):
    rv = client.get('/agent')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['name'] == 'HuskyCat'
    assert 'capabilities' in data

def test_validate_endpoint(client):
    rv = client.post('/validate', json={
        'path': 'tests/fixtures/valid.py',
        'fix': False
    })
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['status'] == 'success'
```

**Integration Test**: Real JetBrains IDE
1. Install HuskyCat locally
2. Configure ACP in PyCharm
3. Test validation commands in AI Chat
4. Verify results appear correctly
5. Test auto-fix workflow

#### 2.6 Success Metrics

- [ ] ACP server starts on port 8080
- [ ] JetBrains AI Assistant discovers HuskyCat agent
- [ ] Validation commands work from AI Chat
- [ ] Auto-fix applies changes correctly
- [ ] Error messages are user-friendly
- [ ] Documentation is complete

---

### Phase 3: LSP Server (Sprint 5-6) 📋

**Effort**: Medium (3-4 days) | **Impact**: High | **Status**: 📋 Future

#### 3.1 Why LSP?

**Language Server Protocol** enables **real-time validation** in any editor:
- VS Code, Neovim, Emacs, Sublime Text, Zed, etc.
- Inline error highlighting (red squiggles)
- Hover for error details
- Quick fixes (apply auto-fixes inline)

**Complementary to ACP**: LSP = real-time diagnostics, ACP = agent commands

#### 3.2 Implementation Sketch

**New File**: `src/huskycat/lsp_server.py`
```python
from pygls.server import LanguageServer
from lsprotocol import types

server = LanguageServer('huskycat-lsp', 'v2.0')

@server.feature(types.TEXT_DOCUMENT_DID_SAVE)
def did_save(ls: LanguageServer, params: types.DidSaveTextDocumentParams):
    """Validate on file save"""
    uri = params.text_document.uri
    path = Path(uri.replace('file://', ''))

    # Run validation
    results = engine.validate_file(path)

    # Convert to LSP diagnostics
    diagnostics = []
    for result in results:
        for error in result.errors:
            diagnostics.append(types.Diagnostic(
                range=types.Range(
                    start=types.Position(line=error.line-1, character=0),
                    end=types.Position(line=error.line-1, character=100)
                ),
                severity=types.DiagnosticSeverity.Error,
                source=f'huskycat-{result.tool}',
                message=error.message,
                code=error.code
            ))

    ls.publish_diagnostics(uri, diagnostics)

@server.feature(types.TEXT_DOCUMENT_CODE_ACTION)
def code_action(ls: LanguageServer, params: types.CodeActionParams):
    """Provide quick fixes"""
    actions = []
    # If validator supports auto-fix, offer it as code action
    if result.supports_autofix:
        actions.append(types.CodeAction(
            title=f"Fix with {result.tool}",
            kind=types.CodeActionKind.QuickFix,
            command=types.Command(
                title="Apply fix",
                command="huskycat.fix",
                arguments=[params.text_document.uri, result.tool]
            )
        ))
    return actions
```

#### 3.3 VS Code Integration

**Client**: `.vscode/settings.json` or user settings
```json
{
  "huskycat.lsp.enable": true,
  "huskycat.lsp.validateOnSave": true,
  "huskycat.lsp.validateOnType": false
}
```

**Extension Stub** (future Phase 4):
```typescript
import * as vscode from 'vscode';
import { LanguageClient } from 'vscode-languageclient/node';

export function activate(context: vscode.ExtensionContext) {
  const serverOptions = {
    command: 'huskycat',
    args: ['lsp-server']
  };

  const client = new LanguageClient(
    'huskycat',
    'HuskyCat LSP',
    serverOptions,
    clientOptions
  );

  client.start();
}
```

---

### Phase 4: VS Code Extension (Sprint 7-8) 📦

**Effort**: High (5-7 days) | **Impact**: Medium | **Status**: ⏳ Future

**Why Lower Priority?**:
- LSP + MCP already provide VS Code integration
- Extension is "nice to have" (better UX, marketplace visibility)
- Large development effort for incremental benefit

**Features**:
- Wrap MCP/LSP servers
- Commands in command palette (`Ctrl+Shift+P`)
- Problems panel integration
- Status bar indicator
- Configuration UI

**Marketplace**:
- Publish to VS Code marketplace
- SEO: "code validation", "linting", "auto-fix"
- Demo GIFs and screenshots

---

### Phase 5: Enhanced MCP Tools (Sprint 9) 🔧

**Effort**: Low (1-2 days) | **Impact**: Low | **Status**: ⏳ Future

**New Tools for AI Interaction**:
```python
@mcp_tool("huskycat_explain_error")
def explain_error(file: str, line: int, error: str) -> str:
    """Explain validation error with examples"""
    # Provide context: why this is an error, how to fix it, examples
    return {
        "error": error,
        "explanation": "...",
        "example_fix": "...",
        "references": ["https://..."]
    }

@mcp_tool("huskycat_suggest_config")
def suggest_config(project_type: str) -> dict:
    """Suggest .huskycat.yaml configuration"""
    # Return recommended config for project type
    pass

@mcp_tool("huskycat_compare_tools")
def compare_tools(tool1: str, tool2: str) -> dict:
    """Compare two validator tools"""
    # Help AI decide which tool to recommend
    pass
```

---

## Priority Matrix

| Phase | Sprint | Protocol | Effort | Impact | Priority |
|-------|--------|----------|--------|--------|----------|
| 1 | 1-2 | AGENTS.md | Trivial | Medium | ✅ **Immediate** |
| 1 | 1-2 | OpenCode Docs | Trivial | Medium | ✅ **Immediate** |
| 2 | 3-4 | **ACP Server** | **Medium** | **Very High** | 🎯 **Critical** |
| 3 | 5-6 | LSP Server | Medium | High | 📋 High |
| 4 | 7-8 | VS Code Ext | High | Medium | 📦 Medium |
| 5 | 9 | Enhanced MCP | Low | Low | 🔧 Low |

---

## Success Criteria

### By End of Q1 2026:
- ✅ MCP server stable (Claude Code, OpenCode)
- 🎯 ACP server GA (JetBrains marketplace)
- 📋 LSP server beta (real-time validation)
- 📚 Documentation complete for all integrations
- 🎥 Demo videos for each platform

### By End of Q2 2026:
- 📊 10,000+ monthly active users across platforms
- 🌟 Featured in JetBrains plugin marketplace
- 📈 AGENTS.md adopted by 100+ downstream projects
- 🏆 "Protocol-agnostic validation agent" positioning established

---

## Technical Debt & Considerations

### 1. Protocol Router (Future)
**When**: After implementing MCP + ACP + LSP
**Why**: Avoid code duplication, centralize protocol handling
```python
# Future: src/huskycat/protocol_router.py
def detect_protocol(request) -> Protocol:
    if request.starts_with(b'{"jsonrpc"'):
        return Protocol.MCP
    elif request.starts_with(b'GET /agent'):
        return Protocol.ACP
    elif request.starts_with(b'Content-Length:'):
        return Protocol.LSP
```

### 2. Container Performance
**Issue**: Container startup adds latency (~500ms)
**Solution**: Keep container warm, or use binary for fast tools (Black, Ruff)
**Future**: Hybrid mode - binary for fast, container for comprehensive

### 3. Multi-Protocol Testing
**Challenge**: Test matrix explodes (MCP × ACP × LSP × 5 product modes)
**Solution**: Shared test fixtures, protocol adapters, E2E CI tests

---

## Questions for Consideration

1. **Port Assignment**: ACP server on 8080 or dynamic?
   - **Recommendation**: Dynamic with port discovery (avoid conflicts)

2. **Authentication**: Do we need API keys for ACP/LSP?
   - **Recommendation**: No auth for local-only (simplicity)
   - **Future**: Token-based for remote deployment

3. **Rate Limiting**: Should we limit validation requests?
   - **Recommendation**: No limits for MVP (trust local use)
   - **Future**: Configurable limits per client

4. **Telemetry**: Track which protocols are most used?
   - **Recommendation**: Yes, opt-in anonymous usage stats
   - **Data**: Protocol type, validator usage, success rates

---

## Next Steps

### Sprint 1-2 (This Week):
1. [ ] Create `.agents.md` in HuskyCat repo
2. [ ] Write `docs/integrations/opencode.md`
3. [ ] Add "Works with OpenCode" to README
4. [ ] Test OpenCode + HuskyCat MCP server
5. [ ] Blog post: "HuskyCat Protocol Roadmap"

### Sprint 3-4 (Next 2 Weeks):
1. [ ] Implement `acp_server.py` (REST endpoints)
2. [ ] Create `acp.json.template`
3. [ ] Write `docs/integrations/jetbrains.md`
4. [ ] Unit tests for ACP server
5. [ ] Integration test with PyCharm
6. [ ] Submit to JetBrains marketplace (if plugin wrapper needed)

### Sprint 5-6 (Q1 2026):
1. [ ] Implement `lsp_server.py` (diagnostics)
2. [ ] Test with VS Code, Neovim, Emacs
3. [ ] Document LSP setup for each editor
4. [ ] Performance benchmarks (real-time validation)

---

**Roadmap Status**: Ready for Implementation
**Owner**: HuskyCat Core Team
**Review Date**: End of Sprint 2 (reassess priorities)
