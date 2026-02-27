# claude-proxy

**本地 PTY Proxy：Telegram/Discord → OpenClaw → Claude Code CLI**

沒有第三方伺服器。訊息走 Telegram/Discord 進來，OpenClaw 接收，
透過 HTTP localhost 轉給本機的 `claude` CLI（跑在 PTY 裡），
拿到回應後再送回給你。

```
你 (Telegram/Discord)
        ↕
   OpenClaw Agent
        ↕  HTTP localhost:8765
  claude-proxy (proxy.py)
        ↕  PTY (偽終端)
   claude CLI
   ├── tool use ✓
   ├── file editing ✓
   ├── git 整合 ✓
   └── 完整對話記憶 ✓
```

## 安裝

```bash
# 1. 安裝 uv（如果還沒有）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 安裝 Node.js（claude CLI 需要）
# 已有就跳過

# 3. 確認 ANTHROPIC_API_KEY 在環境中
export ANTHROPIC_API_KEY=sk-ant-...

# 4. 啟動 proxy
cd ~/.openclaw/workspace/claude-proxy
./start.sh
```

## 測試

```bash
# 健康檢查
curl http://127.0.0.1:8765/health

# 發送訊息
python client.py "你好，幫我列出當前目錄的檔案"

# 指定 session（同 session 保有對話記憶）
python client.py "剛才我說什麼？" my-session
```

## systemd 自動啟動（選用）

```bash
# 安裝 service
cp claude-proxy.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now claude-proxy

# 查看 log
journalctl --user -u claude-proxy -f
```

## HTTP API

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/chat` | 發送訊息，取得回應 |
| GET | `/sessions` | 列出現有 session |
| DELETE | `/session` | 關閉指定 session |
| GET | `/health` | 健康檢查 |

### POST /chat

```json
{
  "session_id": "telegram:123456789",
  "message": "幫我寫一個 hello world",
  "timeout": 120
}
```

## Session 設計

每個 `session_id` 對應一個獨立的 `claude` CLI process（跑在 PTY 裡）。
同一個 session 保有完整的對話歷史，和直接在終端機用 claude 一樣。

建議的 session_id 命名：
- Telegram DM：`telegram:<chat_id>`
- Discord 頻道：`discord:<channel_id>`

閒置超過 1 小時自動關閉（可在 `proxy.py` 調整）。

## 注意事項

- claude CLI 的工作目錄預設是啟動 proxy 時的目錄
- 若要讓 claude 操作特定專案，可在 `/chat` 前先發 `cd /path/to/project` 訊息
- PTY 的 prompt 偵測靠啟發式方法，若回應被截斷可調高 `timeout`
