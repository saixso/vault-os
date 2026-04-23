---
name: teams-sync
description: >
  Ratchet wiki learnings back into the domain file. Surfaces new wiki pages
  tagged with the domain since the last sync, lets you pick what matters,
  and updates the domain file with fresh context.
  Triggers on: "teams sync", "teams:sync", "/teams-sync", "sync domain",
  "update domain", "ratchet domain".
allowed-tools: Read Write Edit Glob Grep
---

# teams-sync: Ratchet Wiki Learnings Into the Domain File

The wiki compounds through daily work — /save, /wiki-ingest, manual edits. But the domain file stays static unless you update it. This skill closes the loop: it reads what's new in the wiki for your domain and helps you fold it into the domain file.

The domain file is the 500-token mental model. This skill keeps it current.

---

## Inputs

- **domain name** (required): must match an existing domain file
- **vault path** (optional): check if `./wiki/` exists in the current directory. If yes, use it. If no, ask the user to provide a path. Do not infer vault locations from environment, hooks, or session context.

---

## Workflow

### 1. Load the domain file

Read `{vault}/wiki/domains/{domain}.md`. Extract:
- `updated:` date from frontmatter (this is the "last sync" marker)
- Current content of each section
- Current `## Vault — query when needed` links

### 2. Find what's new

Search the wiki for pages that are relevant to this domain:

```
Glob: {vault}/wiki/**/*.md
```

Filter to pages where:
- `tags:` contains the domain name, OR
- `domain:` frontmatter matches, OR
- Filename or content references known domain entities

Then filter to pages where `updated:` or `created:` is after the domain file's `updated:` date.

### 3. Categorize the new pages

Group them:

| Category | What it means for the domain file |
|----------|----------------------------------|
| New entities | May need a link in "Vault — query when needed" |
| New concepts | May reveal a pattern worth adding to "How things work" |
| New decisions | May change "Conventions" or "Current context" |
| Saved insights | May surface a failure mode for "What breaks and why" |
| Updated pages | Existing knowledge got deeper — check if domain file is stale |

### 4. Present the digest

Show the user a summary:

```
Wiki changes since {last_sync_date} for domain '{domain}':

New pages:
  + wiki/entities/new-service.md      (entity, created 2026-04-20)
  + wiki/concepts/retry-pattern.md    (concept, created 2026-04-21)
  + wiki/questions/why-dedup-fails.md (insight, saved 2026-04-22)

Updated pages:
  ~ wiki/entities/auth-service.md     (updated 2026-04-21)

Suggestions:
  → Add [[new-service]] to vault references
  → "retry-pattern" may belong in "How things work here"
  → "why-dedup-fails" reveals a failure mode for "What breaks and why"
```

### 5. Apply updates (with user approval)

For each suggestion, ask: "Add this to the domain file?"

Then make the edits:
- Add new wikilinks to `## Vault — query when needed`
- Append one-liners to the relevant section (conventions, failure modes, etc.)
- Never remove existing content — only append or update

### 6. Bump the sync date

Update the domain file's `updated:` frontmatter to today's date.

### 7. Report

```
Domain '{domain}' synced:
  {n} new references added
  {n} sections updated
  updated: {today}

The domain file is current. Next session will load the latest context.
```

---

## Constraints

- Never auto-apply changes — always show the digest and ask before editing
- Never rewrite sections — append to them. The user's hand-written context is sacred.
- Keep suggestions actionable: "add X to Y section" not "consider updating"
- If no new pages found, say: "Wiki is up to date for {domain}. Nothing to sync."
- Domain file must stay under ~500 tokens after updates — warn if it's growing too large
- The `updated:` date in frontmatter is the sync marker — always bump it
