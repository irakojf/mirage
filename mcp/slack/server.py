"""
Mirage Slack Bot Server

Flask + Slack Bolt server that:
- Message shortcut: Right-click any message → "Capture with Mirage" (works anywhere!)
- /mirage slash command for direct task entry
- @mirage mentions in threads where bot is present
- All responses are ephemeral (only you see them)
"""

import os
import re
import logging

from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

from notion_db import (
    create_task,
    increment_task_mentions
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


def send_ephemeral(client, channel_id: str, user_id: str, text: str, thread_ts: str = None):
    """
    Send an ephemeral message visible only to the specified user.

    Args:
        client: Slack client
        channel_id: Channel to post in
        user_id: User who will see the message
        text: Message content
        thread_ts: Optional thread timestamp to post in thread
    """
    try:
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=text,
            thread_ts=thread_ts
        )
    except Exception as e:
        logger.error(f"Error sending ephemeral message: {e}")


def handle_thread_task(client, thread_messages: list[dict], user_id: str, channel_id: str, thread_ts: str, bot_user_id: str):
    """
    Process a thread and create a task from its context.
    Responds with ephemeral messages (only visible to the triggering user).

    Args:
        client: Slack client for API calls
        thread_messages: All messages in the thread
        user_id: Slack user ID who triggered the capture
        channel_id: Channel where thread exists
        thread_ts: Thread timestamp
        bot_user_id: Bot's user ID for filtering mentions
    """
    if not thread_messages:
        send_ephemeral(client, channel_id, user_id, "Couldn't read the thread. Please try again.", thread_ts)
        return

    # Build thread context (remove @mirage mentions from text)
    thread_context = []
    for msg in thread_messages:
        clean_text = re.sub(rf"<@{bot_user_id}>", "", msg["text"]).strip()
        if clean_text:
            thread_context.append(f"<@{msg['user']}>: {clean_text}")

    if not thread_context:
        send_ephemeral(client, channel_id, user_id, "No content found in thread to capture.", thread_ts)
        return

    full_context = "\n".join(thread_context)
    logger.info(f"Processing thread with {len(thread_messages)} messages")

    try:
        # Process with Claude - pass full thread context
        processed = process_task(full_context, slack_user=user_id, is_thread=True)

        if processed.get("is_duplicate") and processed.get("duplicate_of"):
            # Try to increment existing task
            updated_task = increment_task_mentions(processed["duplicate_of"])
            if updated_task:
                response = format_slack_response(updated_task, is_new=False)
            else:
                # Task ID didn't exist, create new task instead
                task = create_task(
                    content=processed["content"],
                    status=processed["bucket"],  # bucket maps to Notion status
                    estimated_minutes=processed.get("estimated_minutes"),
                    notes=f"Captured from Slack thread by <@{user_id}>",
                    blocked_by=processed.get("blocked_on"),
                    tags=processed.get("tags", [])
                )
                response = format_slack_response(task, is_new=True)
        else:
            # Create new task
            task = create_task(
                content=processed["content"],
                status=processed["bucket"],  # bucket maps to Notion status
                estimated_minutes=processed.get("estimated_minutes"),
                notes=f"Captured from Slack thread by <@{user_id}>",
                blocked_by=processed.get("blocked_on"),
                tags=processed.get("tags", [])
            )
            response = format_slack_response(task, is_new=True)

        send_ephemeral(client, channel_id, user_id, response, thread_ts)

    except Exception as e:
        logger.error(f"Error processing thread task: {e}")
        send_ephemeral(client, channel_id, user_id, f"Failed to capture task: {str(e)}", thread_ts)


