---
description: Wire a domain team into one or more repositories so Claude sessions start with domain context.
---

You are the teams-deploy skill. Wire a domain into repositories so the Domain Router hook loads context on SessionStart.

IMPORTANT: When you need missing input, print a plain text question and wait for the user to reply. Do NOT use the AskUserQuestion tool. Do not offer selectable options or pre-filled suggestions.

## Inputs

- **domain name** (required): must match an existing domain file. Taken from command arguments.
- **repo paths** (optional): one or more repo paths. Can be provided as arguments, or the user can type them when asked. Defaults to current directory if nothing provided.

If no domain name was provided, print: "What domain? (must match a domain file in your vault)" and wait.

## Workflow

1. **Resolve vault** (check in order, use the first match):
   1. Read `.claude/CLAUDE.md` or `CLAUDE.md` in the current project for a `Path:` line pointing to a vault
   2. Check if `./wiki/` exists in the current directory
   3. Ask the user to type a path
   Do not scan the home directory, environment variables, hooks, or session context for vault locations.

2. **Verify domain exists**: check `{vault}/wiki/domains/{domain}.md`. If not found: "Domain '{domain}' not found. Run `/teams-new {domain}` first."

3. **Resolve target repos**: if no repo paths were provided, print:
   "Which repos? You can provide one or more paths, one per line. Or press enter to use the current directory."
   Wait for the user to respond. Accept multiple paths (one per line, comma-separated, or space-separated).

4. **For each repo**, do the following:

   a. **Verify it's a git repo**: `git -C {repo} rev-parse --git-dir`. If not: print "{repo} is not a git repo, skipping." and continue.

   b. **Always use `.claude/CLAUDE.md`** for the domain line. The SessionStart Domain Router hook reads from `.claude/CLAUDE.md`, not root `CLAUDE.md`. Create `{repo}/.claude/` directory if it doesn't exist. If `.claude/CLAUDE.md` already exists, preserve its content. Never write the domain line to root `CLAUDE.md`.

   c. **Check current domain**:
      - Same domain already set: note "already wired" and skip.
      - Different domain: note "switching from {other} to {domain}".
      - No domain line: add it.

   d. **Write domain reference**: add or update `domain: {domain}` at the top of the CLAUDE.md. Preserve all existing content.

   e. **Update .gitignore**: if using `.claude/CLAUDE.md`, ensure it's excluded in `{repo}/.gitignore`. If missing, append it.

5. **Verify Domain Router hook** (once, not per repo): check `~/.claude/settings.json` for a SessionStart hook that reads domain files. Warn if missing.

6. **Load domain context into current session**: read the domain file (`{vault}/wiki/domains/{domain}.md`) and print its contents so the domain context is immediately available. Preface it with:

```
Domain context loaded for this session:
```

7. **Report**: print a summary for all repos:

```
Domain **{domain}** deployed:

  {repo1}/.claude/CLAUDE.md   — wired (new)
  {repo2}/.claude/CLAUDE.md   — wired (updated, was: {old-domain})
  {repo3}/.claude/CLAUDE.md   — already wired, skipped

Domain context is active now. Future sessions will load it automatically via the Domain Router hook.
```

## Constraints

- Never commit `.claude/CLAUDE.md` (local-only)
- Never modify the domain file itself
- Preserve existing CLAUDE.md content (only add/update the `domain:` line)
- Always write the domain line to `.claude/CLAUDE.md`, never to root `CLAUDE.md` (the hook reads `.claude/CLAUDE.md`)

Usage:
- `/teams-deploy <domain>` — deploy to current repo
- `/teams-deploy <domain> /path/to/repo` — deploy to one repo
- `/teams-deploy <domain> /path/to/repo1 /path/to/repo2` — deploy to multiple repos
