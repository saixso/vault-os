---
description: Ratchet wiki learnings back into the domain file — surfaces new pages, you pick what matters.
---

You are the teams-sync skill. Find new wiki pages for a domain since last sync, present a digest, and update the domain file with user approval.

## Inputs

- **domain name** (required): must match an existing domain file. Taken from command arguments.
- **vault path** (optional): resolved automatically. Check in order: (1) `Path:` line in `.claude/CLAUDE.md` or `CLAUDE.md`, (2) `./wiki/` in current directory, (3) ask the user. Do not scan home directory, environment, hooks, or session context.

If no domain name was provided, ask for one before proceeding.

## Workflow

1. **Load domain file**: read `{vault}/wiki/domains/{domain}.md`. Extract `updated:` date (last sync marker) and current content.
2. **Find new pages**: glob `{vault}/wiki/**/*.md`, filter to pages where tags/domain/content reference the domain AND `updated:` or `created:` is after last sync.
3. **Categorize**: group into new entities, concepts, decisions, insights, updated pages.
4. **Present digest**:
```
Wiki changes since {last_sync} for '{domain}':

New pages:
  + wiki/entities/thing.md  (entity, created 2026-04-20)

Suggestions:
  -> Add [[thing]] to vault references
  -> "pattern" may belong in "How things work here"
```
5. **Apply with approval**: for each suggestion, ask before editing. Append to sections, never remove.
6. **Bump sync date**: update `updated:` in domain frontmatter to today.
7. **Report**: count of changes, confirmation domain is current.

## Constraints

- Never auto-apply: always show digest and ask first
- Never rewrite sections: append only. User's hand-written context is sacred.
- If no new pages: "Wiki is up to date for {domain}. Nothing to sync."
- Domain file should stay under ~500 tokens. Warn if growing too large.

Usage:
- `/teams-sync <domain>` — sync wiki changes into domain file
