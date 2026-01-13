# Notion MCP Server

MCP server for Mirage to interact with your Notion Production Calendar.

## One-Time Setup (3 minutes)

### 1. Create a Notion Integration

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Name: "Mirage"
4. Select your workspace
5. Click "Submit"
6. Copy the "Internal Integration Token" (starts with `secret_`)

### 2. Share Your Page with the Integration

1. Open your [Production Calendar](https://www.notion.so/Production-Calendar-28535d23b569808c9689fa367f5fc9b5) in Notion
2. Click "..." (three dots) in the top right
3. Click "Add connections"
4. Search for "Mirage" and select it
5. Click "Confirm"

### 3. Save the Token

Option A: Environment variable (recommended)
```bash
export NOTION_TOKEN="secret_xxxxx"
```

Option B: Add to shell profile (~/.zshrc or ~/.bashrc)
```bash
echo 'export NOTION_TOKEN="secret_xxxxx"' >> ~/.zshrc
source ~/.zshrc
```

### 4. Install Dependencies

```bash
cd mcp/notion
pip install -r requirements.txt
```

### 5. Test

```bash
python server.py
```

## Register with Claude Code

Add to your Claude Code settings:

```json
{
  "mcpServers": {
    "notion": {
      "command": "python",
      "args": ["/path/to/mirage/mcp/notion/server.py"],
      "env": {
        "NOTION_TOKEN": "secret_xxxxx"
      }
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `get_production_calendar` | Fetch items from Production Calendar (next 14 days by default) |
| `get_notion_page` | Fetch content from any Notion page by ID |

## Example Usage

```
"What's on my production calendar this week?"
→ Calls get_production_calendar

"Show me the next 30 days of production"
→ Calls get_production_calendar with days_ahead=30
```

## Customization

The Production Calendar ID is hardcoded in `server.py`:
```python
PRODUCTION_CALENDAR_ID = "28535d23b569808c9689fa367f5fc9b5"
```

If you need to change it, update this value with the ID from your Notion database URL.
