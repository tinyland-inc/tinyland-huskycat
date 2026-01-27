# HuskyCat v2.0 Beta: 3-Wave Opus Agent Execution Plan

**Created**: 2026-01-27
**Status**: READY FOR EXECUTION
**Model**: claude-opus-4-5 (all agents)
**Structure**: 3 waves × 3 agents = 9 total agents

---

## Executive Summary

This plan orchestrates 9 Opus agents across 3 waves to complete HuskyCat v2.0 beta readiness. Each wave includes a **Gap Analysis Agent** that validates progress and identifies blockers before the next wave begins.

### Current State (2026-01-27)

| Area | Priority | Status | Wave |
|------|----------|--------|------|
| CI Pipeline Stability | HIGH | Fix deployed (commit 7671ae0) | 1 - Verify |
| Binary Installation Flow | HIGH | Working | 1 - Validate |
| Beta Testing Workflow | HIGH | Ready (docs exist) | 2 - Execute |
| Darwin Code Signing | HIGH | Not started | 2 - Plan |
| GPL Sidecar IPC Integration | MEDIUM | Partial | 3 - Complete |
| Attic Nix Cache | MEDIUM | Blocked (K8s prereqs) | 2 - Deploy |
| Honey Infrastructure | LOW | Phase 1 complete | 3 - Monitor |

---

## Wave 1: Foundation Verification

**Objective**: Verify CI stability and validate installation flows before beta outreach

**Duration**: ~30 minutes
**Parallelism**: All 3 agents run concurrently

### Agent 1.1: CI Pipeline Validator
**Type**: `general-purpose`
**Focus**: Verify the runner tag fix works

**Tasks**:
1. Monitor current pipeline (triggered by commits 7671ae0, 5ca1455)
2. Verify `container:build:amd64` runs on Rocky Linux (honey), NOT Darwin M1
3. Check job logs for runner identification
4. Report build success/failure with timing data
5. If failed: identify root cause and propose fix

**Inputs**:
- Pipeline URL: `glab ci status`
- Expected runner: honey (Rocky Linux x86_64)
- Key jobs: `container:build:amd64`, `validate:complete`, `container:tag:latest`

**Success Criteria**:
- [ ] All DinD jobs pick up `honey` runner
- [ ] Container build succeeds
- [ ] Build time < 30 minutes

**Commands**:
```bash
glab ci status --live=false
glab ci view --job container:build:amd64
ssh honey "docker ps" # Verify DinD activity
```

---

### Agent 1.2: Binary Installation Tester
**Type**: `general-purpose`
**Focus**: End-to-end binary installation validation

**Tasks**:
1. Download latest binary from CI artifacts (or release)
2. Test installation on Linux (via container or VM)
3. Verify `huskycat --version`, `huskycat status`, `huskycat validate .`
4. Test `huskycat setup-hooks` in a git repository
5. Document any friction or failures

**Inputs**:
- Binary locations: `dist/bin/huskycat-linux-amd64`, `dist/bin/huskycat-darwin-arm64`
- Test repository: Clone a sample project
- Expected behavior: `docs/BETA_TESTING.md`

**Success Criteria**:
- [ ] Binary executes without errors
- [ ] `--version` shows correct version
- [ ] `setup-hooks` creates `.git/hooks/pre-commit`
- [ ] Validation runs and produces output

**Commands**:
```bash
# Test in container
docker run -it --rm -v $(pwd):/workspace alpine sh
wget <binary-url> -O /usr/local/bin/huskycat
chmod +x /usr/local/bin/huskycat
huskycat --version
huskycat validate /workspace
```

---

### Agent 1.3: Wave 1 Gap Analyst
**Type**: `general-purpose`
**Focus**: Reality check and blocker identification

**Tasks**:
1. Wait for Agents 1.1 and 1.2 to complete (or timeout after 20 min)
2. Collect results from both agents
3. Identify any blockers for Wave 2
4. Assess: Can we proceed to beta testing?
5. Produce go/no-go recommendation

**Inputs**:
- Agent 1.1 output file
- Agent 1.2 output file
- Current CI pipeline status

**Deliverable**: Gap Analysis Report
```markdown
## Wave 1 Gap Analysis

### CI Pipeline Status
- Build: PASS/FAIL
- Runner routing: CORRECT/INCORRECT
- Blockers: [list]

### Binary Installation Status
- Linux: PASS/FAIL
- macOS: PASS/FAIL (if tested)
- Blockers: [list]

### Wave 2 Readiness
- GO / NO-GO
- Required fixes before Wave 2: [list]
```

---

## Wave 2: Beta Enablement & Infrastructure

**Objective**: Enable beta testing, deploy Attic cache, plan Darwin signing

**Duration**: ~45 minutes
**Parallelism**: All 3 agents run concurrently
**Prerequisites**: Wave 1 Gap Analysis = GO

