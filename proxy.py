#!/usr/bin/env python3
"""
claude-proxy — 本地 PTY Proxy
把 Telegram/Discord 訊息（透過 OpenClaw）轉發給 claude CLI，再把回應送回。

HTTP API:
  POST /chat        { "session_id": "...", "message": "...", "timeout": 120 }
  DELETE /session   { "session_id": "..." }
  GET  /sessions    列出現有 session
  GET  /health      健康檢查
"""

import asyncio
import os
import pty
import re
import select
import signal
import sys
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# 載入 .env（從 proxy.py 所在目錄）
load_dotenv(Path(__file__).parent / ".env")

# CLAUDE_SETUP_TOKEN → 轉給 claude CLI 用的 ANTHROPIC_API_KEY
_token = os.getenv("CLAUDE_SETUP_TOKEN")
if _token:
    os.environ["ANTHROPIC_API_KEY"] = _token

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ──────────────────────────────────────────────
# 設定
# ──────────────────────────────────────────────
LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 8765

# claude CLI 路徑（npx 方式）
CLAUDE_CMD = ["npx", "-y", "@anthropic-ai/claude-code", "--dangerously-skip-permissions"]

# 偵測 claude 已準備好輸入的 prompt 模式（ANSI 清洗後）
# Claude Code 在等待輸入時會顯示類似 "> " 或包含這些特徵
PROMPT_PATTERNS = [
    re.compile(r">\s*$", re.MULTILINE),           # 標準 > 提示
    re.compile(r"╭─+╮"),                           # 框線 UI
    re.compile(r"Human:\s*$", re.MULTILINE),       # 部分版本
    re.compile(r"\$\s*$", re.MULTILINE),           # shell prompt fallback
]

# 去掉 ANSI escape codes
ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("claude-proxy")

# ──────────────────────────────────────────────
# PTY Session 管理
# ──────────────────────────────────────────────

@dataclass
class ClaudeSession:
    session_id: str
    master_fd: int
    pid: int
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def touch(self):
        self.last_used = time.time()


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub("", text)


def is_prompt_ready(text: str) -> bool:
    """判斷 Claude 是否在等待輸入"""
    clean = strip_ansi(text)
    return any(p.search(clean) for p in PROMPT_PATTERNS)


def read_until_ready(master_fd: int, timeout: float = 30.0) -> str:
    """
    從 PTY 持續讀取，直到：
    1. 偵測到 prompt（Claude 準備好了）
    2. 超時
    回傳累積的原始輸出。
    """
    buf = b""
    deadline = time.time() + timeout
    last_data_time = time.time()
    IDLE_STABLE = 1.5  # 連續無新資料超過這麼久，且已有內容，判定完成

    while time.time() < deadline:
        remaining = deadline - time.time()
        r, _, _ = select.select([master_fd], [], [], min(0.1, remaining))
        if r:
            try:
                chunk = os.read(master_fd, 8192)
                buf += chunk
                last_data_time = time.time()
            except OSError:
                break
        else:
            # 無新資料
            if buf and (time.time() - last_data_time) > IDLE_STABLE:
                text = buf.decode("utf-8", errors="replace")
                if is_prompt_ready(text):
                    break
                # 沒有 prompt 但已穩定一段時間，繼續等
            continue

    return buf.decode("utf-8", errors="replace")


