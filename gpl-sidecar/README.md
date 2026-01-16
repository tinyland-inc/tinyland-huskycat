# HuskyCat GPL Sidecar

This directory contains the GPL-licensed sidecar component for HuskyCat.

## License Isolation

The main HuskyCat binary is licensed under **Apache-2.0** and contains NO GPL code.

This sidecar is a **separate component** licensed under **GPL-3.0** that provides
access to GPL-licensed validation tools via IPC (Inter-Process Communication).

## Why Separate?

GPL-3.0 is a copyleft license that requires derivative works to also be GPL-licensed.
By isolating GPL tools in a separate process that communicates via IPC (Unix sockets),
we maintain license compliance:

1. **Main Binary (Apache-2.0)**: Can be embedded in proprietary software
2. **GPL Sidecar (GPL-3.0)**: Optional add-on for comprehensive validation

## Tools Included

| Tool | License | Description |
|------|---------|-------------|
| shellcheck | GPL-3.0 | Shell script static analysis (340+ rules) |
| hadolint | GPL-3.0 | Dockerfile linting (50+ rules) |
| yamllint | GPL-3.0 | YAML validation (30+ rules) |

## IPC Protocol

The sidecar communicates via JSON-RPC 2.0 over Unix domain sockets:

**Socket path**: `/tmp/huskycat-gpl-$UID.sock` or `~/.huskycat/gpl.sock`

**Request format**:
```json
{
  "jsonrpc": "2.0",
  "method": "execute",
  "id": 1,
  "params": {
    "tool": "shellcheck",
    "args": ["-f", "json", "script.sh"],
    "cwd": "/workspace",
    "timeout_ms": 30000
  }
}
```

**Response format**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tool": "shellcheck",
    "exit_code": 0,
    "stdout": "[...]",
    "stderr": "",
    "duration_ms": 125.4
  }
}
```

## Usage

### As a Container

```bash
# Pull the GPL sidecar container
podman pull ghcr.io/tinyland/huskycat-gpl:latest

# Run alongside main HuskyCat
podman-compose up -d
```

### As a Local Process

```bash
# Start the sidecar server
python3 gpl-sidecar/server.py &

# HuskyCat will auto-detect and use it
huskycat validate --comprehensive .
```

## Building

```bash
# Build the GPL sidecar container
podman build -f ContainerFile.gpl-sidecar -t huskycat-gpl .
```

## Distribution

This sidecar is distributed separately from the main HuskyCat binary:

- **Main binary**: `huskycat` (Apache-2.0)
- **GPL sidecar**: `huskycat-gpl` container or `gpl-sidecar/` package (GPL-3.0)

Users who need comprehensive validation with GPL tools must explicitly
install the sidecar component.
