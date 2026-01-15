# HuskyCat Documentation Audit & Cleanup Plan

**Date**: 2025-12-08
**Scope**: All 65 markdown files in docs/
**Goal**: Ensure every sentence is backed by actual code, Mermaid charts match reality

---

## Current State: 65 Markdown Files

### ✅ KEEP - Core Documentation (18 files)

**User-Facing:**
- docs/installation.md ✅ (VERIFIED - updated in beta sprint)
- docs/binary-downloads.md ✅ (VERIFIED - updated in beta sprint)
- docs/BETA_TESTING.md ✅ (NEW - beta sprint)
- docs/troubleshooting.md ⚠️ (needs verification)
- docs/configuration.md ⚠️ (needs verification)
- docs/cli-reference.md ⚠️ (needs verification)

**Architecture:**
- docs/architecture/execution-models.md ⚠️ (needs code reference verification)
- docs/architecture/product-modes.md ⚠️ (needs code reference verification)
- docs/dogfooding.md ✅ (VERIFIED in Sprint 11)
- docs/nonblocking-hooks.md ⚠️ (needs verification)

**Developer:**
- docs/index.md ⚠️ (MkDocs home, needs verification)
- docs/SPRINT_PLAN.md ⚠️ (current plan, verify vs reality)
- docs/future-roadmap.md ⚠️ (needs verification)

**API:**
- docs/api/mcp-tools.md ⚠️ (needs code verification)
- docs/mcp-tool-api.md ⚠️ (DUPLICATE? check vs api/mcp-tools.md)

**User Guide:**
- docs/user-guide/getting-started.md ⚠️ (needs verification)
- docs/user-guide/binary-gitops-installation.md ⚠️ (needs verification)

**Recent Additions:**
- docs/AGENT_REVIEW_FINDINGS.md ✅ (NEW - beta sprint)
- docs/BETA_TESTING_READINESS.md ✅ (NEW - beta sprint)

---

## 🗑️ ARCHIVE - Sprint Completion Summaries (20 files)

**Sprint Summaries (Root):**
- [ ] docs/SPRINT10_CLEANUP_SUMMARY.md → archive/sprints/
- [ ] docs/SPRINT10_PLAN_VS_REALITY.md → archive/sprints/
- [ ] docs/SPRINT10_TEST_COVERAGE_COMPLETE.md → archive/sprints/
- [ ] docs/SPRINT10_TEST_COVERAGE_PLAN.md → archive/sprints/
- [ ] docs/SPRINT11_DOGFOODING_BINARY_BOOTSTRAP.md → archive/sprints/ (keep reference in current docs)
- [ ] docs/PHASE1_INTEGRATION_COMPLETE.md → archive/sprints/
- [ ] docs/CURRENT_STATUS.md → archive/sprints/ (outdated)

**Proposals - Completed Sprints:**
- [ ] docs/proposals/phase-1-implementation-complete.md → archive/sprints/
- [ ] docs/proposals/phase-2-implementation-complete.md → archive/sprints/
- [ ] docs/proposals/phase-3-implementation-complete.md → archive/sprints/
- [ ] docs/proposals/phase-4-sprint-8-complete.md → archive/sprints/
- [ ] docs/proposals/sprint-9a-phase-1-implementation-summary.md → archive/sprints/
- [ ] docs/proposals/sprint-9a-phase-2-implementation-summary.md → archive/sprints/
- [ ] docs/proposals/sprint-9a-session-summary.md → archive/sprints/
- [ ] docs/proposals/sprint-9b-implementation-summary.md → archive/sprints/
- [ ] docs/proposals/sprint-10-architectural-refactor.md → archive/sprints/

**Chapel Formatter (6 files - completed feature):**
- [ ] docs/proposals/chapel-formatter-design.md → archive/chapel/
- [ ] docs/proposals/chapel-formatter-final-summary.md → archive/chapel/
- [ ] docs/proposals/chapel-formatter-implementation-complete.md → archive/chapel/
- [ ] docs/proposals/chapel-formatter-sprint-plan.md → archive/chapel/
- [ ] docs/proposals/chapel-future-enhancements.md → archive/chapel/
- [ ] docs/proposals/chapel-language-research.md → archive/chapel/

**LLM Docs (2 files - completed):**
- [ ] docs/proposals/llm-docs-implementation-summary.md → archive/proposals-completed/
- [ ] docs/proposals/llm-friendly-docs-ci.md → archive/proposals-completed/

---

## 🔀 MERGE - Redundant Documentation (8 files)

### Fat Binary Docs (3 files → 1)
**Merge into**: `docs/architecture/fat-binaries.md` (NEW)

Source files:
- docs/FAT_BINARY_ARCHITECTURE.md
- docs/fat-binary-builds.md
- docs/EMBEDDED_TOOLS_MIGRATION.md

**Action**: Create comprehensive fat-binaries.md covering:
- Architecture overview
- Build process (.gitlab/ci/build.yml references)
- Tool embedding (shellcheck, hadolint, taplo)
- Tool extraction (src/huskycat/core/tool_extractor.py)
- Platform support

