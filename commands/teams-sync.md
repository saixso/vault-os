---
description: Check what's new in the wiki for your domain, or ratchet learnings into the domain file.
---

You are the teams-sync skill. Two modes: **brief** (what's new, fast read) and **ratchet** (fold learnings into the domain file).

IMPORTANT: When you need missing input, print a plain text question and wait. Do NOT use AskUserQuestion.

## Inputs

- **domain name** (required): taken from command arguments, or read from `.claude/CLAUDE.md` `domain:` line.
- **mode** (optional): `brief` (default) or `ratchet`. Specified as argument or flag.
- **vault path**: resolved automatically from `vault:` line in `.claude/CLAUDE.md`, then `./wiki/`, then ask.

If no domain name was provided and none found in `.claude/CLAUDE.md`, print: "What domain?" and wait.

## Mode: brief (default)

Quick read. No edits. Shows what's new since last sync.

1. **Load domain file**: read `{vault}/wiki/domains/{domain}.md`. Extract `updated:` date.
2. **Find new pages**: glob `{vault}/wiki/**/*.md`, filter to pages where tags/domain/content reference the domain AND `updated:` or `created:` is after the domain file's `updated:` date.
3. **Print digest**:

```
What's new for **{domain}** since {last_sync}:

New:
  + wiki/entities/new-service.md        (entity, 2026-04-20)
  + wiki/concepts/retry-pattern.md      (concept, 2026-04-21)

Updated:
  ~ wiki/entities/auth-service.md       (2026-04-21)

{n} new, {n} updated. Run `/teams-sync {domain} ratchet` to fold these into the domain file.
```

If nothing new: "Wiki is up to date for **{domain}**. Nothing since {last_sync}."

That's it. No edits, no bumping dates. Fast.

## Mode: ratchet

Deliberate curation. Shows digest, then helps you fold learnings into the domain file.

1. **Load domain file**: read `{vault}/wiki/domains/{domain}.md`. Extract `updated:` date and current content.
2. **Find new pages**: same as brief mode.
3. **Categorize**: group into entities, concepts, decisions, insights, updated pages.
4. **Present digest with suggestions**:

```
Wiki changes since {last_sync} for **{domain}**:

New:
  + wiki/entities/new-service.md      (entity, 2026-04-20)
  + wiki/concepts/retry-pattern.md    (concept, 2026-04-21)

Suggestions:
  -> Add [[new-service]] to Vault references
  -> "retry-pattern" may belong in "How things work"
  -> Saved insight reveals a failure mode for "What breaks and why"
```

5. **Apply with approval**: for each suggestion, print it and wait for the user to approve or skip. Append to the relevant section. Never remove existing content.
6. **Bump sync date**: update `updated:` in domain frontmatter to today.
7. **Report**: count of changes, confirmation domain is current.

## Constraints

- Brief mode: read-only. Never edit any file.
- Ratchet mode: never auto-apply. Always show and ask first.
- Never rewrite sections: append only. User's hand-written context is sacred.
- Domain file should stay under ~500 tokens. Warn if growing too large.
- If domain name is in `.claude/CLAUDE.md`, use it without asking.

Usage:
- `/teams-sync` — brief for current domain (reads domain from .claude/CLAUDE.md)
- `/teams-sync <domain>` — brief for named domain
- `/teams-sync ratchet` — ratchet current domain
- `/teams-sync <domain> ratchet` — ratchet named domain
