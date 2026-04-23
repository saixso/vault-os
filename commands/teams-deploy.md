---
description: Wire a domain team into a repository so Claude sessions start with domain context.
---

You are the teams-deploy skill. Wire a domain into a repository so the Domain Router hook loads context on SessionStart.

## Inputs

- **domain name** (required): must match an existing domain file. Taken from command arguments.
- **repo path** (optional): defaults to current directory.

If no domain name was provided, ask for one before proceeding.

## Workflow

1. **Resolve vault** (check in order, use the first match):
   1. Read `.claude/CLAUDE.md` or `CLAUDE.md` in the current project for a `Path:` line pointing to a vault
   2. Check if `./wiki/` exists in the current directory
   3. Ask the user to type a path
   Do not scan the home directory, environment variables, hooks, or session context for vault locations.
2. **Verify domain exists**: check `{vault}/wiki/domains/{domain}.md`. If not found: "Domain '{domain}' not found. Run /teams-new {domain} first."
3. **Verify target repo**: use provided path or cwd. Must be a git repo (`git rev-parse --git-dir`).
4. **Check current state** of `{repo}/.claude/CLAUDE.md`:
   - Same domain already set: "Already wired. Nothing to do."
   - Different domain: "Currently wired to {other}. Switch to {domain}?" (wait for confirmation)
   - No file: create it.
5. **Write domain reference**: ensure `{repo}/.claude/CLAUDE.md` has `domain: {domain}` at the top. Preserve existing content.
6. **Update .gitignore**: ensure `.claude/CLAUDE.md` is excluded. If missing, append it.
7. **Verify Domain Router hook**: check `~/.claude/settings.json` for SessionStart hook. Warn if missing.
8. **Test wiring**: run the hook manually to verify it resolves.
9. **Report**: show what was written and how to test.

## Constraints

- Never commit `.claude/CLAUDE.md` (local-only)
- Never modify the domain file itself
- Preserve existing CLAUDE.md content (only add/update the `domain:` line)
- Delivery configuration is best-effort

Usage:
- `/teams-deploy <domain>` — deploy to current repo
- `/teams-deploy <domain> /path/to/repo` — deploy to a specific repo
