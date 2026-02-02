"""
Task processing using Claude Opus API.

Handles:
- Cleaning and formatting task text
- Categorization into buckets (action, project, idea, blocked)
- Priority tag assignment
- Semantic deduplication against existing tasks
- Time estimation for actions
"""

import os
import json
import logging
from typing import Optional
from anthropic import Anthropic

try:
    from mirage_core.services import normalize_task_name as _normalize_task_name
except Exception:  # pragma: no cover - fallback when mirage_core isn't on path
    def _normalize_task_name(raw: str) -> str:
        name = raw.strip()
        for prefix in ("- ", "* ", "• ", "→ "):
            if name.startswith(prefix):
                name = name[len(prefix):]
        return " ".join(name.split())

logger = logging.getLogger(__name__)

from notion_db import get_open_tasks

# Initialize Anthropic client
client = Anthropic()

SYSTEM_PROMPT = """You are Mirage, a task processing agent inspired by James Clear's Atomic Habits.

Your job is to process raw task input from Slack and return structured task data.

## IMPORTANT: User Identity
The user's name is "Ira". When you see messages referring to "Ira" in third person, convert them to first-person tasks for the user:
- "Ira will bring the tripod" → "Bring the tripod"
- "Ira needs to call mom" → "Call mom"
- "Ira - do QUICKBOOKS" → "Do QUICKBOOKS"
- "Tell Ira to send the invoice" → "Send the invoice"

If someone else is responsible (not Ira), keep their name and mark as blocked:
- "Sarah will send the designs" → "Wait for Sarah to send the designs" (blocked on Sarah)

## Core Principles (from Atomic Habits)
1. Identity over outcomes: "Who do you want to become?" drives prioritization
2. 2-minute rule: If it takes <2 min, flag as [DO IT]
3. Never miss twice: Skipped yesterday? It's top priority today
4. Keystone habits: Some actions unlock others — find and prioritize those
5. 1% better: Small compounding actions beat big one-time efforts
6. Systems > Goals: Focus on the process, not just the outcome

## Task Buckets
- action: Single sitting, clear next step
- project: Multi-step, needs breakdown
- idea: Needs more thinking
- blocked: Waiting on someone/something

## Priority Tags
- [DO IT]: ≤2 min, do immediately
- [KEYSTONE]: Unlocks other tasks
- [COMPOUNDS]: 1% improvement, builds over time
- [IDENTITY]: Aligns with identity goals

## Your Response Format
You MUST respond with valid JSON only. No markdown, no explanation, just JSON:

{
  "content": "Clean, actionable task description",
  "bucket": "action|project|idea|blocked",
  "estimated_minutes": 5,  // Only for action bucket, null otherwise
  "tags": ["[DO IT]"],     // Array of applicable tags
  "is_duplicate": false,   // true if semantically same as existing task
  "duplicate_of": null,    // ID of existing task if is_duplicate is true
  "blocked_on": null       // Who/what it's blocked on (for blocked bucket)
}

## Semantic Deduplication
When checking for duplicates, match by MEANING not exact words:
- "call mom" = "phone call with mother" = "ring mum"
- "finish report" = "complete the quarterly report"

Be strict: only mark as duplicate if it's truly the same task."""


