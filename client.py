#!/usr/bin/env python3
"""
claude-proxy client — 快速測試用
用法：python client.py "你好，請介紹你自己" [session_id]
"""
import sys
import json
import urllib.request
import urllib.error

PROXY_URL = "http://127.0.0.1:8765"


def chat(message: str, session_id: str = "cli-test") -> str:
    payload = json.dumps({
        "session_id": session_id,
        "message": message,
        "timeout": 120,
    }).encode()

    req = urllib.request.Request(
        f"{PROXY_URL}/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=130) as resp:
            data = json.loads(resp.read())
            return data.get("response", "(no response)")
    except urllib.error.URLError as e:
        return f"❌ 無法連線到 proxy：{e}\n請確認 proxy 已啟動：\n  cd ~/.openclaw/workspace/claude-proxy && uv run python proxy.py"


def health():
    try:
        with urllib.request.urlopen(f"{PROXY_URL}/health", timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python client.py <message> [session_id]")
        print(f"Proxy 狀態: {health()}")
        sys.exit(1)

    msg = sys.argv[1]
    sid = sys.argv[2] if len(sys.argv) > 2 else "cli-test"

    print(f"→ 發送到 session [{sid}]: {msg!r}")
    resp = chat(msg, sid)
    print(f"← 回應:\n{resp}")
