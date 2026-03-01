#!/usr/bin/env python3
"""
claude-proxy — Print-mode Proxy
Forwards messages from OpenClaw to the local claude CLI (--print mode) and returns the response.

HTTP API:
  POST /chat    { "session_id": "...", "message": "...", "timeout": 20 }
  GET  /health  Health check
"""

import json
import os
import subprocess
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

CLAUDE_TIMEOUT_DEFAULT = float(os.getenv("CLAUDE_TIMEOUT_DEFAULT", "20"))

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 8765
CLAUDE_BIN = os.path.expanduser("~/.local/bin/claude")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("claude-proxy")


def run_claude(message: str, timeout: float) -> str:
    env = os.environ.copy()
    env["PATH"] = os.path.expanduser("~/.local/bin") + ":" + env.get("PATH", "")

    cmd = [
        CLAUDE_BIN,
        "--dangerously-skip-permissions",
        "--print",
        "--output-format", "json",
        message,
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Claude CLI timed out after {timeout}s")

    if proc.returncode != 0:
        raise RuntimeError(f"Claude CLI error: {proc.stderr[:500]}")

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Invalid JSON from claude: {proc.stdout[:200]}")

    if data.get("is_error"):
        raise RuntimeError(f"Claude error: {data.get('result', 'unknown error')}")

    return data.get("result", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="claude-proxy", version="3.0.0", lifespan=lifespan)


class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str
    timeout: float = CLAUDE_TIMEOUT_DEFAULT


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")
    import asyncio
    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(None, run_claude, req.message, CLAUDE_TIMEOUT_DEFAULT)
        return {"session_id": req.session_id, "response": response}
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        log.exception("Error in /chat")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host=LISTEN_HOST, port=LISTEN_PORT, log_level="info")
