---
name: identity
description: Set and update your identity goals - who you want to become
---

## Instructions

When the user runs /identity, manage their identity statements stored in Notion.

**Identity Page:** https://www.notion.so/Identity-2eb35d23b569808eb1ecc18dc3903100

### 1. Fetch Current Identity

Use the Claude AI Notion MCP to read the Identity page (this tool returns full content):

```
Call: mcp__claude_ai_Notion__notion-fetch
Arguments: { "id": "2eb35d23b569808eb1ecc18dc3903100" }
```

### 2. Display Current Identity (if exists)

```
WHO I'M BECOMING

Health (Mental):      "I am the type of person who..."
Health (Physical):    "I am the type of person who..."
Work:                 "I am the type of person who..."
Love:                 "I am the type of person who..."
Wealth:               "I am the type of person who..."
Relationships:        "I am the type of person who..."
Life / Experience:    "I am the type of person who..."
Social / Connection:  "I am the type of person who..."
```

### 3. Prompt for Updates

Ask: "Which would you like to update? (1-8, category name, or 'all')"

Categories:
1. Health (Mental)
2. Health (Physical)
3. Work
4. Love
5. Wealth
6. Relationships
7. Life / Experience
8. Social / Connection

### 4. Identity Statement Format

Guide the user to write identity statements in James Clear's format:

> "I am someone who [behavior/trait]"
> or
> "I am the type of person who [behavior/trait]"

**Current Statements (for reference):**
- Health (Mental): "I am the type of person who maintains mental calm and clarity."
- Health (Physical): "I am the type of person who moves fast, feels strong, avoids injury, and maintains a physical age 10 years younger than my biological age."
- Work: "I am the type of person who builds with patience and leads with a level head. I am the type of person who masters my craft, applies technology creatively, and shows up authentically in everything I create. I am the type of person who leads calmly when times are turbulent."
- Love: "I am the type of person who shows up reliably, dedicates intentional time to my partner, and is clear on my priorities."
- Wealth: "I am the type of person who creates wealth through revenue and creative selling, building so far ahead that money becomes an afterthought — a tool for shaping my world, not a constraint on it."
- Relationships: "I am the type of person who is reliable, sets aside time for the people who matter, and cultivates deep trust with a few — those who are loyal, kind, creative, and building a better world."
- Life / Experience: "I am the type of person who lives fully — saying yes to once-in-a-lifetime moments, exploring the world, and treating life as an adventure to be seized, not optimized."
- Social / Connection: "I am the type of person who is genuinely open and interested in others — someone who hosts, brings people together, and creates spaces for connection."

### 5. Save Identity to Notion

**Important:** Identity is stored directly on the Notion page as structured content.

Format the page content as:

```
# Identity Statements
Who I am becoming. These drive all prioritization.

## Health (Mental)
> I am the type of person who...

## Health (Physical)
> I am the type of person who...

## Work
> I am the type of person who...

## Love
> I am the type of person who...

## Wealth
> I am the type of person who...

## Relationships
> I am the type of person who...

## Life / Experience
> I am the type of person who...

## Social / Connection
> I am the type of person who...
```

Use `mcp__notion__update_page_content` to save updates:
```
Call: mcp__notion__update_page_content
Arguments: { "page_id": "2eb35d23b569808eb1ecc18dc3903100", "content": "<formatted markdown>" }
```

### 6. First-Time Setup

If no identity exists, walk through all 8 categories:

```
Let's define who you're becoming. For each area, complete:
"I am the type of person who..."

1. HEALTH (MENTAL) — calm, clarity, mental wellbeing:
>

2. HEALTH (PHYSICAL) — strength, energy, longevity:
>

3. WORK — craft, career, contribution:
>

4. LOVE — romantic partnership, showing up for partner:
>

5. WEALTH — money, revenue, financial freedom:
>

6. RELATIONSHIPS — friends, family, trust:
>

7. LIFE / EXPERIENCE — adventure, saying yes, exploration:
>

8. SOCIAL / CONNECTION — hosting, bringing people together:
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

## Identity → Task Tag Mapping

When tagging tasks with `[Identity]`, reference the relevant category:

| Category | Example Tasks |
|----------|---------------|
| Health (Mental) | Meditation, journaling, therapy, digital detox |
| Health (Physical) | Workouts, meal prep, sleep optimization, recovery |
| Work | Deep work, strategic planning, shipping, building |
| Love | Date nights, quality time, partner communication |
| Wealth | Sales calls, invoicing, deal closing, revenue goals |
| Relationships | Family calls, friend catch-ups, maintaining trust |
| Life / Experience | Travel, new experiences, spontaneous adventures |
| Social / Connection | Hosting, intros, community events, bringing people together |
