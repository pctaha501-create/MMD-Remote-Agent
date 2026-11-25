# MMD Remote Agent

Windows Python runner for the existing AI/MCP gateway at https://ssh.the-end.shop/.

## Run (no build, no EXE, no auto-updater)

1. Open PowerShell **as Administrator**.
2. Go to the folder containing this repository.
3. Run:

   ```powershell
   python .\main.py
   ```

Python 3.10+ is recommended. The runner uses only Python's standard library; no pip packages, compiler, Go build, or EXE are needed.

On first run, generate a one-time 8-digit connection code on https://ssh.the-end.shop/ and enter it when prompted. The device token is stored encrypted with Windows DPAPI in the current Windows user's AppData folder. Later runs reconnect automatically. If the token is revoked, the runner asks for a new code.

Commands received from MCP are displayed in this local console. They execute only if the local user types exactly `YES`; all other input rejects the command. Commands run through PowerShell. Run as Administrator because remote commands may require elevated Windows permissions.

The runner makes outbound HTTPS requests only. It does not open an inbound SSH server or firewall port. It does not download or install updates.
