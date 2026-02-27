#!/usr/bin/env bash
# claude-proxy 停止腳本

PID=$(lsof -ti tcp:8765 2>/dev/null)

if [ -z "$PID" ]; then
  echo "⚠️  claude-proxy 未在執行（port 8765 無程序）"
  exit 0
fi

echo "🛑 停止 claude-proxy (PID: $PID) ..."
kill "$PID"
sleep 1

if kill -0 "$PID" 2>/dev/null; then
  echo "⚠️  強制終止..."
  kill -9 "$PID"
fi

echo "✅ claude-proxy 已停止"
