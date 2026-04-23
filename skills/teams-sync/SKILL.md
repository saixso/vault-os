---
name: teams-sync
description: >
  Check what's new in the wiki for your domain (brief mode), or fold learnings
  into the domain file (ratchet mode). Brief is default and fast. Ratchet is
  deliberate curation.
  Triggers on: "teams sync", "teams:sync", "/teams-sync", "sync domain",
  "what's new", "domain update", "ratchet domain".
allowed-tools: Read Write Edit Glob Grep
---

# teams-sync: Domain Briefing & Ratchet

Two modes:
- **brief** (default): what's new in the wiki for this domain? Read-only, fast.
- **ratchet**: fold new wiki learnings into the domain file. Deliberate, with approval.

---

## Inputs

- **domain name** (required): must match an existing domain file. Read from `.claude/CLAUDE.md` `domain:` line if available.
- **mode** (optional): `brief` (default) or `ratchet`
- **vault path**: resolved from `vault:` in `.claude/CLAUDE.md`, then `./wiki/`, then ask.

---

## Mode: brief (default)

Quick read. No edits.

### 1. Load the domain file
Read `{vault}/wiki/domains/{domain}.md`. Extract `updated:` date.

### 2. Find what's new
Glob `{vault}/wiki/**/*.md`. Filter to pages where:
- `tags:` contains the domain name, OR
- `domain:` frontmatter matches, OR
- Content references known domain entities

AND `updated:` or `created:` is after the domain file's `updated:` date.

### 3. Print digest
Show new and updated pages. End with: "Run `/teams-sync {domain} ratchet` to fold these into the domain file."

If nothing new: "Wiki is up to date for **{domain}**."

No edits. No date bumps. Fast.

---

## Mode: ratchet

Deliberate curation with user approval.

### 1. Load the domain file
Read `{vault}/wiki/domains/{domain}.md`. Extract `updated:` date and current section content.

### 2. Find what's new
Same as brief mode.

### 3. Categorize
Group by: new entities, concepts, decisions, insights, updated pages.

### 4. Present digest with suggestions
For each new page, suggest where it fits in the domain file:
- New entity → "Vault — query when needed" section
- New concept → "How things work" section
- New insight/failure → "What breaks and why" section
- New convention → "Conventions" section

### 5. Apply with approval
For each suggestion, ask before editing. Append to the relevant section. Never remove existing content.

### 6. Bump sync date
Update `updated:` in domain frontmatter to today.

### 7. Report
Count of changes. Confirmation domain is current.

---

## Constraints

- Brief mode: read-only. Never edit any file.
- Ratchet mode: never auto-apply. Always ask first.
- Never rewrite sections: append only. User's hand-written context is sacred.
- Domain file should stay under ~500 tokens. Warn if growing too large.
- The `updated:` date in frontmatter is the sync marker. Only ratchet bumps it.
