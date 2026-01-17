---
name: dump
description: Start a brain dump session to capture everything on your mind
---

## Instructions

When the user runs /dump, start a brain dump session:

### 1. Enter Dump Mode

Tell the user:
> "Brain dump started. Just dump everything on your mind - work, personal, random thoughts. I'll organize it all when you're done. Type /done when finished."

### 2. Capture Everything

- Accept ALL freeform input without judgment or categorization
- Acknowledge briefly after each input: "Got it. What else?"
- Do NOT try to organize, label, or process yet
- Keep all captured items in memory for processing when /done is called

### 3. Keep Going Until /done

Continue accepting input until the user types /done, which triggers the done skill.

## Example Interaction

```
User: /dump

Mirage: Brain dump started. Just dump everything on your mind - work, personal,
random thoughts. I'll organize it all when you're done. Type /done when finished.

User: need to fix the auth bug, also email jake about the contract renewal
should probably schedule that dentist appointment I keep putting off
oh and I had an idea about automating the weekly reports

Mirage: Got it. What else?

User: blocked on the API migration waiting for devops
also need to plan Q1 goals with the team

Mirage: Got it. What else?

User: /done
```

## Key Behaviors

- Be a passive listener during dump mode
- Never interrupt the flow with questions or suggestions
- Save EVERYTHING - even vague thoughts are valuable
- The magic happens in /done, not here
