# claude-proxy Skill

當使用者的訊息需要轉發給本地 Claude Code CLI 時，使用此 skill。

## 前置條件

- proxy 已啟動（`~/.openclaw/extensions/claude-proxy/start.sh`）
- `.env` 已設定 `CLAUDE_SETUP_TOKEN`

## 使用方式

呼叫本地 proxy HTTP server：

```
POST http://127.0.0.1:8765/chat
Content-Type: application/json

{
  "session_id": "<channel>:<user_id>",
  "message": "<user message>",
  "timeout": 120
}
```

把 `response.response` 回傳給使用者。

## Session ID 規則

- Telegram 直接對話：`telegram:<chat_id>`
- Discord 頻道：`discord:<channel_id>`
- Discord DM：`discord:dm:<user_id>`

## 錯誤處理

- 若 proxy 未啟動（connection refused），提示用戶：
  ```
  cd ~/.openclaw/extensions/claude-proxy && ./start.sh
  ```
- 若 `.env` 缺少 `CLAUDE_SETUP_TOKEN`，提示複製 `.env.example`
- 若超時，回傳部分結果並說明