THREAD_SYSTEM_PROMPT = """You are Mirage, a task processing agent inspired by James Clear's Atomic Habits.

Your job is to read a Slack thread conversation and extract a single, actionable task that captures the essence of what needs to be done.

## IMPORTANT: User Identity
The user's name is "Ira". When you see messages referring to "Ira" in third person, convert them to first-person tasks for the user:
- "Ira will bring the tripod" → "Bring the tripod"
- "Ira needs to call mom" → "Call mom"
- "Ira - do QUICKBOOKS" → "Do QUICKBOOKS"
- "Tell Ira to send the invoice" → "Send the invoice"

If someone else is responsible (not Ira), keep their name and mark as blocked:
- "Sarah will send the designs" → "Wait for Sarah to send the designs" (blocked on Sarah)

## How to Process Thread Conversations
1. Read the entire conversation to understand the context
2. Identify the core action item or decision that emerged
3. Summarize into ONE clear, actionable task
4. Include relevant context (who, what, when, blockers) in the task description

## Task Buckets
- action: Single sitting, clear next step
- project: Multi-step, needs breakdown
- idea: Needs more thinking
- blocked: Waiting on someone/something (use this if thread shows someone waiting on another person)

## Priority Tags
- [DO IT]: ≤2 min, do immediately
- [KEYSTONE]: Unlocks other tasks
- [COMPOUNDS]: 1% improvement, builds over time
- [IDENTITY]: Aligns with identity goals

## Your Response Format
You MUST respond with valid JSON only. No markdown, no explanation, just JSON:

{
  "content": "Clear task description summarizing the thread outcome",
  "bucket": "action|project|idea|blocked",
  "estimated_minutes": 5,  // Only for action bucket, null otherwise
  "tags": ["[DO IT]"],     // Array of applicable tags
  "is_duplicate": false,   // true if semantically same as existing task
  "duplicate_of": null,    // ID of existing task if is_duplicate is true
  "blocked_on": null       // Who/what it's blocked on (for blocked bucket)
}

## Examples

Thread: "Can we move the meeting to Thursday?" / "Thursday works for me" / "Great, I'll send the invite"
→ content: "Send meeting invite for Thursday"

Thread: "The API is returning 500 errors" / "I checked, it's a database connection issue" / "Sarah is looking into it"
→ content: "Fix database connection causing API 500 errors", bucket: "blocked", blocked_on: "Sarah"

Thread: "Should we use React or Vue for the new dashboard?" / "React has better ecosystem" / "Let's discuss in standup"
→ content: "Decide React vs Vue for dashboard - discuss in standup", bucket: "idea"

## Semantic Deduplication
When checking for duplicates, match by MEANING not exact words.
Be strict: only mark as duplicate if it's truly the same task."""


def process_task(raw_input: str, slack_user: Optional[str] = None, is_thread: bool = False) -> dict:
    """
    Process raw task input using Claude.

    Args:
        raw_input: The raw text from Slack (single message or full thread)
        slack_user: Optional Slack username for context
        is_thread: If True, use thread summarization prompt

    Returns:
        Processed task dict with content, bucket, tags, etc.
    """
    # Get existing tasks for dedup check
    existing_tasks = get_open_tasks()

    # Build context for Claude
    existing_tasks_context = ""
    if existing_tasks:
        task_list = "\n".join(
            f"- [{t['id'][:8]}] {t['content']} (status: {t['status']}, mentions: {t['times_added']})"
            for t in existing_tasks[:50]  # Limit to 50 most recent
        )
        existing_tasks_context = f"\n\n## Existing Open Tasks (check for duplicates)\n{task_list}"

    # Use appropriate prompt based on input type
    if is_thread:
        system_prompt = THREAD_SYSTEM_PROMPT
        user_message = f"""Summarize this Slack thread conversation into a single task:

{raw_input}
{existing_tasks_context}

Remember: Respond with JSON only."""
    else:
        system_prompt = SYSTEM_PROMPT
        user_message = f"""Process this task input from Slack:

"{raw_input}"
{existing_tasks_context}

Remember: Respond with JSON only."""

    # Try Opus first, fall back to Sonnet
    try:
        response = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=500,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
    except Exception as e:
        logger.warning(f"Opus failed, falling back to Sonnet: {e}")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

    # Parse the response
    response_text = response.content[0].text.strip()
    logger.info(f"Claude response: {response_text[:500]}")

    # Try to extract JSON from the response
    try:
        # Handle case where response might have markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            json_lines = []
            in_json = False
            for line in lines:
                if line.startswith("```") and not in_json:
                    in_json = True
                    continue
                if line.startswith("```") and in_json:
                    break
                if in_json:
                    json_lines.append(line)
            response_text = "\n".join(json_lines)

        result = json.loads(response_text)
    except json.JSONDecodeError:
        # Fallback: create basic task
        result = {
            "content": raw_input.strip(),
            "bucket": "action",
            "estimated_minutes": None,
            "tags": [],
            "is_duplicate": False,
            "duplicate_of": None,
            "blocked_on": None
        }

    # Ensure required fields exist
    result.setdefault("content", raw_input.strip())
    result.setdefault("bucket", "action")
    result.setdefault("tags", [])
    result.setdefault("is_duplicate", False)
    result.setdefault("duplicate_of", None)
    result.setdefault("blocked_on", None)

    result["content"] = _normalize_task_name(result["content"])

    # Ensure action tasks have an estimate (default to 5 min if Claude didn't provide)
    if result.get("bucket") == "action" and not result.get("estimated_minutes"):
        result["estimated_minutes"] = 5
        logger.info(f"Defaulting estimated_minutes to 5 for action task: {result['content'][:50]}")
    elif result.get("bucket") != "action":
        result["estimated_minutes"] = None

    return result


