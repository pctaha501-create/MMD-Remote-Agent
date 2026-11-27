import argparse
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


COLOR_ENABLED=True
COLORS={"cyan":"\033[96m","blue":"\033[94m","green":"\033[92m","yellow":"\033[93m","red":"\033[91m","white":"\033[97m","muted":"\033[90m","bold":"\033[1m","reset":"\033[0m"}
def paint(value,tone="white",bold=False):
    if not COLOR_ENABLED:return str(value)
    return COLORS.get(tone,COLORS["white"])+(COLORS["bold"] if bold else "")+str(value)+COLORS["reset"]
def enable_terminal():
    if os.name=="nt":
        try:
            h=ctypes.windll.kernel32.GetStdHandle(-11);mode=wt.DWORD()
            if ctypes.windll.kernel32.GetConsoleMode(h,ctypes.byref(mode)):ctypes.windll.kernel32.SetConsoleMode(h,mode.value|4)
            ctypes.windll.kernel32.SetConsoleTitleW("MMD Remote Agent | Secure MCP Gateway")
        except Exception:pass
def panel(title,lines,tone="cyan",width=72):
    inner=width-4
    print(paint("  ╭"+"─"*(width-2)+"╮",tone));print(paint("  │ "+title[:inner].ljust(inner)+" │",tone,True));print(paint("  ├"+"─"*(width-2)+"┤",tone))
    for line in lines:
        for chunk in textwrap.wrap(str(line),width=inner) or [""]:print("  │ "+chunk.ljust(inner)+" │")
    print(paint("  ╰"+"─"*(width-2)+"╯",tone))
def banner():
    print();panel("MMD  /  REMOTE AGENT",["SECURE MCP GATEWAY  ·  WINDOWS COMMAND BRIDGE",GATEWAY,"Commands are never executed without explicit approval."],"cyan");print()

def pair():
    code=f"{secrets.randbelow(100_000_000):08d}";secret=secrets.token_urlsafe(32)
    panel("PAIR THIS WINDOWS DEVICE",["Open https://ssh.the-end.shop/ in your browser.","Enter the 8-digit code below. It expires in 3 minutes."],"blue")
    print();print(paint("                 YOUR ONE-TIME PAIRING CODE","muted",True));print(paint("                    ┌──────────────────┐","cyan"));print(paint("                    │    "+code+"    │","white",True));print(paint("                    └──────────────────┘","cyan"));print()
    status,data=http_json("/agent/pair/init",payload={"code":code,"secret":secret})
    if status!=200 or not isinstance(data,dict) or data.get("ok") is not True:
        panel("PAIRING COULD NOT START",[f"Gateway response: HTTP {status}",json.dumps(data,ensure_ascii=False)],"red");raise SystemExit(1)
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        status,data=http_json("/agent/pair/complete",payload={"code":code,"secret":secret});token=data.get("device_token") if isinstance(data,dict) else None
        if status==200 and isinstance(data,dict) and data.get("paired") is True and token:
            APP_DIR.mkdir(parents=True,exist_ok=True);TOKEN_FILE.write_bytes(dpapi_protect(token.encode("utf-8")))
            print(paint("  ✓ Device paired. Credential protected with Windows DPAPI.","green",True));return token
        if status==202:time.sleep(2);continue
        if status in (401,404,409,410):
            panel("PAIRING FAILED",[f"Gateway response: HTTP {status}",json.dumps(data,ensure_ascii=False)],"red");raise SystemExit(1)
        print(paint(f"  ! Pairing check returned HTTP {status}; retrying...","yellow"));time.sleep(3)
    print(paint("  ✕ Pairing code expired. Run with --pair to try again.","red",True));raise SystemExit(1)

def load_token():
    try:
        return dpapi_unprotect(TOKEN_FILE.read_bytes()).decode("utf-8").strip()
    except FileNotFoundError:
        return None
    except Exception as exc:
        try:
            if TOKEN_FILE.exists():
                backup = TOKEN_FILE.with_name("device.dat.corrupt." + time.strftime("%Y%m%d-%H%M%S"))
                TOKEN_FILE.replace(backup)
                print(f"\n[!] Saved credential could not be decrypted; preserved backup: {backup}")
        except Exception as backup_error:
            print(f"\n[!] Saved credential could not be read or backed up: {backup_error}")
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
    command=str(job.get("command",""));panel("MCP COMMAND  /  LOCAL APPROVAL REQUIRED",["Job ID: "+str(job.get("id","unknown")),"Review every line before approving."],"yellow")
    print(paint("  COMMAND","cyan",True));print(paint("  ┌"+"─"*68+"┐","cyan"))
    for line in textwrap.wrap(command,width=66,break_long_words=True,replace_whitespace=False) or [""]:print("  │ "+line.ljust(66)+" │")
    print(paint("  └"+"─"*68+"┘","cyan"));print(paint("  Type YES (uppercase) to execute. Any other input rejects it.","yellow",True))
    try:answer=input(paint("  Approval  > ","white",True)).strip()
    except EOFError:answer=""
    return answer=="YES"

