"""
Mirage Slack Bot — Minimal intake surface.

Commands:
  /mirage <task text>       — Capture a single task
  /prioritize               — Rank tasks using core priority rules
  /plan                     — Draft a day plan from priorities + estimates
  /review                   — Weekly review snapshot
  Message shortcut           — "Capture with Mirage" (right-click any message)
  @mirage (in thread)       — Capture thread as a task

All responses are ephemeral (only you see them).
No brain dumps, no conversational routing, no heuristic intent detection.
"""

import os
import re
import logging
import asyncio

from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

from task_processor import process_task, format_slack_response

from mirage_core.adapters.notion_repo import NotionTaskRepository
from mirage_core.config import MirageConfig
from mirage_core.ingestion import CaptureRequest, IngestionService
from mirage_core.models import TaskId
from mirage_core.prioritization import prioritize
from mirage_core.review import ReviewService
from mirage_core.ports import ReviewRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

slack_app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)

flask_app = Flask(__name__)
handler = SlackRequestHandler(slack_app)


# ── Helpers ───────────────────────────────────────────────────────────


class _NullReviewRepository(ReviewRepository):
    async def create(self, review):
        return review


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        return asyncio.run(coro)
    if loop.is_running():
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
    return loop.run_until_complete(coro)


def _get_task_repo() -> NotionTaskRepository:
    cfg = MirageConfig.from_env()
    return NotionTaskRepository.from_env(cfg.tasks_database_id)


def _format_priorities(result, limit: int = 5) -> str:
    if not result.suggestions:
        return "No open tasks to prioritize."

    lines = ["Top priorities:"]
    for i, suggestion in enumerate(result.suggestions[:limit], start=1):
        task = suggestion.task
        tags = " ".join(suggestion.tags)
        line = f"{i}) {task.name}"
        if tags:
            line += f" {tags}"
        line += f" — {suggestion.suggested_reason}"
        lines.append(line)
    return "\n".join(lines)


def _minutes_from_hhmm(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def _build_day_plan(result, config: MirageConfig, limit: int = 5) -> str:
    if not result.suggestions:
        return "No open tasks to plan."

    work_minutes = _minutes_from_hhmm(config.work_end) - _minutes_from_hhmm(config.work_start)
    if work_minutes <= 0:
        return "Invalid work hours configuration."

    remaining = work_minutes
    buffer_minutes = max(0, config.buffer_minutes)
    scheduled = []
    unscheduled = []

    for suggestion in result.suggestions:
        task = suggestion.task
        if task.complete_time_minutes is None:
            unscheduled.append(task.name)
            continue

        needed = task.complete_time_minutes
        if scheduled:
            needed += buffer_minutes
        if needed <= remaining:
            scheduled.append((task.name, task.complete_time_minutes))
            remaining -= needed
        if len(scheduled) >= limit:
            break

    lines = [f"Day plan ({work_minutes} min capacity):"]
    if scheduled:
        for i, (name, minutes) in enumerate(scheduled, start=1):
            lines.append(f"{i}) {name} — {minutes} min")
    else:
        lines.append("No estimated tasks fit into the plan.")

    if unscheduled:
        lines.append("Unscheduled (no estimate): " + ", ".join(unscheduled[:5]))

    if remaining >= 0:
        lines.append(f"Remaining: {remaining} min")

    return "\n".join(lines)


def _format_review_snapshot(data) -> str:
    lines = [f"Weekly review snapshot (week of {data.week_start})"]
    lines.append(f"Completed: {data.completed.count}")

    if data.procrastination_list:
        top = data.procrastination_list[:3]
        items = ", ".join(f"{p.task.name} ({p.reason})" for p in top)
        lines.append(f"Procrastination: {items}")

    energy = data.energy
    lines.append(
        f"Energy: green {energy.green}, yellow {energy.yellow}, red {energy.red}, unrated {energy.unrated}"
    )

    if data.stale_decisions:
        lines.append(f"Stale decisions: {len(data.stale_decisions)}")

    return "\n".join(lines)


def send_ephemeral(client, channel_id, user_id, text, thread_ts=None):
    """Send a message visible only to user_id."""
    try:
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=text,
            thread_ts=thread_ts,
        )
    except Exception as e:
        logger.error(f"Error sending ephemeral: {e}")


def fetch_thread_messages(client, channel_id, thread_ts):
    """Return human messages from a thread."""
    try:
        result = client.conversations_replies(
            channel=channel_id, ts=thread_ts, limit=100
        )
        return [
            {"user": m.get("user", "unknown"), "text": m.get("text", ""), "ts": m.get("ts", "")}
            for m in result.get("messages", [])
            if not m.get("bot_id")
        ]
    except Exception as e:
        logger.error(f"Error fetching thread: {e}")
        return []