### TUI Docs (3 files → 1)
**Merge into**: `docs/architecture/tui.md` (NEW)

Source files:
- docs/TUI_INTEGRATION.md
- docs/tui_framework.md
- docs/tui_implementation_summary.md

**Action**: Create comprehensive tui.md covering:
- TUI framework (src/huskycat/core/tui.py references)
- Rich integration
- Progress tracking
- Non-TTY graceful degradation

### CI Pipeline Docs (2 files → 1)
**Merge into**: `docs/ci-cd/gitlab.md` (NEW, create ci-cd/ subdir)

Source files:
- docs/ci-pipeline-architecture.md
- docs/ci-pipeline-fat-binary-status.md

**Action**: Create docs/ci-cd/gitlab.md covering:
- Pipeline architecture
- Binary build jobs
- Multi-platform support
- Artifact management

---

## ⚠️ VERIFY - Needs Code Reference Checks (12 files)

### High Priority - User Facing

**docs/troubleshooting.md**:
- [ ] Verify all error messages exist in actual code
- [ ] Confirm solutions work with current codebase
- [ ] Check file paths are correct

**docs/configuration.md**:
- [ ] Verify .huskycat.yaml schema matches code
- [ ] Check all config options are implemented
- [ ] Validate example configs work

**docs/cli-reference.md**:
- [ ] Verify all commands exist in src/huskycat/commands/
- [ ] Check all flags are implemented
- [ ] Validate example outputs are current

### Medium Priority - Architecture

**docs/architecture/execution-models.md**:
- [ ] Verify line numbers: `unified_validation.py:85-170` (file is 2146 lines!)
- [ ] Check Mermaid diagram matches actual execution flow
- [ ] Validate code examples compile and run

**docs/architecture/product-modes.md**:
- [ ] Verify 5 modes vs actual 6 adapters (git_hooks_nonblocking.py exists!)
- [ ] Check adapter code references
- [ ] Validate mode detection logic matches code

**docs/architecture/simplified-architecture.md**:
- [ ] Verify Mermaid diagram represents current architecture
- [ ] Check component relationships are accurate
- [ ] Update if outdated

### Low Priority - Technical

**docs/parallel_executor.md**:
- [ ] Verify references to src/huskycat/core/parallel_executor.py
- [ ] Check example code works

**docs/process_manager_integration.md**:
- [ ] Verify ProcessManager implementation details
- [ ] Check code references

**docs/performance.md**:
- [ ] Verify benchmark numbers are current
- [ ] Check performance claims against actual timings

**docs/migration/to-nonblocking.md**:
- [ ] Verify migration steps work
- [ ] Check code examples are current

**docs/features/mcp-server.md**:
- [ ] Verify MCP server implementation
- [ ] Check protocol details vs src/huskycat/mcp_server.py

**docs/api/mcp-tools.md vs docs/mcp-tool-api.md**:
- [ ] DUPLICATE CHECK - merge if same content

---

## 🚧 ACTIVE PROPOSALS (Keep in proposals/) (7 files)

**Keep - Active Planning:**
- docs/proposals/auto-format-comprehensive-review.md
- docs/proposals/auto-format-implementation-plan.md
- docs/proposals/documentation-overhaul-2025.md
- docs/proposals/e2e-ci-testing-strategy.md
- docs/proposals/feature-parity-analysis.md
- docs/proposals/git-tracked-hooks.md
- docs/proposals/gitops-binary-bootstrap-plan.md

**Note**: These are forward-looking proposals, not historical summaries

---

## 🔍 SPECIAL CASES

### docs/EMBEDDED_TOOL_EXECUTION.md
**Status**: Unclear - check if redundant with FAT_BINARY_ARCHITECTURE.md
**Action**: Review and either merge or archive

### docs/QUICK_START_NONBLOCKING.md
**Status**: May be redundant with docs/nonblocking-hooks.md
**Action**: Review and merge if duplicate

### docs/gitlab-auto-devops-complete.md
**Status**: Completion summary - archive?
**Action**: Review and decide archive vs keep

### docs/github-actions.md
**Status**: Future feature (not implemented)
**Action**: Keep in proposals/ or mark as "planned"

### docs/macos-code-signing.md
**Status**: Important for macOS distribution
**Action**: Keep but verify against actual signing process

---

## 📊 MERMAID DIAGRAM VERIFICATION

### Priority 1: Core Architecture Diagrams

**docs/architecture/execution-models.md** - Execution flow diagram
```
Current diagram shows:
  Binary → Container → UV Development

Verify against:
  - src/huskycat/unified_validation.py execution routing
  - src/huskycat/core/tool_extractor.py bundled vs local detection
  - huskycat_main.py frozen mode detection
```

**docs/architecture/product-modes.md** - Mode adapter diagram
```
Current diagram shows: 5 modes
Actual code has: 6 adapters

Verify:
  - git_hooks.py
  - git_hooks_nonblocking.py ← MISSING FROM DIAGRAM
  - ci.py
  - cli.py
  - pipeline.py
  - mcp.py
```