BRAIN_DUMP_SYSTEM_PROMPT = """You are Mirage, a task processing agent inspired by James Clear's Atomic Habits.

Your job is to process a brain dump — a raw list of thoughts, tasks, and ideas — and extract structured tasks from it.

## IMPORTANT: User Identity
The user's name is "Ira". When you see messages referring to "Ira" in third person, convert them to first-person tasks for the user:
- "Ira will bring the tripod" → "Bring the tripod"
- "Ira needs to call mom" → "Call mom"

If someone else is responsible (not Ira), keep their name and mark as blocked:
- "Sarah will send the designs" → "Wait for Sarah to send the designs" (blocked on Sarah)

## Core Principles (from Atomic Habits)
1. Identity over outcomes: "Who do you want to become?" drives prioritization
2. 2-minute rule: If it takes <2 min, flag as [DO IT]
3. Keystone habits: Some actions unlock others — find and prioritize those
4. 1% better: Small compounding actions beat big one-time efforts

## Task Buckets
- action: Single sitting, clear next step
- project: Multi-step, needs breakdown
- idea: Needs more thinking
- blocked: Waiting on someone/something

## Priority Tags
- [DO IT]: ≤2 min, do immediately
- [KEYSTONE]: Unlocks other tasks
- [COMPOUNDS]: 1% improvement, builds over time
- [IDENTITY]: Aligns with identity goals

## Your Response Format
You MUST respond with a JSON array of tasks. Each task object has:

[
  {
    "content": "Clean, actionable task description",
    "bucket": "action|project|idea|blocked",
    "estimated_minutes": 5,  // Only for action bucket, null otherwise
    "tags": ["[DO IT]"],     // Array of applicable tags
    "is_duplicate": false,   // true if semantically same as existing task
    "duplicate_of": null,    // ID of existing task if is_duplicate is true
    "blocked_on": null       // Who/what it's blocked on (for blocked bucket)
  }
]

## Guidelines
- Each line of input is typically ONE task (unless they're clearly part of the same thought)
- Combine fragmented thoughts into single coherent tasks
- Clean up grammar and make tasks actionable
- Skip pure commentary or non-task content
- Check against existing tasks for duplicates (match by MEANING not exact words)

Respond with JSON only. No markdown, no explanation."""


