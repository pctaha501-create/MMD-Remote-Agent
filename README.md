# MMD Remote Agent

A minimal Windows console agent for the private MCP gateway at `https://ssh.the-end.shop`.

## What it does

- Runs as **Administrator** (Windows UAC prompt is embedded in the executable manifest).
- Connects outbound over HTTPS; no inbound port, SSH server, tunnel, Electron, or extra runtime.
- Polls the gateway for queued jobs and returns command output and exit code.
- Requires local interactive approval: type exactly `YES` for each command.
- Retries transient network failures with backoff and retries result uploads.
- Uses only the Go standard library at runtime.

## Build

GitHub Actions builds the Windows x64 executable on every push to `main`. Download it from the workflow run's Artifacts section. Tag a commit with `v1.0.0` to publish a GitHub Release asset.

## Configure

Set the agent token provided by the gateway administrator in the current PowerShell session, then launch the executable:

```powershell
$env:SSH_GATEWAY_TOKEN = Read-Host "Agent token"
.\MMD-Remote-Agent.exe
```

Do not commit or share the token. The agent intentionally does not persist it in a plaintext config file.

## Safety

Administrator mode grants broad local authority, but remote commands are **not** executed automatically. Each command is displayed and requires a local `YES` confirmation. Only connect to a gateway you control. The agent does not implement arbitrary remote file access.
