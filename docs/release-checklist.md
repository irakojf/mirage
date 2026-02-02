# Release Checklist

Pre-deploy checks and rollback steps for the Mirage Slack bot on fly.io.

## Pre-Deploy

- [ ] All tests pass: `python -m pytest`
- [ ] Lint clean: `ruff check mirage_core mcp tests`
- [ ] Format clean: `ruff format --check mirage_core mcp tests`
- [ ] Schema validation: `python schema/validate.py --dry-run && python schema/validate.py --check-enums`
- [ ] No secrets in staged files: check `.env`, credentials, tokens
- [ ] Changes committed to `main`

## Deploy (Slack Bot)

```bash
cd mcp/slack
fly deploy
fly status        # verify machine is running
fly logs          # watch for startup errors
```

## Post-Deploy Verification

- [ ] `/mirage test task` — creates a task in Notion
- [ ] `/prioritize` — returns ranked list
- [ ] `/plan` — returns day plan
- [ ] `/review` — returns review snapshot
- [ ] Health check: `curl https://mirage-slack.fly.dev/health`

## Rollback

```bash
# List recent deployments
fly releases

# Roll back to previous release
fly deploy --image <previous-image-ref>

# Or scale down if broken
fly scale count 0
```

## Secrets Rotation

When rotating secrets, update fly.io and verify:

```bash
fly secrets set SLACK_BOT_TOKEN=xoxb-new-token
fly secrets set SLACK_SIGNING_SECRET=new-secret
fly secrets set ANTHROPIC_API_KEY=sk-ant-new-key
fly secrets set NOTION_TOKEN=secret_new-token

# Restart to pick up new secrets
fly apps restart
```
