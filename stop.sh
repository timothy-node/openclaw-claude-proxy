#!/usr/bin/env bash
# Stop claude-proxy

if ! pgrep -f "python proxy.py" > /dev/null 2>&1; then
  echo "⚠️  claude-proxy is not running"
  exit 0
fi

echo "🛑 Stopping claude-proxy ..."
pkill -f "python proxy.py"
sleep 1

if pgrep -f "python proxy.py" > /dev/null 2>&1; then
  echo "⚠️  Force killing..."
  pkill -9 -f "python proxy.py"
fi

echo "✅ claude-proxy stopped"
