# claude-proxy Skill

當使用者的訊息需要轉發給本地 Claude Code CLI 時，使用此 skill。

## 使用方式

呼叫本地 proxy HTTP server：

```
POST http://127.0.0.1:8765/chat
Content-Type: application/json

{
  "session_id": "<channel>:<user_id>",   // 每個頻道/用戶獨立 session
  "message": "<user message>",
  "timeout": 120
}
```

把 response.response 回傳給使用者。

## Session ID 規則

- Telegram 直接對話：`telegram:<chat_id>`
- Discord 頻道：`discord:<channel_id>`
- Discord DM：`discord:dm:<user_id>`

## 錯誤處理

- 若 proxy 未啟動（connection refused），提示用戶執行：
  `cd ~/.openclaw/workspace/claude-proxy && ~/.local/bin/uv run python proxy.py`
- 若超時，回傳部分結果並說明
