#!/usr/bin/env python3
"""MMD Remote Agent for Linux (Ubuntu/Kali); standard library only."""
from __future__ import annotations
import argparse
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

GATEWAY = "https://ssh.the-end.shop"
POLL_SECONDS = 2
CONFIG_DIR = Path.home() / ".config" / "mmd-remote-agent"
TOKEN_FILE = CONFIG_DIR / "token"
TRANSIENT_HTTP = {408, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524, 525, 526, 527, 530}
PERMANENT_RESULT_HTTP = {400, 401, 403, 404, 409, 410, 422}

def http_json(path: str, payload=None, token=None, timeout=25):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(GATEWAY + path, data=data, headers=headers, method="POST")
    backoff, attempt = 2, 0
    while True:
        attempt += 1
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read(1024 * 1024)
                return response.status, json.loads(raw.decode("utf-8")) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read(4096).decode("utf-8", "replace")
            if exc.code in TRANSIENT_HTTP:
                print(f"[!] Gateway HTTP {exc.code}; retry {attempt} in {backoff}s", flush=True)
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)
                continue
            try:
                detail = json.loads(raw)
            except Exception:
                detail = {"error": raw or str(exc)}
            return exc.code, detail
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, json.JSONDecodeError) as exc:
            print(f"[!] Connection/response error: {exc}; retry {attempt} in {backoff}s", flush=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)

def save_token(token: str):
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700)
    fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(token)
    os.chmod(TOKEN_FILE, 0o600)

def load_token():
    try:
        return TOKEN_FILE.read_text(encoding="utf-8").strip() or None
    except FileNotFoundError:
        return None

def pair(previous_token=None):
    code = f"{secrets.randbelow(100_000_000):08d}"
    secret = secrets.token_urlsafe(32)
    status, data = http_json("/agent/pair/init", {"code": code, "secret": secret}, previous_token)
    if status != 200 or data.get("ok") is not True:
        raise RuntimeError(f"Pairing init failed: HTTP {status} {data}")
    print("\nMMD Remote Agent — Linux pairing")
    print(f"Pairing code: {code}")
    print("Enter this code in the website dashboard within 3 minutes.")
    while True:
        status, data = http_json("/agent/pair/complete", {"code": code, "secret": secret}, previous_token)
        if status == 202:
            time.sleep(POLL_SECONDS)
            continue
        if status == 200 and data.get("paired") is True and isinstance(data.get("device_token"), str):
            save_token(data["device_token"])
            print(f"Paired successfully. Device ID: {data.get('device_id')}")
            return data["device_token"]
        raise RuntimeError(f"Pairing failed: HTTP {status} {data}")
def approve_job(job, token):
    print("\n" + "=" * 68)
    print("COMMAND REQUIRES LOCAL APPROVAL")
    print("=" * 68)
    print(job.get("command", ""))
    print("=" * 68)
    decision = "approve" if input("Type YES to execute; anything else rejects: ").strip() == "YES" else "reject"
    status, data = http_json("/agent/approval", {"id": job["id"], "decision": decision}, token)
    if status != 200:
        raise RuntimeError(f"Approval update failed: HTTP {status} {data}")
    return data.get("approval_status", "pending")

def run_shell(command):
    try:
        result = subprocess.run(command, shell=True, executable="/bin/bash",
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, errors="replace")
        return result.stdout or "", result.returncode
    except Exception as exc:
        return f"Command execution error: {exc}", 1

def main(argv=None):
    parser = argparse.ArgumentParser(description="MMD Remote Agent for Linux")
    parser.add_argument("--pair", action="store_true", help="re-pair this Linux device")
    args = parser.parse_args(argv)
    token = load_token()
    if args.pair:
        token = pair(token)
    elif not token:
        token = pair()
    print(f"\nMMD Remote Agent ONLINE — Linux — {GATEWAY}")
    backoff = 2
    while True:
        try:
            status, data = http_json("/agent/poll", {"os": "linux", "version": "2.2.0-linux"}, token, timeout=30)
            if status == 401:
                print("[!] Saved device token expired; starting secure re-pair.")
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
            command, job_id = job.get("command"), job.get("id")
            if not isinstance(command, str) or not command.strip() or not isinstance(job_id, str):
                print("[!] Ignoring malformed job.")
                time.sleep(1)
                continue
            approval = job.get("approval_status") or "pending"
            if approval == "pending":
                approval = approve_job(job, token)
            if approval == "approved":
                print(f"\n[+] Approved — executing with Bash — job {job_id}")
                output, exit_code = run_shell(command)
            else:
                print(f"\n[-] Rejected — job {job_id}")
                output, exit_code = "Execution rejected by approval policy.", 125
            payload = {"id": job_id, "output": output, "exit_code": exit_code}
            attempt, delay = 0, 2
            while True:
                attempt += 1
                rs, result = http_json("/agent/result", payload, token, timeout=25)
                if rs == 200 and isinstance(result, dict) and result.get("ok") is True:
                    print(f"[+] Result delivered — {job_id} — exit {exit_code}")
                    if output.strip():
                        print(output.rstrip())
                    break
                print(f"[!] Result upload attempt {attempt} failed: HTTP {rs}")
                if rs in PERMANENT_RESULT_HTTP:
                    print("[CRITICAL] Result not accepted; keep this agent window open.")
                    break
                time.sleep(delay)
                delay = min(delay * 2, 30)
        except KeyboardInterrupt:
            print("\nAgent stopped safely.")
            return 0
        except Exception as exc:
            print(f"[!] Agent error: {exc}; retrying in {backoff}s", file=sys.stderr, flush=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)

if __name__ == "__main__":
    raise SystemExit(main())