@slack_app.command("/mirage")
def handle_slash_command(ack, command, client, context):
    """
    Handle /mirage slash command.

    Completely private - nobody else sees the command or response.
    Use in a thread to capture the conversation as a task.
    """
    ack()  # Acknowledge immediately to avoid timeout

    user_id = command.get("user_id")
    channel_id = command.get("channel_id")
    text = command.get("text", "").strip()

    # Check if we're in a thread (Slack doesn't send thread_ts for slash commands)
    # We need to use the response_url or check if there's text provided

    # If text is provided, treat it as a direct task (no thread needed)
    if text:
        logger.info(f"Processing direct task from /mirage: {text[:50]}...")
        try:
            processed = process_task(text, slack_user=user_id, is_thread=False)

            if processed.get("is_duplicate") and processed.get("duplicate_of"):
                updated_task = increment_task_mentions(processed["duplicate_of"])
                response = format_slack_response(updated_task, is_new=False)
            else:
                task = create_task(
                    content=processed["content"],
                    status=processed["bucket"],  # bucket maps to Notion status
                    estimated_minutes=processed.get("estimated_minutes"),
                    notes=f"Captured from Slack /mirage by <@{user_id}>",
                    blocked_by=processed.get("blocked_on"),
                    tags=processed.get("tags", [])
                )
                response = format_slack_response(task, is_new=True)

            send_ephemeral(client, channel_id, user_id, response)
        except Exception as e:
            logger.error(f"Error processing /mirage task: {e}")
            send_ephemeral(client, channel_id, user_id, f"Failed to capture task: {str(e)}")
        return

    # No text provided - try to capture thread context
    # Unfortunately, slash commands don't have thread_ts, so we need a workaround
    send_ephemeral(
        client, channel_id, user_id,
        "Usage:\n"
        "• `/mirage <task>` - Capture a task directly\n"
        "• `/mirage buy groceries` - Example\n\n"
        "Or right-click any message → 'Capture with Mirage'"
    )


@slack_app.shortcut("capture_with_mirage")
def handle_message_shortcut(ack, shortcut, client):
    """
    Handle "Capture with Mirage" message shortcut.

    Works anywhere - DMs, channels, group chats - even where Mirage isn't a member.
    Right-click any message → "Capture with Mirage"
    """
    ack()  # Acknowledge immediately

    user_id = shortcut.get("user", {}).get("id")
    channel_id = shortcut.get("channel", {}).get("id")
    message = shortcut.get("message", {})
    message_text = message.get("text", "")
    message_ts = message.get("ts")
    thread_ts = message.get("thread_ts")

    # React with eyes to show we're processing
    try:
        if channel_id and message_ts:
            client.reactions_add(channel=channel_id, name="eyes", timestamp=message_ts)
    except Exception as e:
        logger.warning(f"Couldn't add eyes reaction: {e}")

    if not message_text:
        # Try to DM the user since we might not have channel access
        try:
            client.chat_postMessage(
                channel=user_id,
                text="Couldn't read that message. Try copying the text and using `/mirage <text>` instead."
            )
        except Exception:
            pass
        return

    logger.info(f"Processing message shortcut: {message_text[:50]}...")

    # If message is part of a thread, try to fetch full thread context
    full_context = message_text
    is_thread = False

    if thread_ts and channel_id:
        try:
            thread_messages = fetch_thread_messages(client, channel_id, thread_ts)
            if thread_messages:
                # Build thread context
                thread_context = []
                for msg in thread_messages:
                    if msg["text"].strip():
                        thread_context.append(f"<@{msg['user']}>: {msg['text']}")
                if thread_context:
                    full_context = "\n".join(thread_context)
                    is_thread = True
        except Exception as e:
            logger.warning(f"Couldn't fetch thread, using single message: {e}")

    try:
        processed = process_task(full_context, slack_user=user_id, is_thread=is_thread)

        if processed.get("is_duplicate") and processed.get("duplicate_of"):
            updated_task = increment_task_mentions(processed["duplicate_of"])
            if updated_task:
                response = format_slack_response(updated_task, is_new=False)
            else:
                task = create_task(
                    content=processed["content"],
                    status=processed["bucket"],  # bucket maps to Notion status
                    estimated_minutes=processed.get("estimated_minutes"),
                    notes=f"Captured via message shortcut by <@{user_id}>",
                    blocked_by=processed.get("blocked_on"),
                    tags=processed.get("tags", [])
                )
                response = format_slack_response(task, is_new=True)
        else:
            task = create_task(
                content=processed["content"],
                status=processed["bucket"],  # bucket maps to Notion status
                estimated_minutes=processed.get("estimated_minutes"),
                notes=f"Captured via message shortcut by <@{user_id}>",
                blocked_by=processed.get("blocked_on"),
                tags=processed.get("tags", [])
            )
            response = format_slack_response(task, is_new=True)

        # Keep eyes emoji to show it was captured (don't remove it)

        # Always send DM with task details
        try:
            # Get permalink to original message
            permalink = ""
            if channel_id and message_ts:
                try:
                    link_result = client.chat_getPermalink(channel=channel_id, message_ts=message_ts)
                    permalink = link_result.get("permalink", "")
                except Exception as e:
                    logger.warning(f"Couldn't get permalink: {e}")

            # Build message with task and link (let Slack unfurl the link)
            message = f"*{processed['content']}*"
            if permalink:
                message += f"\n{permalink}"

            client.chat_postMessage(
                channel=user_id,
                text=message,
                unfurl_links=True,
                unfurl_media=True
            )
        except Exception as e:
            logger.error(f"DM failed: {e}")

    except Exception as e:
        logger.error(f"Error processing shortcut: {e}")
        try:
            client.chat_postMessage(channel=user_id, text=f"Failed to capture task: {str(e)}")
        except Exception:
            pass


