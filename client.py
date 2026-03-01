#!/usr/bin/env python3
"""
claude-proxy client — quick test utility
Usage: python client.py "hello" [session_id]
"""
import sys
import os
import json
import urllib.request
import urllib.error
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

PROXY_URL = "http://127.0.0.1:8765"
TIMEOUT = float(os.getenv("CLAUDE_TIMEOUT_DEFAULT", "20"))


def chat(message: str, session_id: str = "cli-test") -> str:
    payload = json.dumps({
        "session_id": session_id,
        "message": message,
        "timeout": TIMEOUT,
    }).encode()

    req = urllib.request.Request(
        f"{PROXY_URL}/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT + 10) as resp:
            data = json.loads(resp.read())
            return data.get("response", "(no response)")
    except urllib.error.URLError as e:
        return (
            f"❌ Cannot connect to proxy: {e}\n"
            f"Make sure the proxy is running:\n"
            f"  cd ~/.openclaw/skills/claude-proxy && ./start.sh"
        )


def health():
    try:
        with urllib.request.urlopen(f"{PROXY_URL}/health", timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client.py <message> [session_id]")
        print(f"Proxy status: {health()}")
        sys.exit(1)

    msg = sys.argv[1]
    sid = sys.argv[2] if len(sys.argv) > 2 else "cli-test"

    print(f"→ Sending to session [{sid}]: {msg!r} (timeout={TIMEOUT}s)")
    resp = chat(msg, sid)
    print(f"← Response:\n{resp}")