def capture_and_respond(client, text, user_id, channel_id, thread_ts=None, is_thread=False):
    """Core capture flow shared by all entry points.

    Processes text with Claude, normalises via core CaptureRequest.from_ai_output(),
    then ingests through IngestionService (dedup + persist).
    """
    try:
        processed = process_task(text, slack_user=user_id, is_thread=is_thread)
        repo = _get_task_repo()
        svc = IngestionService(repo)

        # AI flagged a known duplicate by Notion ID — try incrementing first
        if processed.get("is_duplicate") and processed.get("duplicate_of"):
            try:
                new_count = _run_async(
                    repo.increment_mentioned(TaskId(processed["duplicate_of"]))
                )
                response = format_slack_response(
                    {"content": processed["content"], "times_added": new_count},
                    is_new=False,
                )
                send_ephemeral(client, channel_id, user_id, response, thread_ts)
                return processed
            except Exception:
                pass  # ID stale — fall through to normal ingest

        # Normalise AI output → CaptureRequest → IngestionService
        capture_req = CaptureRequest.from_ai_output(processed, source="slack")
        result = _run_async(svc.ingest(capture_req))

        if result.is_duplicate:
            response = format_slack_response(
                {"content": result.task.name,
                 "times_added": result.new_mentioned_count},
                is_new=False,
            )
        else:
            response = format_slack_response(
                {"content": result.task.name,
                 "status": result.task.status.value,
                 "estimated_minutes": result.task.complete_time_minutes,
                 "tags": processed.get("tags", [])},
                is_new=True,
            )

        send_ephemeral(client, channel_id, user_id, response, thread_ts)
        return processed

    except Exception as e:
        logger.error(f"Error in capture_and_respond: {e}")
        send_ephemeral(client, channel_id, user_id, f"Failed to capture task: {e}", thread_ts)
        return None


# ── /mirage slash command ─────────────────────────────────────────────


@slack_app.command("/mirage")
def handle_slash_command(ack, command, client):
    """Capture a task via /mirage <text>."""
    ack()

    user_id = command["user_id"]
    channel_id = command["channel_id"]
    text = command.get("text", "").strip()

    if not text:
        send_ephemeral(
            client,
            channel_id,
            user_id,
            "Usage: `/mirage <task>`\nExample: `/mirage buy groceries`\n\n"
            "Or right-click any message → 'Capture with Mirage'",
        )
        return

    logger.info(f"/mirage from {user_id}: {text[:50]}...")
    capture_and_respond(client, text, user_id, channel_id)


# ── /prioritize slash command ────────────────────────────────────────


@slack_app.command("/prioritize")
def handle_prioritize(ack, command, client):
    """Prioritize tasks via core rules."""
    ack()

    user_id = command["user_id"]
    channel_id = command["channel_id"]

    try:
        repo = _get_task_repo()
        tasks = _run_async(repo.query(exclude_done=True))
        result = prioritize(tasks)
        response = _format_priorities(result)
        send_ephemeral(client, channel_id, user_id, response)
    except Exception as e:
        logger.error(f"/prioritize error: {e}")
        send_ephemeral(client, channel_id, user_id, f"Failed to prioritize: {e}")


# ── /plan slash command ──────────────────────────────────────────────


@slack_app.command("/plan")
def handle_plan(ack, command, client):
    """Create a day plan from priorities + estimates."""
    ack()

    user_id = command["user_id"]
    channel_id = command["channel_id"]

    try:
        repo = _get_task_repo()
        tasks = _run_async(repo.query(exclude_done=True))
        result = prioritize(tasks)
        response = _build_day_plan(result, MirageConfig.from_env())
        send_ephemeral(client, channel_id, user_id, response)
    except Exception as e:
        logger.error(f"/plan error: {e}")
        send_ephemeral(client, channel_id, user_id, f"Failed to plan: {e}")


# ── /review slash command ────────────────────────────────────────────


@slack_app.command("/review")
def handle_review(ack, command, client):
    """Generate a weekly review snapshot."""
    ack()

    user_id = command["user_id"]
    channel_id = command["channel_id"]

    try:
        repo = _get_task_repo()
        svc = ReviewService(repo, _NullReviewRepository())
        data = _run_async(svc.gather_review_data())
        response = _format_review_snapshot(data)
        send_ephemeral(client, channel_id, user_id, response)
    except Exception as e:
        logger.error(f"/review error: {e}")
        send_ephemeral(client, channel_id, user_id, f"Failed to review: {e}")


# ── Message shortcut: "Capture with Mirage" ──────────────────────────