### Agent 2.1: Beta Testing Coordinator
**Type**: `general-purpose`
**Focus**: Prepare for closed beta launch

**Tasks**:
1. Review `docs/BETA_TESTING.md` for completeness
2. Verify GitLab release artifacts are downloadable
3. Create/update issue templates for bug reports
4. Draft beta announcement message
5. Identify 3-5 internal projects for dogfooding

**Inputs**:
- `docs/BETA_TESTING.md` (396 lines)
- GitLab releases page
- Issue templates in `.gitlab/issue_templates/`

**Deliverables**:
- Updated `docs/BETA_TESTING.md` if gaps found
- Bug report issue template
- Beta announcement draft (for review)

**Success Criteria**:
- [ ] Installation instructions verified working
- [ ] Download links valid
- [ ] Issue template created
- [ ] Dogfooding projects identified

---

### Agent 2.2: Attic Cache Deployer
**Type**: `general-purpose`
**Focus**: Deploy Nix binary cache to Civo cluster

**Prerequisites** (must verify):
- [ ] CNPG operator installed
- [ ] ingress_class = "nginx" (not traefik)
- [ ] Cloudflare provider conditional

**Tasks**:
1. Verify/install CloudNativePG operator
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.22/releases/cnpg-1.22.0.yaml
   ```
2. Fix `terraform.tfvars` ingress_class if needed
3. Run `tofu plan` and verify no errors
4. Run `tofu apply` to deploy Attic
5. Verify `nix-cache.fuzzy-dev.tinyland.dev` responds

**Inputs**:
- Repo: `~/git/attic-cache/tofu/stacks/attic`
- Cluster: Civo bitter-darkness-16657317
- Namespace: fuzzy-dev

**Success Criteria**:
- [ ] CNPG operator healthy
- [ ] `tofu apply` succeeds
- [ ] Attic pods running
- [ ] HTTPS endpoint accessible

**Commands**:
```bash
cd ~/git/attic-cache/tofu/stacks/attic
tofu init
tofu plan -out=tfplan
tofu apply tfplan
kubectl get pods -n attic
curl -s https://nix-cache.fuzzy-dev.tinyland.dev/health
```

---

### Agent 2.3: Wave 2 Gap Analyst
**Type**: `general-purpose`
**Focus**: Assess beta readiness and infrastructure state

**Tasks**:
1. Collect results from Agents 2.1 and 2.2
2. Verify beta testing prerequisites met
3. Check Attic deployment status
4. Identify blockers for Wave 3
5. Assess: Darwin signing feasibility without Apple account

**Deliverable**: Gap Analysis Report
```markdown
## Wave 2 Gap Analysis

### Beta Testing Readiness
- Documentation: COMPLETE/INCOMPLETE
- Artifacts: AVAILABLE/MISSING
- Issue templates: CREATED/MISSING
- Blockers: [list]

### Attic Cache Status
- Deployment: SUCCESS/FAILED
- Endpoint: ACCESSIBLE/UNREACHABLE
- Blockers: [list]

### Darwin Signing Assessment
- Apple Developer Account: YES/NO
- Alternative options: [list]
- Recommendation: [proceed/defer]

### Wave 3 Readiness
- GO / NO-GO
- Required fixes: [list]
```

---

## Wave 3: Integration & Polish

**Objective**: Complete GPL sidecar integration, Darwin signing prep, infrastructure cleanup

**Duration**: ~60 minutes
**Parallelism**: All 3 agents run concurrently
**Prerequisites**: Wave 2 Gap Analysis = GO

### Agent 3.1: GPL Sidecar Integrator
**Type**: `general-purpose`
**Focus**: Complete IPC integration for GPL tools

**Context**:
- IPC Client: `src/huskycat/core/gpl_client.py` (complete)
- IPC Server: `gpl-sidecar/server.py` (complete)
- Integration: `unified_validation.py` (NOT started)

**Tasks**:
1. Review existing GPL client/server implementation
2. Add sidecar detection to `unified_validation.py`
3. Route GPL tool execution through IPC when available
4. Create `podman-compose.yml` with both containers
5. Test comprehensive mode with sidecar running

**Deliverables**:
- Updated `unified_validation.py` with sidecar integration
- `podman-compose.yml` for sidecar deployment
- Integration test results

**Success Criteria**:
- [ ] Sidecar detection working
- [ ] GPL tools (shellcheck, hadolint, yamllint) execute via IPC
- [ ] Fallback to skip works when sidecar unavailable

**Code Changes**:
```python
# unified_validation.py - proposed integration
from huskycat.core.gpl_client import is_sidecar_available, execute_gpl_tool

