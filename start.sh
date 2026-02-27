#!/usr/bin/env bash
# claude-proxy 啟動腳本
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 確保 uv 在 PATH
export PATH="$HOME/.local/bin:$PATH"

# 確保有 ANTHROPIC_API_KEY（從 OpenClaw 環境繼承或自行設定）
if [ -z "$ANTHROPIC_API_KEY" ]; then
  # 嘗試從 OpenClaw config 讀取
  OC_KEY=$(openclaw config get anthropic.apiKey 2>/dev/null || true)
  if [ -n "$OC_KEY" ]; then
    export ANTHROPIC_API_KEY="$OC_KEY"
  else
    echo "⚠️  警告：ANTHROPIC_API_KEY 未設定，Claude Code 可能無法啟動"
  fi
fi

echo "🚀 Starting claude-proxy on 127.0.0.1:8765 ..."
exec uv run python proxy.py
