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

   b. **Check for existing CLAUDE.md**: look for both `{repo}/.claude/CLAUDE.md` and `{repo}/CLAUDE.md`.
      - If `.claude/CLAUDE.md` exists, use that.
      - Else if `CLAUDE.md` exists at repo root, use that.
      - Else create `{repo}/.claude/CLAUDE.md`.

   c. **Check current domain**:
      - Same domain already set: note "already wired" and skip.
      - Different domain: note "switching from {other} to {domain}".
      - No domain line: add it.

   d. **Write domain reference**: add or update `domain: {domain}` at the top of the CLAUDE.md. Preserve all existing content.

   e. **Update .gitignore**: if using `.claude/CLAUDE.md`, ensure it's excluded in `{repo}/.gitignore`. If missing, append it.

5. **Verify Domain Router hook** (once, not per repo): check `~/.claude/settings.json` for a SessionStart hook that reads domain files. Warn if missing.

6. **Report**: print a summary for all repos:

```
Domain **{domain}** deployed:

  {repo1}/.claude/CLAUDE.md   — wired (new)
  {repo2}/CLAUDE.md           — wired (updated, was: {old-domain})
  {repo3}/.claude/CLAUDE.md   — already wired, skipped

Domain Router will load `wiki/domains/{domain}.md` on every SessionStart in these repos.
```

## Constraints

- Never commit `.claude/CLAUDE.md` (local-only)
- Never modify the domain file itself
- Preserve existing CLAUDE.md content (only add/update the `domain:` line)
- If a repo already has a root `CLAUDE.md`, use it instead of creating `.claude/CLAUDE.md`

Usage:
- `/teams-deploy <domain>` — deploy to current repo
- `/teams-deploy <domain> /path/to/repo` — deploy to one repo
- `/teams-deploy <domain> /path/to/repo1 /path/to/repo2` — deploy to multiple repos
