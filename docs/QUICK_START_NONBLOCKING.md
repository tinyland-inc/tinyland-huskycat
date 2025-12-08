# Quick Start: Non-Blocking Git Hooks

## 1-Minute Setup

### Enable Non-Blocking Hooks

**Option A: Configuration File**

Edit or create `.huskycat.yaml`:

```yaml
feature_flags:
  nonblocking_hooks: true
```

**Option B: Environment Variable**

```bash
echo 'export HUSKYCAT_FEATURE_NONBLOCKING_HOOKS=true' >> ~/.bashrc
source ~/.bashrc
```

### Install Hooks

```bash
huskycat setup-hooks
```

## Usage

### Make a Commit (Returns Immediately)

```bash
git add src/myfile.py
git commit -m "feat: add new feature"
```

Output:
```
Validation running in background (PID 12345)
View progress: tail -f .huskycat/runs/latest.log
[main abc1234] feat: add new feature
```

### View Progress

**Terminal 1:**
```bash
git commit -m "feat: add feature"
# Returns immediately
```

**Terminal 2:**
```bash
tail -f .huskycat/runs/latest.log
```

You'll see:
```
┌──────────────────────────────────────────┐
│ HuskyCat Validation (Non-Blocking Mode) │
├──────────┬─────────┬──────┬────────┬────┤
│ Tool     │ Status  │ Time │ Errors │    │
├──────────┼─────────┼──────┼────────┼────┤
│ Overall  │ ████░░  │ 5.2s │        │    │
├──────────┼─────────┼──────┼────────┼────┤
│ black    │ ✓ Done  │ 0.3s │ 0      │    │
│ ruff     │ ✓ Done  │ 0.5s │ 0      │    │
│ mypy     │ ⠋ Run   │ 3.2s │ -      │    │
└──────────┴─────────┴──────┴────────┴────┘
```

## Common Scenarios

### Previous Validation Failed

If the last validation failed, you'll be prompted:

```
  Previous validation FAILED (2 minutes ago)
    Errors:   5
    Warnings: 12

  Proceed with commit anyway? [y/N]
```

**Options:**
- Press `N` (default): Fix issues first
- Press `y`: Proceed despite failures
- Use `git commit --no-verify`: Skip hook entirely

### Check Validation Status

```bash
huskycat status
```

### Clean Old Results

```bash
huskycat clean --max-age 7d
```

## Performance

| Metric              | Blocking | Non-Blocking |
|---------------------|----------|--------------|
| Time to commit      | 30s      | <0.1s        |
| Developer wait time | 30s      | 0s           |
| Tools run           | 4        | 15+          |

## Disable Non-Blocking

### Temporarily

```bash
HUSKYCAT_FEATURE_NONBLOCKING_HOOKS=false git commit -m "message"
```

### Permanently

Remove from `.huskycat.yaml`:

```yaml
feature_flags:
  nonblocking_hooks: false  # or remove line
```

## Troubleshooting

### No Progress Display

Check if validation is running:

```bash
ps aux | grep huskycat
```

View logs:

```bash
cat .huskycat/runs/latest.log
```

### Stuck Processes

```bash
huskycat clean --zombies
```

### Reset State

```bash
rm -rf .huskycat/runs/
```

## Full Documentation

See [docs/nonblocking-hooks.md](./nonblocking-hooks.md) for complete documentation.

## Example Workflow

```bash
# Setup (once)
echo 'feature_flags:' >> .huskycat.yaml
echo '  nonblocking_hooks: true' >> .huskycat.yaml
huskycat setup-hooks

# Daily workflow
git add .
git commit -m "feat: my feature"  # Returns immediately
# Continue working while validation runs in background

# Later: check if validation passed
huskycat status

# If validation failed, fix and recommit
git add .
git commit -m "fix: address validation errors"
```

## Key Benefits

- **No waiting**: Commit returns in <100ms
- **Full validation**: All 15+ tools run in parallel
- **Real-time feedback**: Watch progress with TUI
- **Safety net**: Previous failures block next commit
- **History**: View past validation runs
- **Configurable**: Feature flags for easy enable/disable

## Next Steps

1. Enable non-blocking hooks in config
2. Make a few commits and observe the difference
3. Check validation history with `huskycat status`
4. Read full docs: [docs/nonblocking-hooks.md](./nonblocking-hooks.md)