def process_brain_dump(raw_input: str, slack_user: Optional[str] = None) -> list[dict]:
    """
    Process a brain dump (multiple raw thoughts/tasks) using Claude.

    Args:
        raw_input: The raw brain dump text (newline-separated messages)
        slack_user: Optional Slack username for context

    Returns:
        List of processed task dicts
    """
    # Get existing tasks for dedup check
    existing_tasks = get_open_tasks()

    # Build context for Claude
    existing_tasks_context = ""
    if existing_tasks:
        task_list = "\n".join(
            f"- [{t['id'][:8]}] {t['content']} (status: {t['status']}, mentions: {t['times_added']})"
            for t in existing_tasks[:50]
        )
        existing_tasks_context = f"\n\n## Existing Open Tasks (check for duplicates)\n{task_list}"

    user_message = f"""Process this brain dump into tasks:

{raw_input}
{existing_tasks_context}

Remember: Respond with a JSON array only."""

    # Try Opus first, fall back to Sonnet
    try:
        response = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=2000,
            system=BRAIN_DUMP_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
    except Exception as e:
        logger.warning(f"Opus failed, falling back to Sonnet: {e}")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=BRAIN_DUMP_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

    # Parse the response
    response_text = response.content[0].text.strip()
    logger.info(f"Claude brain dump response: {response_text[:500]}")

    # Try to extract JSON from the response
    try:
        # Handle case where response might have markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            json_lines = []
            in_json = False
            for line in lines:
                if line.startswith("```") and not in_json:
                    in_json = True
                    continue
                if line.startswith("```") and in_json:
                    break
                if in_json:
                    json_lines.append(line)
            response_text = "\n".join(json_lines)

        results = json.loads(response_text)
        if not isinstance(results, list):
            results = [results]
    except json.JSONDecodeError:
        # Fallback: treat each line as a separate task
        lines = [l.strip() for l in raw_input.split("\n") if l.strip()]
        results = [
            {
                "content": line,
                "bucket": "action",
                "estimated_minutes": 5,
                "tags": [],
                "is_duplicate": False,
                "duplicate_of": None,
                "blocked_on": None
            }
            for line in lines
        ]

    # Ensure required fields exist for each task
    for result in results:
        result.setdefault("content", "")
        result.setdefault("bucket", "action")
        result.setdefault("tags", [])
        result.setdefault("is_duplicate", False)
        result.setdefault("duplicate_of", None)
        result.setdefault("blocked_on", None)

        result["content"] = _normalize_task_name(result["content"])

        # Ensure action tasks have an estimate
        if result.get("bucket") == "action" and not result.get("estimated_minutes"):
            result["estimated_minutes"] = 5
        elif result.get("bucket") != "action":
            result["estimated_minutes"] = None

    return results


CONVERSATION_SYSTEM_PROMPT = """You are Mirage, a personal task coach inspired by James Clear's Atomic Habits.

You're having a direct conversation with Ira via Slack DM. Be direct, supportive, and focused on systems over goals. You're not a generic assistant — you're a thinking partner who helps surface what matters.

## Your Personality
- Direct and concise (this is mobile/Slack, keep responses short)
- Supportive but honest — confront procrastination with curiosity, not judgment
- Focus on ONE actionable recommendation when possible
- Use the user's actual task data to give specific advice

## Core Principles (from Atomic Habits)
1. Identity over outcomes: "Who do you want to become?" drives prioritization
2. 2-minute rule: If it takes <2 min, do it now
3. Never miss twice: Skipped yesterday? It's top priority today
4. Keystone habits: Some actions unlock others — prioritize these
5. 1% better: Small compounding actions beat big one-time efforts

## Coaching Questions (use sparingly, when stuck)
- "What would this look like if it were easy?"
- "Does this activity fill you with energy or drain you?"
- "If someone could only see your actions, what would they say your priorities are?"

## Response Guidelines
- Keep responses under 200 words for mobile readability
- Bold the key recommendation or insight
- If suggesting a task, be specific about which one from their list
- Flag tasks mentioned 3+ times as procrastination patterns
- Consider energy levels (Red/Yellow/Green) when prioritizing

## What You Can Help With
- Prioritization: "What should I focus on today?"
- Overwhelm: "I have too much to do"
- Procrastination: "Why do I keep avoiding X?"
- Planning: "What's most important this week?"
- Quick wins: "What can I knock out quickly?"

Respond conversationally. No JSON needed — just talk to them like a coach would."""


