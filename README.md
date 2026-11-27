# MMD Remote Agent

Windows agent for the existing MCP gateway: https://ssh.the-end.shop/

## Run
Open PowerShell as Administrator in this folder and run:

    python main.py

Python 3.10+ is recommended. The agent uses only Python's standard library. No SSH server, inbound firewall rule, or additional Python package is required.

On first launch, the agent prints an 8-digit one-time pairing code. Enter it on https://ssh.the-end.shop/ within 3 minutes. The device token is stored using Windows DPAPI.

On later launches, the saved secure connection is reused automatically; a new code is not expected each time. To revoke the current device session and generate a fresh 8-digit code, stop the running agent and run:

    python main.py --pair

The website dashboard keeps its existing appearance and lets you enter the new code. The old device is retired without deleting command history. Use `--no-color` if your terminal does not support ANSI colors.

## Command approval
Every MCP command requires one explicit approval. Approve or reject it either:
- in the website dashboard, or
- in the local PowerShell window by typing uppercase YES (any other input rejects).

The gateway stores the first decision atomically. If the website has already approved a command, the agent receives the approved state and does not ask for a second approval. A rejected command is never executed. The agent also refuses to report execution results for a command without a recorded approval.

## Security
Commands run through PowerShell under the current Windows account. Review the full command before approving it. The agent makes outbound HTTPS requests only.

## Multiple devices

The gateway supports multiple independently paired agents. Pair another Windows PC or Linux agent from its own terminal; do not unpair the existing PC. The dashboard device selector lets you choose a target and rename it. Command queues, local approvals, and auto-approval quotas are scoped to each device.

For MCP clients:
1. Call `list_devices` and choose the exact `device_id`.
2. Call `run_command` with `command` and `device_id`.
3. Poll `get_result` with both the returned job `id` and the same `device_id` until a final status appears.

When exactly one device is online, `device_id` can be omitted from `run_command`; when multiple devices are online it is required. Completed/rejected/failed history is capped at the latest 50 records per device. Queued, running, and pending-approval jobs are preserved.

## Linux agent (Ubuntu / Kali)

Python 3.10+ is required; no third-party packages are used. From this repository directory, run:

    python3 linux_agent.py

On first launch, enter the displayed one-time pairing code in the website dashboard. The agent stores its token under `~/.config/mmd-remote-agent/` with owner-only directory/file permissions. To re-pair, run:

    python3 linux_agent.py --pair

Linux commands execute through Bash. A pending command requires typing uppercase `YES` in the Linux terminal unless the user has explicitly enabled auto-approval for that device in the dashboard.

## Command approval

Each command requires either a local/dashboard approval or an explicitly enabled auto-approval grant for that specific device. Auto-approval consumes one quota unit per command; when the quota is exhausted or revoked, local approval resumes. Review commands before approving them.
