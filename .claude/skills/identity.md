---
name: identity
description: Set and update your identity goals - who you want to become
---

## Instructions

When the user runs /identity, manage their identity statements stored in Notion.

**Identity Page:** https://www.notion.so/Identity-2eb35d23b569808eb1ecc18dc3903100

### 1. Fetch Current Identity

Use the Notion MCP to read the Identity page:

```
Call: mcp__notion__get_notion_page
Arguments: { "page_id": "2eb35d23b569808eb1ecc18dc3903100" }
```

### 2. Display Current Identity (if exists)

```
WHO I'M BECOMING

Love:          "I am someone who..."
Relationships: "I am someone who..."
Work:          "I am someone who..."
Health:        "I am someone who..."
Wealth:        "I am someone who..."
```

### 3. Prompt for Updates

Ask: "Which would you like to update? (love / relationships / work / health / wealth / all)"

### 4. Identity Statement Format

Guide the user to write identity statements in James Clear's format:

> "I am someone who [behavior/trait]"
> or
> "I am the type of person who [behavior/trait]"

**Examples:**
- Love: "I am someone who shows up fully present for my partner"
- Relationships: "I am the type of person who reaches out first"
- Work: "I am someone who ships consistently, not perfectly"
- Health: "I am someone who never misses a workout twice"
- Wealth: "I am the type of person who pays themselves first"

### 5. Save Identity to Notion

**Important:** Identity is stored directly on the Notion page as structured content.

Format the page content as:

```
## Love
I am someone who...

## Relationships
I am someone who...

## Work
I am someone who...

## Health
I am someone who...

## Wealth
I am someone who...
```

Tell the user to update the Notion page directly, or use the Notion API to update page blocks if available.

### 6. First-Time Setup

If no identity exists, walk through all 5 categories:

```
Let's define who you're becoming. For each area, complete:
"I am someone who..." or "I am the type of person who..."

LOVE (romantic partnership, self-love):
>

RELATIONSHIPS (friends, family, community):
>

WORK (career, craft, contribution):
>

HEALTH (physical, mental, energy):
>

WEALTH (money, assets, financial freedom):
>
```

### 7. Integration with Task Prioritization

After updating, remind the user:
> "Got it. I'll use these to tag tasks that align with your identity as [IDENTITY] priority."

The `/done` skill references these statements when inferring the `[IDENTITY]` tag.

## Key Behaviors

- **Keep it simple**: One statement per category
- **Use James Clear's format**: "I am someone who..." / "I am the type of person who..."
- **Allow partial updates**: User can update just one category
- **Notion is the source of truth**: All identity data lives in the Notion page
- **Connect to tasks**: Make it clear this influences prioritization
