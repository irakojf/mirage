# Identity Goals

Set or update identity statements that drive prioritization. Based on James Clear's "identity over outcomes" principle.

## Instructions

1. Query current identity statements:
   ```sql
   SELECT category, statement FROM identity ORDER BY category;
   ```

2. If no identities exist, guide the user through setting them:
   > "Identity drives behavior. Let's define who you want to become in these areas:"

3. Categories to cover:
   - **Love** — Who do you want to be as a partner/in relationships?
   - **Relationships** — Who do you want to be for family/friends?
   - **Work** — What kind of professional do you want to be?
   - **Health** — Who do you want to be physically/mentally?
   - **Wealth** — What's your relationship with money/abundance?

4. For each category, ask:
   > "Complete this: 'I am the type of person who...'"

5. Save identity statements:
   ```sql
   INSERT OR REPLACE INTO identity (category, statement, updated_at)
   VALUES (?, ?, datetime('now'));
   ```

6. If identities already exist, show them and ask:
   > "These are your current identity statements. Want to update any?"

## Usage

When processing tasks, check if they align with identity statements and tag with `[IDENTITY]` if so.

## Persona

This is deep work. Be thoughtful and give space for reflection. These statements matter — they're the north star for all prioritization.
