# claude-proxy

> ⚠️ **Use at your own risk.** This project is provided as-is, without warranty of any kind. The author is not responsible for any damage, data loss, or security issues arising from its use.

## 🤝 Community
  
- 💬 Telegram: https://t.me/timothy_node
- 💬 Youtube : https://youtu.be/arIWurmMKMg

Forwards messages from OpenClaw to the local `claude` CLI (`--print` mode) via HTTP.

```
OpenClaw Agent
├─ proxy not running → respond directly via model
└─ proxy running → POST localhost:8765 → claude CLI → response
```

## Installation

```bash
# Vibe Coding
Install https://github.com/timothy-node/openclaw-claude-proxy
```

```bash
# 1. Clone the repository
git clone https://github.com/timothy-node/openclaw-claude-proxy.git ~/.openclaw/skills/claude-proxy

# 2. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install claude CLI
npm install -g @anthropic-ai/claude-code --prefix ~/.local

# 4. Configure token
cd ~/.openclaw/skills/claude-proxy
cp .env.example .env
# Put your token in: ~/.openclaw/skills/claude-proxy/.env
# CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat...

# Default timeout in seconds for claude CLI calls
CLAUDE_TIMEOUT_DEFAULT=20
```

```bash
# Start claude proxy
cd ~/.openclaw/skills/claude-proxy
./start.sh
```

```bash
# Stop claude proxy
cd ~/.openclaw/skills/claude-proxy
./stop.sh
```

## .env

```
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat...

# Default timeout in seconds for claude CLI calls
CLAUDE_TIMEOUT_DEFAULT=20
```

> `.env` is listed in `.gitignore` and will not be committed.

## HTTP API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Send a message and get a response |
| GET | `/health` | Health check |

### POST /chat

```json
{
  "message": "hello",
  "timeout": $CLAUDE_TIMEOUT_DEFAULT
}
```

Response:
```json
{ "session_id": "...", "response": "..." }
```

## systemd Auto-start (optional)

```bash
cd ~/.openclaw/skills/claude-proxy
cp claude-proxy.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now claude-proxy
```

### Disable systemd Auto-start (optional)

```bash
systemctl --user disable --now claude-proxy
```