def detect_intent(text: str) -> str:
    """
    Detect whether the user message is a task to capture or a question/conversation.

    Returns: "task", "question", or "greeting"
    """
    text_lower = text.lower().strip()

    # Greeting patterns
    greetings = ["hi", "hello", "hey", "sup", "yo", "good morning", "good afternoon", "good evening"]
    if text_lower in greetings or any(text_lower.startswith(g + " ") for g in greetings):
        return "greeting"

    # Question patterns - things that ask for help/advice
    question_patterns = [
        "what should", "what do", "what can", "what's",
        "help me", "help with",
        "how do", "how should", "how can",
        "which task", "which one",
        "prioritize", "priority", "priorities",
        "focus on", "work on",
        "overwhelmed", "too much", "stressed",
        "procrastinating", "avoiding", "stuck",
        "advice", "suggest", "recommend",
        "show me", "list my", "what's on",
        "?",  # Any question mark
    ]

    if any(pattern in text_lower for pattern in question_patterns):
        return "question"

    # Default: treat as a task to capture
    return "task"


def process_conversation(message: str, slack_user: Optional[str] = None) -> str:
    """
    Process a conversational message and return a helpful response.

    Args:
        message: The user's message
        slack_user: Optional Slack user ID for context

    Returns:
        Conversational response string
    """
    # Get current tasks for context
    existing_tasks = get_open_tasks()

    # Build task context
    tasks_by_status = {
        "Tasks": [],
        "Projects": [],
        "Ideas": [],
        "Blocked": []
    }

    procrastination_flags = []

    for task in existing_tasks:
        status = task.get("status", "Tasks")
        if status in tasks_by_status:
            task_line = f"- {task['content']}"
            if task.get("estimated_minutes"):
                task_line += f" ({task['estimated_minutes']} min)"
            if task.get("times_added", 0) >= 3:
                task_line += f" (mentioned {task['times_added']}x)"
                procrastination_flags.append(task['content'])
            if task.get("blocked_on"):
                task_line += f" [blocked on: {task['blocked_on']}]"
            tasks_by_status[status].append(task_line)

    # Format task context
    task_context = ""
    for status, tasks in tasks_by_status.items():
        if tasks:
            task_context += f"\n*{status}:*\n" + "\n".join(tasks[:10]) + "\n"

    if not task_context:
        task_context = "\n(No open tasks currently)\n"

    # Add procrastination warning if relevant
    procrastination_context = ""
    if procrastination_flags:
        procrastination_context = f"\n*Procrastination patterns detected:* {', '.join(procrastination_flags[:3])}\n"

    user_prompt = f"""Here are Ira's current tasks:
{task_context}
{procrastination_context}
Ira says: "{message}"

Respond as their coach. Keep it short and actionable for mobile."""

    # Call Claude (Sonnet for faster responses on mobile)
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            system=CONVERSATION_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Error in conversation: {e}")
        return f"Sorry, I hit an error: {str(e)}"


def format_slack_response(task: dict, is_new: bool = True) -> str:
    """
    Format a task for Slack response.

    Args:
        task: The task dict
        is_new: Whether this is a new task or a duplicate

    Returns:
        Formatted Slack message string
    """
    if is_new:
        # Format tags
        tags_str = " ".join(task.get("tags", []))

        # Format time estimate
        time_str = ""
        if task.get("estimated_minutes"):
            time_str = f" | {task['estimated_minutes']} min"

        # Use status if available (from Notion), fall back to bucket for compatibility
        status = task.get('status') or task.get('bucket', 'action')
        response = f"""Got it!

"{task['content']}"
{status}{time_str}"""

        if tags_str:
            response += f"\n{tags_str}"

    else:
        # Duplicate task
        times = task.get("times_added", 1)
        response = f"""Already tracking this!

"{task['content']}" (mentioned {times}x)"""

        if times >= 3:
            response += "\nFlagged for procrastination review"

    return response
