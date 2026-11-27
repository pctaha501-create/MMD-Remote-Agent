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
