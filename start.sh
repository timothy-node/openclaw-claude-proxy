#!/usr/bin/env bash
# claude-proxy 啟動腳本
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 確保 uv 在 PATH
export PATH="$HOME/.local/bin:$PATH"

# .env 由 proxy.py 自動載入（python-dotenv）
# 確認 .env 存在
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  echo "⚠️  找不到 .env，請複製範本並填入 token："
  echo "   cp $SCRIPT_DIR/.env.example $SCRIPT_DIR/.env"
  exit 1
fi

echo "🚀 Starting claude-proxy on 127.0.0.1:8765 ..."
exec uv run --no-project \
  --with fastapi \
  --with "uvicorn[standard]" \
  --with pydantic \
  --with python-dotenv \
  python proxy.py
