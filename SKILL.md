---
name: claude-proxy
description: "Use for ALL incoming user messages. Check if claude-proxy is running on localhost:8765, then route the message to the proxy (Claude Code CLI) or respond directly via model. Always check proxy health first before replying to anything."
---

# claude-proxy Skill

**For every incoming message: check if the proxy is running before deciding how to respond.**

## Flow

### Step 1: Health check
```bash
curl -s -m 2 http://127.0.0.1:8765/health
```

- **Running** (`{"status":"ok"}`) → go to Step 2
- **Not running** (connection refused) → respond directly via model, no mention of proxy

### Step 2: Forward to proxy

```
POST http://127.0.0.1:8765/chat
Content-Type: application/json

{
  "session_id": "<channel>:<chat_id>",
  "message": "<user message>",
  "timeout": $CLAUDE_TIMEOUT_DEFAULT
}
```

Return `response.response` to the user.

## Error handling

| Case | Action |
|------|--------|
| Proxy not running | Respond directly via model |
| HTTP 504 timeout | Inform user of timeout (increase `CLAUDE_TIMEOUT_DEFAULT` in .env if needed) |
| HTTP 500 | Inform user of error details |
