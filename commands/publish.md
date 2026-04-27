---
description: Commit, version-bump, and push vault-os changes live to the marketplace.
---

You are the publish skill. Commit, bump version, and push vault-os to main.

## Inputs

- **commit message** (optional): custom message. If not provided, auto-generate from staged changes.
- **subcommand** (optional): `status` (show unpublished changes), `undo` (revert last publish)

## Workflow

### Default: `/publish` or `/publish "message"`
1. Run `git status` and `git diff --stat` to show what changed
2. Read `.claude-plugin/plugin.json`, extract current version
3. Bump patch version (e.g., 2.0.1 -> 2.0.2)
4. Update version in `plugin.json`
5. Stage all changes, commit with message (or auto-generated)
6. Push to main
7. Report: version, commit hash, what was published

### `/publish status`
Show `git status`, current version, and unpublished changes since last tag/push.

### `/publish undo`
`git revert HEAD` (safe revert, not force-push). Report the revert commit.

## Constraints

- Only run from the vault-os repo root
- Never force-push
- Always show what will be committed before committing
- Ask for confirmation before pushing

Usage:
- `/publish` — auto-message publish
- `/publish "feat: new skill"` — custom message
- `/publish status` — check what's unpublished
- `/publish undo` — safe revert
