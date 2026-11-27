import ctypes
import ctypes.wintypes as wt
import json
import os
import secrets
import subprocess
import sys
import time
import textwrap
import urllib.error
import urllib.request
from pathlib import Path

GATEWAY = "https://ssh.the-end.shop"
APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "MMD-Remote-Agent"
TOKEN_FILE = APP_DIR / "device.dat"
POLL_SECONDS = 2
MAX_COMMAND_SECONDS = 1800

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

crypt32 = ctypes.WinDLL("Crypt32.dll", use_last_error=True)
kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
crypt32.CryptProtectData.argtypes = [ctypes.POINTER(DATA_BLOB), wt.LPCWSTR, ctypes.POINTER(DATA_BLOB), wt.LPVOID, wt.LPVOID, wt.DWORD, ctypes.POINTER(DATA_BLOB)]
crypt32.CryptProtectData.restype = wt.BOOL
crypt32.CryptUnprotectData.argtypes = [ctypes.POINTER(DATA_BLOB), ctypes.POINTER(wt.LPWSTR), ctypes.POINTER(DATA_BLOB), wt.LPVOID, wt.LPVOID, wt.DWORD, ctypes.POINTER(DATA_BLOB)]
crypt32.CryptUnprotectData.restype = wt.BOOL
kernel32.LocalFree.argtypes = [wt.HLOCAL]
kernel32.LocalFree.restype = wt.HLOCAL

def blob(data: bytes):
    buf = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte))), buf