**docs/architecture/simplified-architecture.md**
```
Verify component relationships match:
  - Factory pattern (src/huskycat/core/factory.py)
  - Adapter pattern (src/huskycat/core/adapters/)
  - Validator classes (src/huskycat/unified_validation.py)
```

**README.md** - Execution model diagram
```
Verify against actual implementation
Check entry points match code
```

---

## 📁 PROPOSED NEW STRUCTURE

```
docs/
├── README.md                          # Docs navigation
├── installation.md                    # ✅ VERIFIED
├── BETA_TESTING.md                   # ✅ NEW
├── troubleshooting.md                 # ⚠️ needs verification
├── configuration.md                   # ⚠️ needs verification
├── cli-reference.md                   # ⚠️ needs verification
│
├── architecture/                      # Technical architecture
│   ├── execution-models.md           # ⚠️ verify code refs
│   ├── product-modes.md              # ⚠️ verify 6 adapters
│   ├── fat-binaries.md               # 🆕 MERGE 3 files
│   ├── tui.md                        # 🆕 MERGE 3 files
│   └── parallel-execution.md         # ⚠️ verify
│
├── features/                          # Feature-specific docs
│   ├── nonblocking-hooks.md          # ⚠️ verify
│   ├── mcp-server.md                 # ⚠️ verify vs code
│   └── auto-format.md                # Future
│
├── user-guide/                        # User documentation
│   ├── getting-started.md            # ⚠️ verify
│   ├── binary-gitops-installation.md # ⚠️ verify
│   └── migration-to-nonblocking.md   # ⚠️ verify
│
├── ci-cd/                             # 🆕 NEW directory
│   ├── gitlab.md                     # 🆕 MERGE 2 files
│   └── github.md                     # Planned
│
├── api/                               # API reference
│   └── mcp-tools.md                  # ⚠️ verify, check duplicate
│
├── proposals/                         # Active proposals only
│   ├── auto-format-*.md              # ✅ Active
│   ├── documentation-overhaul-2025.md # ✅ Active
│   ├── e2e-ci-testing-strategy.md    # ✅ Active
│   └── ... (7 active proposals)
│
└── archive/                           # 🆕 Historical docs
    ├── sprints/                       # Sprint summaries
    │   ├── sprint-9a-*.md            # 3 files
    │   ├── sprint-9b-*.md            # 1 file
    │   ├── sprint-10-*.md            # 4 files
    │   ├── phase-*.md                # 4 files
    │   └── SPRINT10_*.md             # 4 files
    ├── chapel/                        # Chapel formatter
    │   └── *.md                      # 6 files
    └── proposals-completed/           # Finished proposals
        └── llm-*.md                  # 2 files
```

**Total Files**:
- Current: 65 files
- After cleanup: ~35 active files
- Archived: ~30 files

---

## 🎯 ACTION PLAN

### Phase 1: Archive Obvious Candidates (15 minutes)
1. Move sprint summaries to archive/sprints/ (16 files)
2. Move chapel docs to archive/chapel/ (6 files)
3. Move completed proposals to archive/proposals-completed/ (2 files)

### Phase 2: Merge Redundant Docs (45 minutes)
1. Create docs/architecture/fat-binaries.md (merge 3)
2. Create docs/architecture/tui.md (merge 3)
3. Create docs/ci-cd/gitlab.md (merge 2)
4. Delete source files after verification

### Phase 3: Verify Code References (90 minutes)
1. Check all file:line references in architecture docs
2. Verify Mermaid diagrams match code
3. Update outdated references
4. Add missing adapter (git_hooks_nonblocking.py) to diagrams

### Phase 4: Update Mermaid Diagrams (60 minutes)
1. Fix product-modes.md (5 → 6 adapters)
2. Verify execution-models.md against code
3. Update simplified-architecture.md if needed
4. Check README.md diagrams

### Phase 5: Reorganize Structure (30 minutes)
1. Create ci-cd/ directory
2. Move files to new structure
3. Update internal links
4. Create docs/README.md navigation

**Total Estimated Time**: 4 hours

---

## ✅ SUCCESS CRITERIA

After cleanup:
- [ ] Every code reference (file:line) is verified accurate
- [ ] All Mermaid diagrams match actual code architecture
- [ ] No duplicate documentation
- [ ] Historical docs archived, not deleted
- [ ] Documentation structure is intuitive
- [ ] All active docs have clear purpose
- [ ] Cross-references work (no broken links)

---

## 🚀 NEXT STEPS

1. Execute Phase 1 (archive sprint summaries)
2. Execute Phase 2 (merge redundant docs)
3. Execute Phase 3 (verify code references)
4. Execute Phase 4 (fix Mermaid diagrams)
5. Execute Phase 5 (reorganize structure)
6. Commit with detailed summary

**Start with**: Phase 1 - Low risk, high impact