def resolve_approval(job, token, decision):
    status, data = http_json("/agent/approval", payload={"id": job.get("id"), "decision": decision}, token=token)
    if status != 200 or not isinstance(data, dict):
        raise RuntimeError(f"Approval decision failed: HTTP {status} {data}")
    return data.get("approval_status")

def main(argv=None):
    global COLOR_ENABLED
    parser=argparse.ArgumentParser(description="MMD Remote Agent - secure Windows MCP command bridge")
    parser.add_argument("--pair","--re-pair",dest="force_pair",action="store_true",help="revoke saved device and show a fresh 8-digit pairing code")
    parser.add_argument("--no-color",action="store_true",help="disable terminal colors")
    args=parser.parse_args(argv);COLOR_ENABLED=not args.no_color
    if os.name!="nt":print("This runner currently supports Windows only.");return 1
    try:
        if not ctypes.windll.shell32.IsUserAnAdmin():print(paint("ERROR: Run this terminal as Administrator.","red",True));return 1
    except Exception:print("ERROR: Could not verify Administrator privileges.");return 1
    enable_terminal();banner();token=load_token()
    if args.force_pair and token:
        print(paint("  Re-pair requested. Revoking the previous device session...","yellow"))
        try:status,data=http_json("/agent/unpair",token=token)
        except Exception as exc:print(paint(f"  Gateway unreachable; saved credential kept: {exc}","red"));return 1
        if status not in (200,401):print(paint(f"  Re-pair refused: HTTP {status} {data}. Saved credential kept.","red"));return 1
        TOKEN_FILE.unlink(missing_ok=True);print(paint("  Previous device session revoked.","green"));token=None
    if token:print(paint("  ✓ Saved secure connection loaded.","green",True))
    else:token=pair()
    print();panel("AGENT ONLINE",["Gateway  : "+GATEWAY,"Security : Website approval OR local PowerShell approval","Status   : Waiting for MCP commands","Exit     : Ctrl+C"],"green")
    print(paint("  Tip: run  python main.py --pair  to generate a new pairing code.","muted"));print();backoff=2
    while True:
        try:
            status,data=http_json("/agent/poll",token=token,timeout=30)
            if status==401:
                print(paint("\n  ! Saved connection is no longer valid. Starting secure re-pairing...","yellow",True));TOKEN_FILE.unlink(missing_ok=True);token=pair();backoff=2;continue
            if status!=200:raise RuntimeError(f"Gateway HTTP {status}: {data}")
            backoff=2;job=data.get("job") if isinstance(data,dict) else None
            if not job:time.sleep(POLL_SECONDS);continue
            command=job.get("command");job_id=job.get("id")
            if not isinstance(command,str) or not command.strip() or not isinstance(job_id,str):print(paint("  ! Ignoring malformed job received from gateway.","yellow"));time.sleep(1);continue
            approval=job.get("approval_status") or "pending"
            if approval=="pending":approval=resolve_approval(job,token,"approve" if approve(job) else "reject")
            if approval=="approved":print(paint("\n  ✓ Approved — executing in PowerShell...","green",True));output,exit_code=run_powershell(command)
            else:print(paint("\n  ✕ Rejected — command was not executed.","red",True));output,exit_code="Execution rejected by approval policy.",125
            payload={"id":job_id,"output":output,"exit_code":exit_code};sent=False
            for attempt in range(1,6):
                rs,result=http_json("/agent/result",payload=payload,token=token,timeout=25)
                if rs==200 and result.get("ok") is True:sent=True;break
                print(paint(f"  ! Result upload attempt {attempt} failed: HTTP {rs}","yellow"));time.sleep(attempt*2)
            if sent:
                print(paint(f"  ✓ Result delivered  ·  Job {job_id}  ·  Exit code {exit_code}","green" if exit_code==0 else "yellow",True))
                if output.strip():print(paint("  ── COMMAND OUTPUT ──","muted"));print(output.rstrip());print(paint("  ───────────────────","muted"))
            else:print(paint("  CRITICAL: Result could not be uploaded. Keep this window open and check the connection.","red",True))
        except KeyboardInterrupt:print(paint("\n  ● Agent disconnected safely.","muted"));return 0
        except Exception as exc:print(paint(f"  ! Connection error: {exc}","red"),file=sys.stderr);print(paint(f"    Retrying in {backoff}s...","muted"),file=sys.stderr);time.sleep(backoff);backoff=min(backoff*2,30)

if __name__ == "__main__":
    raise SystemExit(main())
