# Google Calendar MCP Server

MCP server for Mirage to interact with Google Calendar.

## One-Time Setup (5 minutes)

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **Google Calendar API**:
   - Go to APIs & Services > Library
   - Search "Google Calendar API"
   - Click Enable

### 2. Create OAuth Credentials

1. Go to APIs & Services > Credentials
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - User Type: External (or Internal if using Workspace)
   - App name: "Mirage"
   - Add your email as a test user
4. Application type: **Desktop app**
5. Name: "Mirage Calendar"
6. Download the JSON file

### 3. Save Credentials

```bash
mkdir -p ~/.config/mirage
mv ~/Downloads/client_secret_*.json ~/.config/mirage/credentials.json
```

### 4. Install Dependencies

```bash
cd mcp/google-calendar
pip install -r requirements.txt
```

### 5. First Run (Authorize)

```bash
python server.py
```

This will open a browser for one-time authorization. After authorizing, a token is saved at `~/.config/mirage/token.json` and you won't need to authorize again.

## Register with Claude Code

Add to your Claude Code settings (`~/.claude/settings.json` or project `.claude/settings.json`):

```json
{
  "mcpServers": {
    "google-calendar": {
      "command": "python",
      "args": ["/path/to/mirage/mcp/google-calendar/server.py"]
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `get_free_time` | Get available time blocks for a specific date |
| `get_week_overview` | Get busy/free summary for the week |
| `create_event` | Create a new calendar event |
| `list_events` | List events for a date range |

## Example Usage

Once registered, Claude can use these tools:

```
"How much free time do I have today?"
→ Calls get_free_time

"Schedule 'Deep work: API migration' for tomorrow 2-4pm"
→ Calls create_event

"What does my week look like?"
→ Calls get_week_overview
```
