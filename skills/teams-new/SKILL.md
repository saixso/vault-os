---
name: teams-new
description: >
  Scaffold a new domain — creates the domain file and wires it to the vault index.
  The domain file is the knowledge overlay: context that makes every agent session smarter.
  Agents come from other plugins (e.g. spoton-ai-dev-enablement). This skill only creates
  the knowledge layer.
  Triggers on: "teams new", "teams:new", "/teams-new", "create a domain",
  "scaffold a domain", "new domain".
allowed-tools: Read Write Edit Glob Grep Bash
---

# teams-new: Scaffold a Domain

Create the knowledge layer for a domain: a domain file you fill with real context, wired to the vault index.

The domain file is the overlay. Agent pipelines (python-dev, go-dev, etc.) come from other plugins. This skill creates the context they all share.

---

## Inputs

- **domain name** (required): lowercase, hyphenated (e.g., `payments`, `onboarding`)
- **vault path** (optional): resolved automatically (see below)

---

## Workflow

### 1. Resolve the vault path

Check in order:
1. Read `.claude/CLAUDE.md` for a `vault:` line (written by `/teams-deploy`)
2. `./wiki/` in current directory
3. Ask the user

### 2. Check for existing domain

Read `{vault}/wiki/domains/` — if `{domain}.md` already exists, show it and ask: "Domain file exists. Update it or start fresh?"

### 3. Create the domain file

Write `{vault}/wiki/domains/{domain}.md`:

```yaml
---
type: domain
title: "{Domain} Engineering"
status: active
created: {today}
updated: {today}
tags:
  - type/domain
  - {domain}
mcps: []
process_skills: []
discipline_skills: []
delivery:
  merge_strategy: squash
  pre_merge: []
---

# {Domain} Engineering

## Mission
<!-- One sentence: what does this team own? What happens if you fail? -->

## What we own
<!-- The boundaries. What's yours, what's not. Adjacent teams and where the handoff is. -->

## How things work
<!-- The mental model. How data flows. How components connect. The things that aren't obvious from reading the code. -->

## What breaks and why
<!-- Patterns of failure from real incidents. What to check first. The non-obvious rules senior engineers carry in their heads. -->

## Vendors
<!-- External systems, platforms, tools. Who does what. Migration status. -->

## The team
<!-- Who carries what knowledge. Escalation contacts. Tribal knowledge holders. -->

## Conventions
<!-- Rules not written anywhere else. Naming patterns, testing conventions. What never to do. -->

## Stakeholders
<!-- Who depends on this domain. Who do you depend on. -->

## Current context
<!-- What's active right now. Open problems. Recent changes. North star metric if you have one. -->

## Vault — query when needed
<!-- Link wiki pages agents should pull when they need depth. These are NOT loaded at startup. -->
```

### 4. Wire the domain to the vault index

Append `- [[{domain}]]` to `{vault}/wiki/index.md` under `## Domains` (create section if missing). Just the wikilink.

### 5. Report

```
Domain **{domain}** created at `wiki/domains/{domain}.md`

This file is empty. Only you can fill it — write the context that isn't in the code:
  - Mission, ownership boundaries, how things actually work
  - What breaks and why, vendor landscape, team knowledge
  - Conventions, stakeholders, current focus

Then run `/teams-deploy {domain}` to wire it into your repos.

Agent pipelines (python-dev, go-dev, etc.) pick up domain context automatically via SessionStart.
```

---

## Constraints

- Domain file MUST use HTML comments as placeholders, not lorem ipsum
- Never generate fake domain content — the user writes real context
- Keep frontmatter flat YAML (no nesting beyond one level for delivery)
- Do NOT create agent stubs or agent files. Agents come from other plugins. This skill only creates the knowledge layer.
- Always check for existing domain before creating
- Token budget: domain file should stay under ~500 tokens when filled in