@slack_app.shortcut("capture_with_mirage")
def handle_message_shortcut(ack, shortcut, client):
    """Right-click any message → Capture with Mirage."""
    ack()

    user_id = shortcut.get("user", {}).get("id")
    channel_id = shortcut.get("channel", {}).get("id")
    message = shortcut.get("message", {})
    message_text = message.get("text", "")
    message_ts = message.get("ts")
    thread_ts = message.get("thread_ts")

    # React with eyes to show processing
    try:
        if channel_id and message_ts:
            client.reactions_add(channel=channel_id, name="eyes", timestamp=message_ts)
    except Exception:
        pass

    if not message_text:
        try:
            client.chat_postMessage(
                channel=user_id,
                text="Couldn't read that message. Try `/mirage <text>` instead.",
            )
        except Exception:
            pass
        return

    logger.info(f"Shortcut from {user_id}: {message_text[:50]}...")

    # If in a thread, fetch full context
    full_context = message_text
    is_thread = False
    if thread_ts and channel_id:
        try:
            msgs = fetch_thread_messages(client, channel_id, thread_ts)
            if msgs:
                full_context = "\n".join(
                    f"<@{m['user']}>: {m['text']}" for m in msgs if m["text"].strip()
                )
                is_thread = True
        except Exception as e:
            logger.warning(f"Couldn't fetch thread: {e}")

    processed = capture_and_respond(client, full_context, user_id, channel_id, is_thread=is_thread)

    # Also DM the user with task name + permalink
    if processed:
        try:
            permalink = ""
            if channel_id and message_ts:
                try:
                    link = client.chat_getPermalink(channel=channel_id, message_ts=message_ts)
                    permalink = link.get("permalink", "")
                except Exception:
                    pass
            msg = f"*{processed['content']}*"
            if permalink:
                msg += f"\n{permalink}"
            client.chat_postMessage(
                channel=user_id, text=msg, unfurl_links=True, unfurl_media=True
            )
        except Exception as e:
            logger.error(f"DM failed: {e}")


# ── @mirage in threads ────────────────────────────────────────────────


@slack_app.event("app_mention")
def handle_mention(event, context, client):
    """Handle @mirage mentions in threads."""
    user_id = event.get("user")
    channel_id = event.get("channel")
    thread_ts = event.get("thread_ts")
    message_ts = event.get("ts")
    bot_user_id = context.get("bot_user_id", "")

    try:
        client.reactions_add(channel=channel_id, name="eyes", timestamp=message_ts)
    except Exception:
        pass

    if not thread_ts:
        send_ephemeral(
            client,
            channel_id,
            user_id,
            "Tag me in a thread to capture the conversation as a task.",
        )
        return

    thread_messages = fetch_thread_messages(client, channel_id, thread_ts)
    if not thread_messages:
        send_ephemeral(client, channel_id, user_id, "Couldn't read the thread.", thread_ts)
        return

    # Build thread context, stripping @mirage mentions
    context_lines = []
    for msg in thread_messages:
        clean = re.sub(rf"<@{bot_user_id}>", "", msg["text"]).strip()
        if clean:
            context_lines.append(f"<@{msg['user']}>: {clean}")

    if not context_lines:
        send_ephemeral(client, channel_id, user_id, "No content found in thread.", thread_ts)
        return

    capture_and_respond(
        client, "\n".join(context_lines), user_id, channel_id, thread_ts, is_thread=True
    )


# ── DM handling (simple capture only) ─────────────────────────────────


@slack_app.event("message")
def handle_message(event, context, client):
    """Handle DMs — capture as a task (no conversational routing)."""
    if event.get("subtype") in ["bot_message", "message_changed", "message_deleted"]:
        return
    if event.get("channel_type") != "im":
        return

    text = event.get("text", "").strip()
    user_id = event.get("user")
    channel_id = event.get("channel")
    bot_user_id = context.get("bot_user_id", "")

    clean_text = re.sub(rf"<@{bot_user_id}>", "", text).strip()
    if not clean_text:
        return

    try:
        client.reactions_add(channel=channel_id, name="eyes", timestamp=event.get("ts"))
    except Exception:
        pass

    capture_and_respond(client, clean_text, user_id, channel_id)


# ── Flask routes ──────────────────────────────────────────────────────


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


@flask_app.route("/slack/commands", methods=["POST"])
def slack_commands():
    return handler.handle(request)


@flask_app.route("/slack/interactive", methods=["POST"])
def slack_interactive():
    return handler.handle(request)


@flask_app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200


@flask_app.route("/", methods=["GET"])
def index():
    return {"app": "mirage-slack", "status": "running"}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    flask_app.run(host="0.0.0.0", port=port)
