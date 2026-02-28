#!/usr/bin/env bash
# Start claude-proxy
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PATH="$HOME/.local/bin:$PATH"

if [ ! -f "$SCRIPT_DIR/.env" ]; then
  echo "⚠️  .env not found. Copy the template and fill in your token:"
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
