# LangGraph for Dependency Orchestration

**Date:** 2026-02-06
**Status:** Research / RFC
**Context:** Evaluating LangGraph as an orchestration layer for multi-MR dependency update workflows in huskycat, complementing Renovate Bot for automated dependency management.

---

## Table of Contents

1. [LangGraph Architecture Overview](#1-langgraph-architecture-overview)
2. [Multi-MR Orchestration Patterns](#2-multi-mr-orchestration-patterns)
3. [Dependency Management Automation with Stateful Agents](#3-dependency-management-automation-with-stateful-agents)
4. [Comparison Matrix](#4-comparison-matrix)
5. [Prototype Graph Design](#5-prototype-graph-design)
6. [Integration Points](#6-integration-points)
7. [Risks and Open Questions](#7-risks-and-open-questions)

---

## 1. LangGraph Architecture Overview

LangGraph (by LangChain, MIT-licensed) is a low-level orchestration framework for building stateful, multi-step workflows as directed graphs. As of October 2025 it reached 1.0 stable, signaling production readiness. The framework models workflows as state machines with durable execution semantics -- making it a candidate for complex CI/CD orchestration that goes beyond what cron-based or event-driven tools handle natively.

### 1.1 Core Primitives

**Nodes** are Python functions that receive the current graph state and return state updates:

```python
from langgraph.graph import StateGraph, START, END

def check_versions(state: WorkflowState) -> dict:
    """Node: compare current vs latest dependency versions."""
    outdated = find_outdated_deps(state["lock_file"])
    return {"outdated_deps": outdated, "status": "versions_checked"}
```

**Edges** define transitions between nodes. Three types exist:

| Edge Type | Purpose | Example |
|-----------|---------|---------|
| Normal | Fixed A -> B transition | `graph.add_edge("check", "update")` |
| Conditional | Route based on state | `graph.add_conditional_edges("ci", route_on_result)` |
| START/END | Entry and terminal points | `graph.add_edge(START, "checkout")` |

**State** is a shared TypedDict (or Pydantic model) that flows through the graph. Annotated reducers control how node outputs merge into state:

```python
from typing import Annotated, TypedDict
from operator import add

class WorkflowState(TypedDict):
    repo_url: str
    branch: str
    outdated_deps: list[dict]
    mr_ids: Annotated[list[int], add]       # append, never overwrite
    ci_results: dict[str, str]
    error_log: Annotated[list[str], add]    # accumulate errors
    status: str
```

The `Annotated[list, add]` pattern is critical for fan-out/fan-in: when multiple parallel nodes return `mr_ids`, the reducer appends all results rather than overwriting.

### 1.2 StateGraph Construction

```python
from langgraph.graph import StateGraph, START, END

builder = StateGraph(WorkflowState)

# Add nodes (functions)
builder.add_node("checkout", git_checkout_node)
builder.add_node("detect_updates", detect_updates_node)
builder.add_node("update_deps", update_deps_node)
builder.add_node("run_ci", run_ci_node)
builder.add_node("merge", merge_node)

# Add edges
builder.add_edge(START, "checkout")
builder.add_edge("checkout", "detect_updates")
builder.add_conditional_edges(
    "detect_updates",
    lambda state: "update_deps" if state["outdated_deps"] else END
)
builder.add_edge("update_deps", "run_ci")
builder.add_conditional_edges(
    "run_ci",
    lambda state: "merge" if state["ci_results"]["status"] == "pass" else END
)
builder.add_edge("merge", END)

# Compile with persistence
graph = builder.compile(checkpointer=checkpointer)
```

### 1.3 Persistence Backends

Persistence is the mechanism that makes LangGraph suitable for long-running workflows. A **checkpointer** saves the full graph state at every super-step (a round of parallel node execution).

| Backend | Package | Use Case |
|---------|---------|----------|
| `InMemorySaver` | `langgraph` (built-in) | Development, testing |
| `SqliteSaver` | `langgraph-checkpoint-sqlite` | Single-instance local workflows |
| `PostgresSaver` | `langgraph-checkpoint-postgres` | Production, multi-instance |
| `CosmosDBSaver` | `langgraph-checkpoint-cosmosdb` | Azure environments |

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost:5432/langgraph"
)
graph = builder.compile(checkpointer=checkpointer)

# Every invocation uses a thread_id for state isolation
config = {"configurable": {"thread_id": "dep-update-2026-02-06"}}
result = graph.invoke(initial_state, config)
```

**Key properties of checkpointing:**

- State survives process restarts -- resume from the last successful super-step
- Failed nodes do not corrupt state; successful sibling nodes in the same super-step are preserved
- `graph.get_state(config)` retrieves the current snapshot
- `graph.get_state_history(config)` enables time-travel debugging
- `graph.update_state(config, values)` allows manual state correction (human-in-the-loop)

### 1.4 Durable Execution Model

LangGraph's durable execution means:

1. **Automatic checkpointing** at every super-step boundary
2. **Fault isolation** -- if node B fails in a super-step where node A succeeded, node A's writes are preserved; on retry only node B re-executes
3. **Resumability** -- pass the same `thread_id` and the graph picks up from the last checkpoint
4. **Idempotency** -- nodes should be written to be idempotent since they may re-execute after failure

This is analogous to Temporal's durable execution model but with a lighter runtime: no separate Temporal server needed, just a database for checkpoints.

---

## 2. Multi-MR Orchestration Patterns

The core problem: when Renovate proposes N dependency updates, merging them sequentially is slow and fragile. Parallel MR creation is fast but creates merge conflicts when updates touch overlapping files (lock files, CI configs). LangGraph's graph model maps naturally onto this problem.

### 2.1 Fan-Out / Fan-In with Send API

The `Send` API enables dynamic parallelism -- the number of parallel branches is determined at runtime based on how many updates are detected:

```python
from langgraph.types import Send

class MRState(TypedDict):
    """State for a single MR processing branch."""
    dep_name: str
    dep_version: str
    branch_name: str
    mr_id: int | None
    ci_status: str

class OrchestratorState(TypedDict):
    """Top-level orchestrator state."""
    repo_url: str
    base_branch: str
    updates: list[dict]               # detected updates
    mr_ids: Annotated[list[int], add]  # collected from fan-in
    merge_order: list[int]             # topologically sorted
    status: str

def fan_out_updates(state: OrchestratorState) -> list[Send]:
    """Dispatch one branch per dependency update."""
    return [
        Send("process_single_update", {
            "dep_name": update["name"],
            "dep_version": update["version"],
            "branch_name": f"deps/{update['name']}-{update['version']}",
        })
        for update in state["updates"]
    ]

builder.add_conditional_edges("detect_updates", fan_out_updates)
```

Each `Send` creates an independent execution branch. All branches run concurrently in a single super-step. When all complete, the reducer on `mr_ids` aggregates results and the graph proceeds to the merge-ordering phase.

### 2.2 Conflict Prevention: Topological Merge Ordering

The key insight: even with parallel MR creation, merges must be serialized to avoid lock-file conflicts. The graph models this as a sequential merge phase after the parallel creation phase:

```python
def compute_merge_order(state: OrchestratorState) -> dict:
    """Determine safe merge order based on dependency relationships."""
    dep_graph = build_dependency_graph(state["updates"])
    # Topological sort: merge leaf dependencies first
    order = topological_sort(dep_graph)
    # Map dependency names to MR IDs
    merge_order = [
        mr_id for dep in order
        for mr_id in state["mr_ids"]
        if find_mr_dep(mr_id) == dep
    ]
    return {"merge_order": merge_order}

def merge_next(state: OrchestratorState) -> dict:
    """Merge the next MR in order, rebase remaining."""
    next_mr = state["merge_order"][0]
    merge_result = gitlab_merge(next_mr)
    remaining = state["merge_order"][1:]

    # Rebase all remaining MRs against updated base
    for mr_id in remaining:
        gitlab_rebase(mr_id)

    return {
        "merge_order": remaining,
        "status": "merged" if not remaining else "merging",
    }
```

### 2.3 State Tracking Across Branches

Each MR's lifecycle is tracked in the graph state, enabling visibility and recovery:

```
OrchestratorState
  |-- updates[]           # Input: what needs updating
  |-- mr_ids[]            # Fan-in: created MRs
  |-- merge_order[]       # Computed: safe merge sequence
  |-- ci_results{}        # Map<mr_id, pass|fail|pending>
  |-- failed_mrs[]        # MRs that failed CI
  |-- merged_mrs[]        # Successfully merged
  |-- status              # Overall workflow status
```

Using `graph.get_state(config)`, an operator can inspect exactly which MRs are pending, which failed, and which merged -- at any point, even after a process restart.

### 2.4 Supervisor Pattern for Multi-Agent Coordination

For complex scenarios, a supervisor agent oversees specialized worker agents:

```python
def supervisor_node(state: OrchestratorState) -> Command:
    """Central coordinator that dispatches work and handles exceptions."""
    if state["status"] == "ci_failed":
        return Command(
            update={"status": "resolving_conflicts"},
            goto="conflict_resolver"
        )
    elif state["status"] == "all_ci_passed":
        return Command(
            update={"status": "merging"},
            goto="sequential_merger"
        )
    elif state["status"] == "merge_conflict":
        return Command(
            update={"status": "rebasing"},
            goto="rebase_handler"
        )
    else:
        return Command(goto=END)
```

---

## 3. Dependency Management Automation with Stateful Agents

### 3.1 Version Bumping Node

```python
import subprocess
import tomllib

def version_bump_node(state: MRState) -> dict:
    """Update dependency version in pyproject.toml or package.json."""
    dep = state["dep_name"]
    version = state["dep_version"]
    ecosystem = state.get("ecosystem", "python")

    if ecosystem == "python":
        # Use uv for Python dependency management
        result = subprocess.run(
            ["uv", "add", f"{dep}>={version}"],
            capture_output=True, text=True, cwd=state["work_dir"]
        )
    elif ecosystem == "npm":
        result = subprocess.run(
            ["npm", "install", f"{dep}@{version}"],
            capture_output=True, text=True, cwd=state["work_dir"]
        )
    elif ecosystem == "nix":
        result = subprocess.run(
            ["nix", "flake", "update", dep],
            capture_output=True, text=True, cwd=state["work_dir"]
        )

    if result.returncode != 0:
        return {"error_log": [f"Version bump failed for {dep}: {result.stderr}"]}

    return {"status": "version_bumped"}
```

### 3.2 Compatibility Checking Node

```python
def compatibility_check_node(state: MRState) -> dict:
    """Verify updated dependency doesn't break type checking or imports."""
    work_dir = state["work_dir"]
    checks = []

    # Type checking
    mypy_result = subprocess.run(
        ["mypy", "--no-error-summary", "src/"],
        capture_output=True, text=True, cwd=work_dir
    )
    checks.append(("mypy", mypy_result.returncode == 0, mypy_result.stdout))

    # Import verification
    import_result = subprocess.run(
        ["python", "-c", f"import {state['dep_name']}; print('OK')"],
        capture_output=True, text=True, cwd=work_dir
    )
    checks.append(("import", import_result.returncode == 0, import_result.stderr))

    failed = [name for name, passed, _ in checks if not passed]
    if failed:
        return {
            "error_log": [f"Compatibility check failed: {', '.join(failed)}"],
            "ci_status": "compat_fail",
        }

    return {"ci_status": "compat_pass"}
```

### 3.3 Lock File Regeneration Node

```python
def regenerate_lockfile_node(state: MRState) -> dict:
    """Regenerate lock files after version bump."""
    work_dir = state["work_dir"]
    ecosystem = state.get("ecosystem", "python")

    commands = {
        "python": ["uv", "lock"],
        "npm": ["npm", "install", "--package-lock-only"],
        "nix": ["nix", "flake", "lock"],
    }

    cmd = commands.get(ecosystem)
    if not cmd:
        return {"error_log": [f"Unknown ecosystem: {ecosystem}"]}

    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=work_dir
    )

    if result.returncode != 0:
        return {"error_log": [f"Lock regeneration failed: {result.stderr}"]}

    return {"status": "lock_regenerated"}
```

### 3.4 CI Validation Node

```python
import time
import requests

GITLAB_API = "https://gitlab.example.com/api/v4"

def ci_validation_node(state: MRState) -> dict:
    """Trigger CI pipeline and poll for results."""
    mr_id = state["mr_id"]
    project_id = state["project_id"]
    headers = {"PRIVATE-TOKEN": state["gitlab_token"]}

    # Get pipeline for the MR
    mr_info = requests.get(
        f"{GITLAB_API}/projects/{project_id}/merge_requests/{mr_id}",
        headers=headers,
    ).json()

    pipeline_id = mr_info.get("head_pipeline", {}).get("id")
    if not pipeline_id:
        return {"ci_status": "no_pipeline", "error_log": ["No pipeline found"]}

    # Poll pipeline status (with timeout)
    for _ in range(60):  # 30 min max at 30s intervals
        pipeline = requests.get(
            f"{GITLAB_API}/projects/{project_id}/pipelines/{pipeline_id}",
            headers=headers,
        ).json()

        status = pipeline["status"]
        if status in ("success", "failed", "canceled"):
            return {"ci_status": status}

        time.sleep(30)

    return {"ci_status": "timeout", "error_log": ["CI pipeline timed out"]}
```

### 3.5 Subgraph Composition for Per-MR Processing

Each MR's lifecycle (bump -> lock -> test -> push -> CI) is itself a subgraph, composed into the parent orchestrator:

```python
# Per-MR subgraph
mr_builder = StateGraph(MRState)
mr_builder.add_node("version_bump", version_bump_node)
mr_builder.add_node("regen_lock", regenerate_lockfile_node)
mr_builder.add_node("compat_check", compatibility_check_node)
mr_builder.add_node("git_push", git_push_node)
mr_builder.add_node("ci_validate", ci_validation_node)

mr_builder.add_edge(START, "version_bump")
mr_builder.add_edge("version_bump", "regen_lock")
mr_builder.add_edge("regen_lock", "compat_check")
mr_builder.add_conditional_edges(
    "compat_check",
    lambda s: "git_push" if s["ci_status"] == "compat_pass" else END
)
mr_builder.add_edge("git_push", "ci_validate")
mr_builder.add_edge("ci_validate", END)

mr_subgraph = mr_builder.compile()

# Parent orchestrator uses subgraph as a node
orchestrator = StateGraph(OrchestratorState)
orchestrator.add_node("process_update", mr_subgraph)  # nested graph
```

---

## 4. Comparison Matrix

| Dimension | Serial Scripts | Renovate Native | Claude Code Hooks | LangGraph Orchestration |
|---|---|---|---|---|
| **Parallelism** | None. Sequential execution only. | Per-MR parallel creation; sequential merge via `prConcurrentLimit`. | Single-session sequential. Multi-session possible but uncoordinated. | Native fan-out/fan-in. Dynamic parallelism via `Send` API. Concurrent super-steps. |
| **Error Recovery** | Manual restart from beginning. No partial progress saved. | Automatic retry on MR conflicts. Dashboard shows failed MRs. | Claude can retry within session. No cross-session recovery. | Automatic resume from last checkpoint. Failed nodes re-execute; successful siblings preserved. Time-travel debugging. |
| **State Persistence** | None beyond filesystem artifacts. | Renovate maintains internal state in `renovate.json` dashboard issue. | Ephemeral per-session memory. `.claude/` project memory for context. | Full state in PostgreSQL/SQLite. Thread-based isolation. Cross-session, cross-process. |
| **Conflict Resolution** | Manual developer intervention. | Auto-rebase with `rebaseWhen: "behind-base-branch"`. Limited to rebase strategy. | LLM can reason about conflicts but no structured workflow. | Graph-modeled: detect conflict -> rebase -> re-validate -> retry merge. Conditional edges handle each outcome. |
| **Extensibility** | Shell scripts; hard to compose. | `packageRules`, `customManagers` (regex), `postUpdateOptions`. Declarative but bounded. | Fully programmable via hooks (`PreToolUse`, `PostToolUse`). MCP servers for tool access. | Arbitrary Python nodes. Subgraph composition. Add nodes/edges without restructuring. |
| **Observability** | Log files. | Dependency Dashboard issue. MR descriptions with changelogs. | Session transcripts. | `get_state()`, `get_state_history()` API. LangSmith tracing. LangGraph Studio visual debugger. |
| **Human-in-the-Loop** | Fully manual. | `automerge: false` for manual review. Dashboard checkboxes. | Interactive by design. Developer approves each action. | `interrupt()` pauses graph. `update_state()` for manual correction. Resume with `invoke()`. |
| **Setup Complexity** | Low. Shell scripts + cron. | Medium. JSON config + bot hosting or Mend cloud. | Low. `.claude/settings.json` hooks. | High. Python code + persistence backend + deployment infrastructure. |
| **Best For** | Simple, infrequent updates. Single-ecosystem repos. | Steady-state dependency updates. Broad ecosystem coverage. | Ad-hoc fixes. Complex reasoning about breaking changes. | Multi-MR orchestration with ordering constraints. Cross-ecosystem coordinated upgrades. |

### When to Use What

- **Renovate alone**: Standard dependency updates where `automerge` + `packageRules` suffice (80% of cases).
- **Renovate + Claude Code hooks**: When MR merge requires reasoning (breaking API changes, migration scripts).
- **LangGraph orchestration**: When you need coordinated multi-MR merges with dependency ordering, cross-ecosystem lock-file regeneration, and automated conflict resolution.
- **LangGraph + Renovate**: Renovate detects updates and creates MRs; LangGraph orchestrates the merge-rebase-validate cycle.

---

## 5. Prototype Graph Design

### 5.1 Mermaid Diagram

```mermaid
graph TD
    START((START)) --> GitCheckout

    GitCheckout["GitCheckout<br/><i>Clone repo, create worktree</i>"]
    GitCheckout --> DetectUpdates

    DetectUpdates["DetectUpdates<br/><i>Parse Renovate MRs or scan deps</i>"]
    DetectUpdates -->|"updates found"| FanOut
    DetectUpdates -->|"no updates"| END_NODE((END))

    FanOut{"Fan-Out<br/><i>Send() per update</i>"}

    FanOut --> DU1["DependencyUpdate<br/><i>bump + lock + test</i>"]
    FanOut --> DU2["DependencyUpdate<br/><i>bump + lock + test</i>"]
    FanOut --> DUN["DependencyUpdate<br/><i>... N branches</i>"]

    DU1 --> CIValidate1["CIValidate<br/><i>push branch, poll pipeline</i>"]
    DU2 --> CIValidate2["CIValidate<br/><i>push branch, poll pipeline</i>"]
    DUN --> CIValidateN["CIValidate<br/><i>push branch, poll pipeline</i>"]

    CIValidate1 --> FanIn
    CIValidate2 --> FanIn
    CIValidateN --> FanIn

    FanIn["FanIn / Aggregate<br/><i>Collect MR IDs + CI results</i>"]
    FanIn --> ComputeOrder

    ComputeOrder["ComputeMergeOrder<br/><i>Topological sort on dep graph</i>"]
    ComputeOrder --> MergeLoop

    MergeLoop{"MergeNext?"}
    MergeLoop -->|"queue not empty"| MergeCommit
    MergeLoop -->|"queue empty"| END_NODE

    MergeCommit["MergeCommit<br/><i>Merge MR, rebase remaining</i>"]
    MergeCommit --> PostMergeCI

    PostMergeCI["PostMergeCI<br/><i>Validate base after merge</i>"]
    PostMergeCI -->|"pass"| MergeLoop
    PostMergeCI -->|"fail"| ConflictResolve

    ConflictResolve["ConflictResolve<br/><i>Revert or fix conflicts</i>"]
    ConflictResolve -->|"resolved"| PostMergeCI
    ConflictResolve -->|"unresolvable"| NotifyHuman

    NotifyHuman["NotifyHuman<br/><i>interrupt() + alert</i>"]
    NotifyHuman --> END_NODE

    style GitCheckout fill:#e1f5fe
    style DetectUpdates fill:#e1f5fe
    style DU1 fill:#fff3e0
    style DU2 fill:#fff3e0
    style DUN fill:#fff3e0
    style CIValidate1 fill:#e8f5e9
    style CIValidate2 fill:#e8f5e9
    style CIValidateN fill:#e8f5e9
    style MergeCommit fill:#fce4ec
    style ConflictResolve fill:#fce4ec
    style NotifyHuman fill:#f3e5f5
```

### 5.2 Node Type Specifications

#### GitCheckout

```python
def git_checkout_node(state: OrchestratorState) -> dict:
    """Clone or update repo, create isolated worktree."""
    work_dir = Path(f"/tmp/dep-updates/{state['thread_id']}")
    work_dir.mkdir(parents=True, exist_ok=True)

    if not (work_dir / ".git").exists():
        subprocess.run(
            ["git", "clone", state["repo_url"], str(work_dir)],
            check=True,
        )

    subprocess.run(
        ["git", "fetch", "origin"], cwd=work_dir, check=True
    )
    subprocess.run(
        ["git", "checkout", state["base_branch"]], cwd=work_dir, check=True
    )
    subprocess.run(
        ["git", "pull", "--rebase"], cwd=work_dir, check=True
    )

    return {"work_dir": str(work_dir), "status": "checked_out"}
```

#### DependencyUpdate (Subgraph)

This is the per-MR subgraph described in Section 3.5, compiled and used via `Send`:

```python
def fan_out_to_updates(state: OrchestratorState) -> list[Send]:
    return [
        Send("dependency_update_subgraph", {
            "dep_name": u["name"],
            "dep_version": u["version"],
            "ecosystem": u["ecosystem"],
            "work_dir": state["work_dir"],
            "base_branch": state["base_branch"],
            "project_id": state["project_id"],
            "gitlab_token": state["gitlab_token"],
        })
        for u in state["updates"]
    ]
```

#### CIValidate

See Section 3.4. Polls GitLab pipeline status with configurable timeout.

#### ConflictResolve

```python
def conflict_resolve_node(state: OrchestratorState) -> dict:
    """Attempt automated conflict resolution."""
    mr_id = state["current_mr"]
    work_dir = state["work_dir"]

    # Try rebase first
    rebase_result = subprocess.run(
        ["git", "rebase", f"origin/{state['base_branch']}"],
        capture_output=True, text=True, cwd=work_dir,
    )

    if rebase_result.returncode == 0:
        subprocess.run(
            ["git", "push", "--force-with-lease"], cwd=work_dir, check=True
        )
        return {"status": "conflict_resolved"}

    # Rebase failed -- check if it is a lock-file-only conflict
    conflict_files = get_conflict_files(work_dir)
    lock_files = {"uv.lock", "package-lock.json", "flake.lock"}

    if set(conflict_files).issubset(lock_files):
        # Abort rebase, take ours, regenerate lock
        subprocess.run(["git", "rebase", "--abort"], cwd=work_dir)
        subprocess.run(
            ["git", "rebase", "-X", "ours", f"origin/{state['base_branch']}"],
            cwd=work_dir,
        )
        # Regenerate lock files
        regenerate_lockfile_node(state)
        subprocess.run(["git", "add", "."], cwd=work_dir)
        subprocess.run(
            ["git", "commit", "--amend", "--no-edit"], cwd=work_dir
        )
        subprocess.run(
            ["git", "push", "--force-with-lease"], cwd=work_dir
        )
        return {"status": "conflict_resolved_via_lock_regen"}

    # Non-trivial conflict -- escalate
    return {"status": "unresolvable", "error_log": [
        f"Merge conflict in non-lock files: {conflict_files}"
    ]}
```

#### MergeCommit

```python
def merge_commit_node(state: OrchestratorState) -> dict:
    """Merge next MR in topological order via GitLab API."""
    mr_id = state["merge_order"][0]
    project_id = state["project_id"]
    headers = {"PRIVATE-TOKEN": state["gitlab_token"]}

    # Attempt merge
    response = requests.put(
        f"{GITLAB_API}/projects/{project_id}/merge_requests/{mr_id}/merge",
        headers=headers,
        json={
            "merge_when_pipeline_succeeds": False,
            "squash": True,
            "should_remove_source_branch": True,
        },
    )

    if response.status_code == 200:
        return {
            "merge_order": state["merge_order"][1:],
            "merged_mrs": [mr_id],
            "status": "merged_one",
        }
    elif response.status_code == 406:  # Not mergeable
        return {
            "current_mr": mr_id,
            "status": "merge_conflict",
        }
    else:
        return {
            "error_log": [f"Merge failed: {response.status_code} {response.text}"],
            "status": "merge_error",
        }
```

### 5.3 Edge Definitions (Conditional Logic)

```python
def route_after_ci(state: OrchestratorState) -> str:
    """Route based on CI validation results."""
    ci = state["ci_results"]
    if all(v == "success" for v in ci.values()):
        return "compute_merge_order"
    elif any(v == "failed" for v in ci.values()):
        return "handle_ci_failures"
    else:
        return "notify_human"  # unexpected state

def route_after_merge(state: OrchestratorState) -> str:
    """Route based on merge result."""
    match state["status"]:
        case "merged_one":
            if state["merge_order"]:
                return "post_merge_ci"
            return END
        case "merge_conflict":
            return "conflict_resolve"
        case "merge_error":
            return "notify_human"
        case _:
            return END

builder.add_conditional_edges("fan_in", route_after_ci)
builder.add_conditional_edges("merge_commit", route_after_merge)
```

---

## 6. Integration Points

### 6.1 GitLab API for MR Management

LangGraph nodes interact with GitLab through its REST API (v4):

| Operation | API Endpoint | Node |
|-----------|-------------|------|
| Create MR | `POST /projects/:id/merge_requests` | DependencyUpdate |
| Get MR status | `GET /projects/:id/merge_requests/:mr_iid` | CIValidate |
| Merge MR | `PUT /projects/:id/merge_requests/:mr_iid/merge` | MergeCommit |
| Rebase MR | `PUT /projects/:id/merge_requests/:mr_iid/rebase` | ConflictResolve |
| Get pipeline | `GET /projects/:id/pipelines/:pipeline_id` | CIValidate |
| Add MR note | `POST /projects/:id/merge_requests/:mr_iid/notes` | NotifyHuman |

```python
import requests

class GitLabClient:
    def __init__(self, base_url: str, token: str, project_id: int):
        self.base = f"{base_url}/api/v4/projects/{project_id}"
        self.headers = {"PRIVATE-TOKEN": token}

    def create_mr(self, source: str, target: str, title: str) -> dict:
        return requests.post(
            f"{self.base}/merge_requests",
            headers=self.headers,
            json={
                "source_branch": source,
                "target_branch": target,
                "title": title,
                "remove_source_branch": True,
                "squash": True,
            },
        ).json()

    def merge(self, mr_iid: int) -> requests.Response:
        return requests.put(
            f"{self.base}/merge_requests/{mr_iid}/merge",
            headers=self.headers,
            json={"squash": True, "should_remove_source_branch": True},
        )

    def rebase(self, mr_iid: int) -> dict:
        return requests.put(
            f"{self.base}/merge_requests/{mr_iid}/rebase",
            headers=self.headers,
        ).json()

    def get_pipeline_status(self, pipeline_id: int) -> str:
        resp = requests.get(
            f"{self.base}/pipelines/{pipeline_id}",
            headers=self.headers,
        ).json()
        return resp["status"]
```

### 6.2 Renovate Webhooks for Triggering

Renovate itself does not emit webhooks, but GitLab does. The integration pattern:

1. **Renovate creates MRs** with label `dependencies` (configured in `renovate.json`)
2. **GitLab webhook** fires on MR creation events
3. **Webhook receiver** (Flask/FastAPI) filters for `dependencies` label
4. **LangGraph graph** is invoked with the MR details as initial state

```python
from fastapi import FastAPI, Request
from langgraph.graph import StateGraph

app = FastAPI()

@app.post("/webhook/gitlab")
async def handle_gitlab_webhook(request: Request):
    payload = await request.json()

    # Filter for Renovate MR events
    if (
        payload.get("object_kind") == "merge_request"
        and "dependencies" in [l["title"] for l in payload["labels"]]
        and payload["object_attributes"]["action"] == "open"
    ):
        # Batch: collect MRs opened in the same Renovate run
        # then invoke orchestrator graph
        thread_id = f"renovate-batch-{payload['object_attributes']['created_at'][:10]}"
        config = {"configurable": {"thread_id": thread_id}}

        await graph.ainvoke({
            "repo_url": payload["project"]["git_ssh_url"],
            "base_branch": payload["object_attributes"]["target_branch"],
            "mr_id": payload["object_attributes"]["iid"],
        }, config)

    return {"status": "ok"}
```

### 6.3 Claude Code Hooks for Developer Interaction

Claude Code hooks can trigger LangGraph workflows and receive results:

**`.claude/settings.json` hook configuration:**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(git merge:*)",
        "command": "python /path/to/check_merge_safety.py \"$TOOL_INPUT\""
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash(git push:*)",
        "command": "python /path/to/trigger_langgraph.py \"$SESSION_ID\""
      }
    ]
  }
}
```

**`trigger_langgraph.py` -- bridge between Claude Code and LangGraph:**

```python
#!/usr/bin/env python3
"""Triggered by Claude Code PostToolUse hook after git push."""
import sys
import requests

SESSION_ID = sys.argv[1]

# Trigger the LangGraph orchestrator via its API
response = requests.post(
    "http://localhost:8123/runs",
    json={
        "assistant_id": "dep-orchestrator",
        "input": {
            "trigger": "claude_code_push",
            "session_id": SESSION_ID,
        },
        "config": {
            "configurable": {
                "thread_id": f"claude-{SESSION_ID}",
            }
        },
    },
)

print(f"LangGraph run started: {response.json().get('run_id')}")
```

### 6.4 MCP Servers for Tool Access

LangGraph nodes can use MCP (Model Context Protocol) servers for structured tool access. This is relevant when nodes invoke LLM reasoning (e.g., for conflict resolution or changelog generation):

```python
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic

@tool
def read_file(path: str) -> str:
    """Read a file from the repository."""
    with open(path) as f:
        return f.read()

@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    with open(path, "w") as f:
        f.write(content)
    return f"Written {len(content)} bytes to {path}"

@tool
def run_shell(command: str) -> str:
    """Execute a shell command."""
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True
    )
    return result.stdout + result.stderr

# LLM-powered conflict resolver node
llm = ChatAnthropic(model="claude-sonnet-4-20250514")
llm_with_tools = llm.bind_tools([read_file, write_file, run_shell])

def llm_conflict_resolver(state: MRState) -> dict:
    """Use an LLM agent to resolve non-trivial merge conflicts."""
    conflict_files = state["conflict_files"]
    messages = [
        {"role": "system", "content": "You are a dependency conflict resolver."},
        {"role": "user", "content": f"Resolve conflicts in: {conflict_files}"},
    ]
    response = llm_with_tools.invoke(messages)
    # Process tool calls...
    return {"status": "llm_resolved"}
```

### 6.5 LangGraph Platform / LangSmith Deployment

For production deployment, LangGraph Platform (now LangSmith Deployment) provides:

- **Cron scheduling**: Run the dependency orchestrator on a schedule without external cron
- **Task queues**: Auto-scaling background task execution
- **30+ API endpoints**: Thread management, run management, state inspection
- **LangGraph Studio**: Visual debugger for graph execution
- **Streaming**: Real-time progress updates to webhook receivers or dashboards

```python
# langgraph.json -- deployment configuration
{
    "graphs": {
        "dep_orchestrator": {
            "module": "dep_orchestrator.graph:compiled_graph",
            "env": {
                "GITLAB_TOKEN": "${GITLAB_TOKEN}",
                "GITLAB_URL": "${GITLAB_URL}"
            }
        }
    },
    "dependencies": [
        "langgraph-checkpoint-postgres",
        "requests",
        "python-gitlab"
    ]
}
```

---

## 7. Risks and Open Questions

### Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| LangGraph adds significant complexity over Renovate-only | High | Start with Renovate; add LangGraph only for the merge-ordering problem |
| PostgreSQL dependency for production persistence | Medium | Start with SQLite for prototyping; migrate to Postgres when scaling |
| CI polling in nodes ties up graph execution | Medium | Use async nodes with `asyncio.sleep`; or webhook-based CI notification |
| LangGraph 1.0 is new (Oct 2025); API may still shift | Medium | Pin versions; write thin adapter layers around LangGraph primitives |
| Lock-file conflict resolution heuristics may be fragile | Medium | Limit auto-resolution to known-safe patterns (lock-only conflicts) |
| Credential management for GitLab tokens in graph state | High | Use encrypted serializer; never log state containing tokens |

### Open Questions

1. **Batching strategy**: Should the graph wait for all Renovate MRs in a run before starting, or process them as they arrive?
2. **Concurrency limits**: How many parallel `Send` branches before overwhelming CI runners?
3. **Rollback semantics**: If a merged MR breaks something downstream, should the graph support automatic revert?
4. **Cost**: LangGraph Platform pricing for long-running workflows vs. self-hosted with just the checkpoint library.
5. **Alternative**: Would Temporal or Prefect be simpler for the pure orchestration case (no LLM reasoning needed in nodes)?

### Recommended Next Steps

1. Prototype the fan-out/fan-in pattern locally with `InMemorySaver` against a test GitLab project
2. Validate the topological merge-ordering logic with huskycat's actual dependency graph
3. Benchmark CI polling overhead vs. webhook-based notification
4. Evaluate whether the LLM-powered conflict resolver justifies LangGraph over simpler orchestrators

---

## References

- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)
- [LangGraph Graph API Docs](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangGraph Persistence Docs](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Workflows and Agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
- [LangGraph Platform GA Announcement](https://www.blog.langchain.com/langgraph-platform-ga/)
- [LangGraph Send API for Dynamic Parallel Execution](https://dev.to/sreeni5018/leveraging-langgraphs-send-api-for-dynamic-and-parallel-workflow-execution-4pgd)
- [LangGraph Subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)
- [LangGraph Multi-Agent Workflows](https://blog.langchain.com/langgraph-multi-agent-workflows/)
- [Claude Code Hooks Guide](https://code.claude.com/docs/en/hooks-guide)
- [Scaling LangGraph Agents: Parallelization, Subgraphs, and Map-Reduce](https://aipractitioner.substack.com/p/scaling-langgraph-agents-parallelization)