def extract_response(raw: str, user_message: str) -> str:
    """
    從 claude CLI 的原始 PTY 輸出中擷取 AI 回應文字。
    去掉 ANSI、去掉 echo 的輸入、去掉尾端 prompt。
    """
    clean = strip_ansi(raw)

    # 去掉 echo 的 user message（PTY 會把輸入 echo 出來）
    if user_message in clean:
        idx = clean.index(user_message) + len(user_message)
        clean = clean[idx:]

    # 去掉尾端的 prompt 行
    lines = clean.split("\n")
    result_lines = []
    for line in lines:
        stripped = line.strip()
        # 跳過純 prompt 行
        if stripped in (">", "$", "Human:"):
            continue
        # 跳過框線
        if re.match(r"^[╭╰─╮│]+$", stripped):
            continue
        result_lines.append(line)

    return "\n".join(result_lines).strip()


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, ClaudeSession] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    async def get_or_create(self, session_id: str) -> ClaudeSession:
        if session_id in self._sessions:
            sess = self._sessions[session_id]
            # 確認 process 還活著
            try:
                os.kill(sess.pid, 0)
                sess.touch()
                return sess
            except OSError:
                log.warning(f"Session {session_id} process dead, respawning")
                del self._sessions[session_id]

        log.info(f"Starting new Claude session: {session_id}")
        sess = await asyncio.get_event_loop().run_in_executor(
            None, self._spawn_session, session_id
        )
        self._sessions[session_id] = sess
        return sess

    def _spawn_session(self, session_id: str) -> ClaudeSession:
        master_fd, slave_fd = pty.openpty()

        # 設定環境（繼承現有環境，確保 API key 等都在）
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["COLUMNS"] = "200"
        env["LINES"] = "50"

        import subprocess
        proc = subprocess.Popen(
            CLAUDE_CMD,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            env=env,
            preexec_fn=os.setsid,
        )
        os.close(slave_fd)

        sess = ClaudeSession(
            session_id=session_id,
            master_fd=master_fd,
            pid=proc.pid,
        )

        # 等待初始 prompt（Claude 啟動需要幾秒）
        log.info(f"Waiting for Claude to start ({session_id})...")
        read_until_ready(master_fd, timeout=60.0)
        log.info(f"Claude ready ({session_id})")
        return sess

    async def send(self, session_id: str, message: str, timeout: float = 120.0) -> str:
        sess = await self.get_or_create(session_id)
        async with sess.lock:
            sess.touch()
            loop = asyncio.get_event_loop()

            def _do_send():
                # 寫入訊息
                msg_bytes = (message + "\n").encode("utf-8")
                os.write(sess.master_fd, msg_bytes)
                # 讀取回應
                raw = read_until_ready(sess.master_fd, timeout=timeout)
                return extract_response(raw, message)

            response = await loop.run_in_executor(None, _do_send)
            return response

    async def close(self, session_id: str):
        if session_id not in self._sessions:
            return
        sess = self._sessions.pop(session_id)
        try:
            os.kill(sess.pid, signal.SIGTERM)
            os.close(sess.master_fd)
        except OSError:
            pass
        log.info(f"Session closed: {session_id}")

    def list_sessions(self) -> list[dict]:
        now = time.time()
        result = []
        for sid, sess in self._sessions.items():
            result.append({
                "session_id": sid,
                "pid": sess.pid,
                "created_ago_s": int(now - sess.created_at),
                "last_used_ago_s": int(now - sess.last_used),
            })
        return result

    async def cleanup_idle(self, max_idle_seconds: float = 3600.0):
        """清理長時間閒置的 session"""
        now = time.time()
        to_close = [
            sid for sid, sess in self._sessions.items()
            if (now - sess.last_used) > max_idle_seconds
        ]
        for sid in to_close:
            log.info(f"Closing idle session: {sid}")
            await self.close(sid)


# ──────────────────────────────────────────────
# FastAPI
# ──────────────────────────────────────────────

manager = SessionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    manager.set_loop(asyncio.get_event_loop())
    async def idle_cleaner():
        while True:
            await asyncio.sleep(300)
            await manager.cleanup_idle()
    asyncio.create_task(idle_cleaner())
    yield

app = FastAPI(title="claude-proxy", version="1.0.0", lifespan=lifespan)


class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str
    timeout: float = 120.0


class SessionRequest(BaseModel):
    session_id: str





@app.get("/health")
async def health():
    return {"status": "ok", "sessions": len(manager._sessions)}


@app.get("/sessions")
async def list_sessions():
    return {"sessions": manager.list_sessions()}


@app.post("/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")
    try:
        response = await manager.send(req.session_id, req.message, req.timeout)
        return {"session_id": req.session_id, "response": response}
    except Exception as e:
        log.exception(f"Error in /chat for session {req.session_id}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/session")
async def close_session(req: SessionRequest):
    await manager.close(req.session_id)
    return {"status": "closed", "session_id": req.session_id}


# ──────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=LISTEN_HOST,
        port=LISTEN_PORT,
        log_level="info",
    )