def dpapi_protect(data: bytes) -> bytes:
    source, keep = blob(data)
    result = DATA_BLOB()
    if not crypt32.CryptProtectData(ctypes.byref(source), "MMD Remote Agent", None, None, None, 0, ctypes.byref(result)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel32.LocalFree(result.pbData)

def dpapi_unprotect(data: bytes) -> bytes:
    source, keep = blob(data)
    result = DATA_BLOB()
    description = wt.LPWSTR()
    if not crypt32.CryptUnprotectData(ctypes.byref(source), ctypes.byref(description), None, None, None, 0, ctypes.byref(result)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel32.LocalFree(result.pbData)
        if description:
            kernel32.LocalFree(description)

def http_json(path: str, method="POST", payload=None, token=None, timeout=25):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(GATEWAY + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(1024 * 1024)
            return response.status, json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read(4096).decode("utf-8", "replace")
        try:
            detail = json.loads(raw)
        except Exception:
            detail = {"error": raw or str(exc)}
        return exc.code, detail

def pair():
    code = f"{secrets.randbelow(100_000_000):08d}"
    secret = secrets.token_urlsafe(32)
    print("\nA one-time pairing code has been generated on this computer:")
    print("\n  " + code + "\n")
    print("Open https://ssh.the-end.shop/ and enter this code there.")
    print("The code expires in 3 minutes. Waiting for website confirmation...")

    status, data = http_json("/agent/pair/init", payload={"code": code, "secret": secret})
    if status != 200 or not isinstance(data, dict) or data.get("ok") is not True:
        print("Could not register pairing code: HTTP", status)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        status, data = http_json("/agent/pair/complete", payload={"code": code, "secret": secret})
        token = data.get("device_token") if isinstance(data, dict) else None
        if status == 200 and isinstance(data, dict) and data.get("paired") is True and token:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            TOKEN_FILE.write_bytes(dpapi_protect(token.encode("utf-8")))
            print("Connection saved securely with Windows DPAPI.")
            return token
        if status == 202:
            time.sleep(2)
            continue
        if status in (401, 404, 410):
            print("Pairing failed or expired: HTTP", status)
            print(json.dumps(data, ensure_ascii=False, indent=2))
            raise SystemExit(1)
        print("Pairing check failed: HTTP", status, data)
        time.sleep(3)

    print("Pairing code expired. Run the app again to generate a new code.")
    raise SystemExit(1)

def load_token():
    try:
        return dpapi_unprotect(TOKEN_FILE.read_bytes()).decode("utf-8").strip()
    except FileNotFoundError:
        return None
    except Exception:
        try:
            TOKEN_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        return None

def run_powershell(command: str):
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=MAX_COMMAND_SECONDS, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        output = result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        return output[-30000:], result.returncode
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return str(out) + "\nCommand timed out.", 124
    except Exception as exc:
        return f"Execution error: {exc}", 1

def approve(job):
    print("\n\033[38;5;75m  ╭" + "─" * 66 + "╮\033[0m")
    print("\033[1;38;5;221m  │  SECURITY REVIEW  /  APPROVAL REQUIRED\033[0m")
    print("\033[90m  Job ID: " + str(job.get("id", "unknown")) + "\033[0m")
    print("\033[38;5;75m  ╰" + "─" * 66 + "╯\033[0m")
    for line in textwrap.wrap(str(job.get("command", "")), width=64, break_long_words=True, replace_whitespace=False):
        print("  " + line)
    print("\033[38;5;75m  ╰" + "─" * 66 + "╯\033[0m")
    print("\033[93m  Type uppercase YES to approve. Any other input rejects.\033[0m")
    return input("\033[1;97m  Approval > \033[0m").strip() == "YES"

def resolve_approval(job, token, decision):
    status, data = http_json("/agent/approval", payload={"id": job.get("id"), "decision": decision}, token=token)
    if status != 200 or not isinstance(data, dict):
        raise RuntimeError(f"Approval decision failed: HTTP {status} {data}")
    return data.get("approval_status")

def main():
    if os.name != "nt":
        print("This runner currently supports Windows only.")
        return 1
    try:
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("ERROR: Run this terminal as Administrator.")
            return 1
    except Exception:
        print("ERROR: Could not verify Administrator privileges.")
        return 1

    try:
        kernel = ctypes.windll.kernel32
        kernel.SetConsoleTitleW("MMD Remote Agent  |  Secure MCP Gateway")
        handle = kernel.GetStdHandle(-11)
        mode = wt.DWORD()
        if kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel.SetConsoleMode(handle, mode.value | 0x0004)
        os.system("")  # Enable ANSI processing in modern Windows terminals.
    except Exception:
        pass

    C = {"blue":"\033[38;5;75m", "cyan":"\033[38;5;81m", "white":"\033[1;97m", "muted":"\033[38;5;245m", "green":"\033[38;5;78m", "gold":"\033[38;5;221m", "reset":"\033[0m"}
    os.system("cls")
    print(C["blue"] + "  ╭──────────────────────────────────────────────────────────────────────╮")
    print("  │" + C["white"] + "                    M M D   R E M O T E   A G E N T                   " + C["blue"] + "│")
    print("  │" + C["muted"] + "                     SECURE  MCP  •  WINDOWS  NODE                    " + C["blue"] + "│")
    print("  ╰──────────────────────────────────────────────────────────────────────╯" + C["reset"])
    print()
    print("  " + C["cyan"] + "CONNECTION" + C["reset"] + "   " + C["muted"] + "──────────────────────────────────────────────────────" + C["reset"])
    token = load_token()
    if token:
        print("  " + C["green"] + "●" + C["reset"] + "  Saved encrypted device credential found")
    else:
        token = pair()

    print("  " + C["green"] + "● ONLINE" + C["reset"] + "   " + C["muted"] + "Gateway  " + C["reset"] + GATEWAY)
    print("  " + C["green"] + "● READY" + C["reset"] + "    " + C["muted"] + "Approval " + C["reset"] + "Website dashboard  /  Local PowerShell")
    print()
    print("  " + C["cyan"] + "ACTIVITY" + C["reset"] + "     " + C["muted"] + "──────────────────────────────────────────────────────" + C["reset"])
    print("  " + C["green"] + "◉" + C["reset"] + "  " + C["white"] + "Listening for secure MCP commands" + C["reset"])
    print("  " + C["muted"] + "   Press Ctrl+C to disconnect safely" + C["reset"])
    print()
    backoff = 2

    while True:
        try:
            status, data = http_json("/agent/poll", token=token, timeout=30)
            if status == 401:
                print("\nSaved connection is no longer valid. Pair again.")
                TOKEN_FILE.unlink(missing_ok=True)
                token = pair()
                backoff = 2
                continue
            if status != 200:
                raise RuntimeError(f"Gateway HTTP {status}: {data}")
            backoff = 2
            job = data.get("job") if isinstance(data, dict) else None
            if not job:
                time.sleep(POLL_SECONDS)
                continue

            command = job.get("command")
            job_id = job.get("id")
            if not isinstance(command, str) or not command.strip() or not isinstance(job_id, str):
                print("Ignoring malformed job received from gateway.")
                time.sleep(1)
                continue

            approval = job.get("approval_status") or "pending"
            if approval == "pending":
                approval = resolve_approval(job, token, "approve" if approve(job) else "reject")
            if approval == "approved":
                print("\\n\033[92m  ✓ Approved — executing in PowerShell...\033[0m")
                output, exit_code = run_powershell(command)
            else:
                print("\\n\033[91m  ✕ Rejected — command was not executed.\033[0m")
                output, exit_code = "Execution rejected by approval policy.", 125

            payload = {"id": job_id, "output": output, "exit_code": exit_code}
            sent = False
            for attempt in range(1, 6):
                result_status, result = http_json("/agent/result", payload=payload, token=token, timeout=25)
                if result_status == 200 and result.get("ok") is True:
                    sent = True
                    break
                print(f"Result upload attempt {attempt} failed: HTTP {result_status}")
                time.sleep(attempt * 2)
            if sent:
                print(f"\033[92m  ✓ Result delivered · Job={job_id} · ExitCode={exit_code}\033[0m")
            else:
                print("CRITICAL: Result could not be uploaded. Keep this window open and check the connection.")
        except KeyboardInterrupt:
            print("\nDisconnected.")
            return 0
        except Exception as exc:
            print(f"\033[91m  ! Connection error: {exc}\033[0m", file=sys.stderr)
            print(f"\033[90m    Retrying in {backoff}s...\033[0m", file=sys.stderr)
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)

if __name__ == "__main__":
    raise SystemExit(main())
