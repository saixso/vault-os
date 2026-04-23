---
name: teams-deploy
description: >
  Wire a domain team into a repository. Installs the domain reference in CLAUDE.md
  so the Domain Router hook loads context on SessionStart. Optionally configures
  delivery settings (agent-worktree, pre-merge hooks).
  Triggers on: "teams deploy", "teams:deploy", "/teams-deploy", "wire domain",
  "deploy team", "install domain".
allowed-tools: Read Write Edit Glob Grep Bash
---

# teams-deploy: Wire a Domain Into a Repo

Install a domain harness into any repository so that every Claude session starts with domain context automatically.

This skill writes the minimal wiring — the Domain Router hook (already in ~/.claude/settings.json) does the rest at SessionStart.

---

## Inputs

- **domain name** (required): must match an existing domain file in the vault
- **repo path** (optional): defaults to current directory

---

## Workflow

### 1. Verify the domain file exists

Check `{vault}/wiki/domains/{domain}.md` exists. If not:
"Domain '{domain}' not found. Run /teams-new {domain} first."

### 2. Resolve the target repo

Use the provided repo path, or default to the current working directory.
Verify it's a git repo (`git rev-parse --git-dir`).

### 3. Check current state

Read `{repo}/.claude/CLAUDE.md` if it exists. Check if `domain:` is already set.
- If same domain: "Already wired to {domain}. Nothing to do."
- If different domain: "Currently wired to {other}. Switch to {domain}?" — wait for confirmation.
- If no CLAUDE.md: create it.

### 4. Write the domain reference

Ensure `{repo}/.claude/CLAUDE.md` exists and contains:

```markdown
domain: {domain}
```

If the file already has content, prepend the domain line at the top (before any other content). If a `domain:` line already exists, replace it.

### 5. Ensure .gitignore excludes CLAUDE.md

Check `{repo}/.gitignore` for `.claude/CLAUDE.md`. If missing, append:

```
# Domain harness — installed locally, not committed
.claude/CLAUDE.md
```

### 6. Configure delivery (optional)

Read the domain file's `delivery:` frontmatter. If it has settings:

Check if `{repo}/.agent-worktree.toml` exists. If agent-worktree is available:
- Set `merge_strategy` from domain file
- Set `pre_merge` hooks from domain file

If agent-worktree is not installed, skip silently — delivery config is optional.

### 7. Verify the Domain Router hook

Check `~/.claude/settings.json` for the SessionStart hook that reads domain files.
If missing, warn:
"Domain Router hook not found in ~/.claude/settings.json. The domain file won't load automatically. Add the SessionStart hook — see the agent-teams build plan."

### 8. Test the wiring

Run the Domain Router hook manually to verify it resolves:
```bash
domain={domain} && cat {vault}/wiki/domains/$domain.md 2>/dev/null | head -5
```

If it prints the frontmatter, wiring works.

### 9. Report

```
Domain '{domain}' deployed to {repo}:
  .claude/CLAUDE.md   ← domain: {domain}
  .gitignore          ← .claude/CLAUDE.md excluded

Domain Router will load wiki/domains/{domain}.md on every SessionStart.

Test it: open a new Claude session in this repo and ask a domain question.
```

---

## Constraints

- Never commit `.claude/CLAUDE.md` — it's local-only, like node_modules
- Never modify the domain file itself — this skill only wires, doesn't author
- If the repo already has a `.claude/CLAUDE.md` with other content, preserve it — only add/update the `domain:` line
- The Domain Router hook lives in user-level settings, not per-repo — don't duplicate it
- Delivery configuration is best-effort — skip if tools aren't installed
