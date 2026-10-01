#!/usr/bin/env bash
export AGENT_MAIL_PROJECT='/Users/irako/Developer/mirage'
export AGENT_MAIL_AGENT='YOUR_AGENT_NAME'
export AGENT_MAIL_URL='http://127.0.0.1:8765/api/'
export AGENT_MAIL_TOKEN="${AGENT_MAIL_TOKEN:-}"
export AGENT_MAIL_INTERVAL='120'
exec '/Users/irako/Developer/mirage/.codex/hooks/notify_inbox.sh' "$@"
