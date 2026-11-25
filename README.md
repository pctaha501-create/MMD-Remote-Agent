# MMD Remote Agent

Windows console agent that securely connects this PC to the AI/MCP gateway at https://ssh.the-end.shop/.

## Connect

1. Open the website and generate a one-time 8-digit connection code.
2. Run MMD-Remote-Agent.exe on Windows.
3. Enter the code when the console asks for Connection Code.
4. The agent pairs with the gateway and starts listening for MCP jobs.

The device token is stored encrypted with Windows DPAPI in the current Windows user's configuration directory. After the first successful pairing, later launches reconnect automatically. If the token is revoked, the app asks for a fresh connection code.

When replacing a previously paired device, disconnect/revoke the old device on the website before generating another code.

## Command safety

Commands received over MCP are displayed in the local console. They run only after the local user types exactly YES. Rejected commands are reported to the gateway without execution.

The executable requests Administrator privileges because some Windows management commands require elevation. The agent uses outbound HTTPS only; no inbound SSH server or open firewall port is required.

## Build

GitHub Actions builds the Windows executable and publishes it to GitHub Releases on pushes to main.
