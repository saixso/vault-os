---
description: Commit, version-bump, and push vault-os changes live to the marketplace.
---

Read the `publish` skill. Then run the workflow.

Usage:
- `/publish` — stage, bump version, commit, push to main
- `/publish "feat: add new skill"` — with a custom commit message
- `/publish undo` — revert the last publish (safe revert, not force-push)
- `/publish status` — show unpublished changes and current version
