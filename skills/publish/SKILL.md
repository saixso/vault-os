---
name: publish
description: >
  Commit, version-bump, and push vault-os to main — making changes live on the marketplace.
  Triggers on: "publish", "ship it", "push to main", "/publish".
allowed-tools: Read Edit Bash Glob
---

# publish: Ship vault-os changes to the marketplace

Commit all pending changes to `main`, bump the plugin version, push to origin, and report what went live. Supports undo via safe revert.

---

## Inputs

- **message** (optional): Commit message. Auto-generated from changed files if omitted.
- **subcommand** (optional): `undo` or `status`

## Workflow

### Default: `/publish` or `/publish "message"`

1. **Check branch.** If not on `main`, ask the user whether to merge current branch into main first or switch.
2. **Check for changes.** Run `git status`. If nothing to commit, say so and stop.
3. **Show preview.** List all files that will be committed. Skip any matching `.env*`, `credentials*`, `*.key`, `*.pem`.
4. **Bump version.** Read `.claude-plugin/plugin.json`, increment the patch version (e.g., `2.0.1` → `2.0.2`). Stage the bumped file.
5. **Commit.** Stage all changed/new files (excluding secrets). Commit with the provided message or auto-generate one like `publish: <summary of changes>`.
6. **Push.** `git push origin main`.
7. **Report.** Show: version number, commit hash, file list, and confirm "Live on marketplace."

### Undo: `/publish undo`

1. Show the last commit on `main` (hash, message, files changed).
2. Ask the user to confirm the revert.
3. Run `git revert HEAD --no-edit` — safe revert, preserves history.
4. Push to `origin main`.
5. Report: "Reverted `<hash>`. Marketplace updated to previous state."

### Status: `/publish status`

1. Show uncommitted local changes.
2. Show commits ahead of `origin/main`.
3. Show current plugin version from `plugin.json`.

## Output Format

```
Published vault-os v2.0.3 (abc1234)
  - skills/publish/SKILL.md (new)
  - commands/publish.md (new)
  - .claude-plugin/plugin.json (modified)
Live on marketplace.
```

## Constraints

- Never force-push. Undo uses `git revert`, not `git reset`.
- Never stage files matching `.env*`, `credentials*`, `*.key`, `*.pem`.
- Always show the user what will be committed before committing.
- Always use `--no-pager` with git commands.
- The version bump is always patch-level. For major/minor bumps, the user should edit `plugin.json` manually before publishing.
