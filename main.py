import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import sys
import time
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
    while True:
        code = input("Enter Connection Code: ").strip()
        if len(code) != 8 or not code.isascii() or not code.isdigit():
            print("Enter the 8-digit code shown on the website.")
            continue
        print("Connecting to gateway...")
        status, data = http_json("/agent/pair", payload={"code": code})
        token = data.get("device_token") if isinstance(data, dict) else None
        if status == 200 and data.get("paired") is True and token:
            try:
                APP_DIR.mkdir(parents=True, exist_ok=True)
                TOKEN_FILE.write_bytes(dpapi_protect(token.encode("utf-8")))
                print("Connection saved securely.")
            except Exception as exc:
                print("Warning: secure token storage failed:", exc)
            return token
        print("Pairing failed:", data.get("error", f"HTTP {status}") if isinstance(data, dict) else f"HTTP {status}")
        print("Generate a fresh connection code on the website and try again.")

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
    print("\n" + "=" * 72)
    print("NEW MCP COMMAND — LOCAL APPROVAL REQUIRED")
    print("Job ID:", job.get("id", "unknown"))
    print("-" * 72)
    print(job.get("command", ""))
    print("-" * 72)
    return input("Type YES to execute this command; anything else rejects it: ").strip() == "YES"

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

    print("=" * 60)
    print("                 MMD REMOTE AGENT")
    print("=" * 60)
    token = load_token()
    if token:
        print("Saved secure connection found.")
    else:
        token = pair()

    print("Gateway:", GATEWAY)
    print("Waiting for MCP commands... (Ctrl+C to exit)")
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

            if approve(job):
                print("Executing...")
                output, exit_code = run_powershell(command)
            else:
                output, exit_code = "Execution rejected locally by the user.", 125

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
                print(f"Result sent. Job={job_id} ExitCode={exit_code}")
            else:
                print("CRITICAL: Result could not be uploaded. Keep this window open and check the connection.")
        except KeyboardInterrupt:
            print("\nDisconnected.")
            return 0
        except Exception as exc:
            print(f"Connection error: {exc} | retrying in {backoff}s", file=sys.stderr)
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)

if __name__ == "__main__":
    raise SystemExit(main())
