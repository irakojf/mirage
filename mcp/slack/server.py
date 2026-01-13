"""
Mirage Slack Bot Server

Flask + Slack Bolt server that:
- Listens for @mirage mentions in channels
- Listens for DMs to the bot
- Processes tasks using Claude Opus
- Saves to Turso database
- Responds in Slack with confirmation
"""

import os
import re
import logging

from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

from db import (
    create_task,
    increment_task_mentions,
    create_dump_session,
    link_task_to_session
)
from task_processor import process_task, format_slack_response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Slack Bolt app
slack_app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Initialize Flask app
flask_app = Flask(__name__)
handler = SlackRequestHandler(slack_app)


def fetch_thread_messages(client, channel_id: str, thread_ts: str) -> list[dict]:
    """
    Fetch all messages in a thread.

    Returns list of messages with user and text.
    """
    try:
        result = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=100
        )
        messages = []
        for msg in result.get("messages", []):
            # Skip bot messages
            if msg.get("bot_id"):
                continue
            messages.append({
                "user": msg.get("user", "unknown"),
                "text": msg.get("text", ""),
                "ts": msg.get("ts", "")
            })
        return messages
    except Exception as e:
        logger.error(f"Error fetching thread: {e}")
        return []


def handle_thread_task(thread_messages: list[dict], user_id: str, channel_id: str, thread_ts: str, say, bot_user_id: str):
    """
    Process a thread and create a task from its context.

    Args:
        thread_messages: All messages in the thread
        user_id: Slack user ID who triggered the capture
        channel_id: Channel where thread exists
        thread_ts: Thread timestamp
        say: Slack say function for responding
        bot_user_id: Bot's user ID for filtering mentions
    """
    if not thread_messages:
        say("Couldn't read the thread. Please try again.", thread_ts=thread_ts)
        return

    # Build thread context (remove @mirage mentions from text)
    thread_context = []
    for msg in thread_messages:
        clean_text = re.sub(rf"<@{bot_user_id}>", "", msg["text"]).strip()
        if clean_text:
            thread_context.append(f"<@{msg['user']}>: {clean_text}")

    if not thread_context:
        say("No content found in thread to capture.", thread_ts=thread_ts)
        return

    full_context = "\n".join(thread_context)
    logger.info(f"Processing thread with {len(thread_messages)} messages")

    try:
        # Process with Claude - pass full thread context
        processed = process_task(full_context, slack_user=user_id, is_thread=True)

        # Create dump session for tracking
        session_id = create_dump_session(f"Slack thread: {full_context[:200]}")

        if processed.get("is_duplicate") and processed.get("duplicate_of"):
            # Increment existing task
            updated_task = increment_task_mentions(processed["duplicate_of"])
            link_task_to_session(processed["duplicate_of"], session_id)

            response = format_slack_response(updated_task, is_new=False)
        else:
            # Create new task
            task = create_task(
                content=processed["content"],
                bucket=processed["bucket"],
                estimated_minutes=processed.get("estimated_minutes"),
                notes=f"Captured from Slack thread by <@{user_id}>"
            )
            link_task_to_session(task["id"], session_id)

            # Add processed data for response formatting
            task["tags"] = processed.get("tags", [])
            response = format_slack_response(task, is_new=True)

        say(response, thread_ts=thread_ts)

    except Exception as e:
        logger.error(f"Error processing thread task: {e}")
        say(f"Failed to capture task: {str(e)}", thread_ts=thread_ts)


@slack_app.event("app_mention")
def handle_mention(event, say, context):
    """Handle @mirage mentions in threads only."""
    user_id = event.get("user")
    channel_id = event.get("channel")
    thread_ts = event.get("thread_ts")
    bot_user_id = context.get("bot_user_id", "")

    # Only work in threads
    if not thread_ts:
        say("I only work in threads. Tag me in a thread to capture the conversation as a task.")
        return

    # Fetch all messages in the thread
    thread_messages = fetch_thread_messages(slack_app.client, channel_id, thread_ts)

    # Process the thread
    handle_thread_task(thread_messages, user_id, channel_id, thread_ts, say, bot_user_id)


@slack_app.event("message")
def handle_dm(event, say, context):
    """Handle direct messages - only in threads."""
    # Ignore bot messages and message_changed events
    if event.get("subtype") in ["bot_message", "message_changed", "message_deleted"]:
        return

    # Only handle DMs (channel type 'im')
    channel_type = event.get("channel_type")
    if channel_type != "im":
        return

    thread_ts = event.get("thread_ts")
    channel_id = event.get("channel")
    user_id = event.get("user")
    bot_user_id = context.get("bot_user_id", "")

    # Only work in threads
    if not thread_ts:
        say("I only work in threads. Reply to a message to start a thread, then send your task there.")
        return

    # Fetch all messages in the thread
    thread_messages = fetch_thread_messages(slack_app.client, channel_id, thread_ts)

    # Process the thread
    handle_thread_task(thread_messages, user_id, channel_id, thread_ts, say, bot_user_id)


# Flask routes
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle Slack events webhook."""
    return handler.handle(request)


@flask_app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for fly.io."""
    return {"status": "ok"}, 200


@flask_app.route("/", methods=["GET"])
def index():
    """Root endpoint."""
    return {"app": "mirage-slack", "status": "running"}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    flask_app.run(host="0.0.0.0", port=port)