class ShellcheckValidator(BaseValidator):
    def is_available(self) -> bool:
        if self.linting_mode == LintingMode.FAST:
            return is_sidecar_available()
        return True  # Container mode
```

---

### Agent 3.2: Darwin Signing Preparer
**Type**: `general-purpose`
**Focus**: Prepare for macOS code signing (with or without Apple account)

**Tasks**:
1. Document Apple Developer Account requirements
2. Create `entitlements.plist` for hardened runtime
3. Update CI job for signing (currently in `macos-pkg.yml`)
4. Investigate ad-hoc signing as temporary alternative
5. Create signing documentation for future reference

**Deliverables**:
- `entitlements.plist` file
- Updated `docs/macos-code-signing.md`
- CI variables checklist

**Success Criteria**:
- [ ] Signing prerequisites documented
- [ ] Entitlements file created
- [ ] CI job ready (pending credentials)

**Ad-hoc Alternative**:
```bash
# For testing without Apple Developer account
codesign --force --deep --sign - dist/bin/huskycat-darwin-arm64
# Note: Will show Gatekeeper warning but allows local testing
```

---

### Agent 3.3: Final Gap Analyst & Release Checklist
**Type**: `general-purpose`
**Focus**: Comprehensive beta release readiness assessment

**Tasks**:
1. Collect all agent outputs from Waves 1-3
2. Verify all beta prerequisites met
3. Check CI pipeline health
4. Verify infrastructure stability
5. Produce final release checklist

**Deliverable**: Beta Release Readiness Report
```markdown
## HuskyCat v2.0 Beta Release Readiness

### Core Functionality
- [ ] Binary builds passing
- [ ] Container builds passing
- [ ] Validation engine working
- [ ] MCP server operational

### Installation
- [ ] Linux AMD64 binary downloadable
- [ ] macOS ARM64 binary downloadable (unsigned)
- [ ] Installation docs accurate
- [ ] One-line installer tested

### Infrastructure
- [ ] CI pipeline stable
- [ ] Runners correctly routed
- [ ] Attic cache deployed (optional)
- [ ] Monitoring in place

### Documentation
- [ ] BETA_TESTING.md complete
- [ ] Issue templates ready
- [ ] Known limitations documented

### Blockers
- [ ] List any remaining blockers

### Recommendation
- READY FOR BETA / NOT READY
- Next steps: [list]
```

---

## Execution Commands

### Launch Wave 1 (All 3 in Parallel)
```
Task tool with:
  Agent 1.1: subagent_type=general-purpose, prompt="[CI Pipeline Validator tasks]"
  Agent 1.2: subagent_type=general-purpose, prompt="[Binary Installation Tester tasks]"
  Agent 1.3: subagent_type=general-purpose, prompt="[Wave 1 Gap Analyst tasks]"
```

### Launch Wave 2 (After Wave 1 Gap Analysis = GO)
```
Task tool with:
  Agent 2.1: subagent_type=general-purpose, prompt="[Beta Testing Coordinator tasks]"
  Agent 2.2: subagent_type=general-purpose, prompt="[Attic Cache Deployer tasks]"
  Agent 2.3: subagent_type=general-purpose, prompt="[Wave 2 Gap Analyst tasks]"
```

### Launch Wave 3 (After Wave 2 Gap Analysis = GO)
```
Task tool with:
  Agent 3.1: subagent_type=general-purpose, prompt="[GPL Sidecar Integrator tasks]"
  Agent 3.2: subagent_type=general-purpose, prompt="[Darwin Signing Preparer tasks]"
  Agent 3.3: subagent_type=general-purpose, prompt="[Final Gap Analyst tasks]"
```

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| CI still fails after fix | HIGH | LOW | Gap analyst will catch, rollback available |
| Attic deployment blocked | MEDIUM | MEDIUM | Proceed with beta without Nix cache |
| Darwin signing blocked | MEDIUM | HIGH | Use ad-hoc signing for beta |
| GPL integration complex | LOW | MEDIUM | Ship beta without GPL tools initially |

---

## Timeline

| Wave | Start | Duration | End |
|------|-------|----------|-----|
| Wave 1 | T+0 | 30 min | T+30 |
| Gap Analysis 1 | T+30 | 10 min | T+40 |
| Wave 2 | T+40 | 45 min | T+85 |
| Gap Analysis 2 | T+85 | 10 min | T+95 |
| Wave 3 | T+95 | 60 min | T+155 |
| Final Analysis | T+155 | 15 min | T+170 |

**Total estimated time**: ~3 hours

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| CI Pipeline Pass Rate | 100% | All jobs green |
| Binary Installation Success | 100% | All platforms working |
| Beta Docs Complete | 100% | All sections filled |
| Infrastructure Uptime | 99% | Services responding |
| Blocker Count | 0 | No blocking issues |

---

*Plan ready for Wave 1 execution.*