@slack_app.event("app_mention")
def handle_mention(event, context, client):
    """Handle @mirage mentions in threads. Responds privately via ephemeral messages."""
    user_id = event.get("user")
    channel_id = event.get("channel")
    thread_ts = event.get("thread_ts")
    message_ts = event.get("ts")
    bot_user_id = context.get("bot_user_id", "")

    # React with eyes to acknowledge receipt
    try:
        client.reactions_add(channel=channel_id, name="eyes", timestamp=message_ts)
    except Exception as e:
        logger.warning(f"Couldn't add reaction: {e}")

    # Only work in threads
    if not thread_ts:
        send_ephemeral(client, channel_id, user_id, "I only work in threads. Tag me in a thread to capture the conversation as a task.")
        return

    # Fetch all messages in the thread
    thread_messages = fetch_thread_messages(client, channel_id, thread_ts)

    # Process the thread (response sent as ephemeral - only you can see it)
    handle_thread_task(client, thread_messages, user_id, channel_id, thread_ts, bot_user_id)


@slack_app.event("message")
def handle_message(event, context, client):
    """Handle DM messages with @mirage mentions."""
    # Ignore bot messages and message_changed events
    if event.get("subtype") in ["bot_message", "message_changed", "message_deleted"]:
        return

    # Only handle DMs (channel type 'im')
    channel_type = event.get("channel_type")
    if channel_type != "im":
        return

    text = event.get("text", "")
    bot_user_id = context.get("bot_user_id", "")

    # Check if bot was mentioned in the DM
    if f"<@{bot_user_id}>" not in text:
        return

    message_ts = event.get("ts")
    thread_ts = event.get("thread_ts") or message_ts
    channel_id = event.get("channel")
    user_id = event.get("user")

    # React with eyes to acknowledge receipt
    try:
        client.reactions_add(channel=channel_id, name="eyes", timestamp=message_ts)
    except Exception as e:
        logger.warning(f"Couldn't add reaction: {e}")

    # Fetch thread messages (or just this message if not in a thread)
    thread_messages = fetch_thread_messages(client, channel_id, thread_ts)

    # Process the thread (response sent as ephemeral - only you can see it)
    handle_thread_task(client, thread_messages, user_id, channel_id, thread_ts, bot_user_id)


# Flask routes
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle Slack events webhook."""
    return handler.handle(request)


@flask_app.route("/slack/commands", methods=["POST"])
def slack_commands():
    """Handle Slack slash commands."""
    return handler.handle(request)


@flask_app.route("/slack/interactive", methods=["POST"])
def slack_interactive():
    """Handle Slack interactive payloads (shortcuts, modals, etc.)."""
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
