---
description: Scaffold a new domain — creates a domain file and wires it into the vault index.
---

You are the teams-new skill. Create a domain file: the knowledge layer that makes every agent session in this domain start smarter.

IMPORTANT: This is a generic skill for any user in any project. When you need missing input, print a plain text question and wait for the user to reply. Do NOT use the AskUserQuestion tool. Do not offer selectable options or pre-filled suggestions.

## Inputs

- **domain name** (required): lowercase, hyphenated (e.g., `payments`, `onboarding`). Taken from the user's command arguments.
- **vault path** (optional): resolved automatically (see vault resolution below).

If no domain name was provided, print: "What domain name? (lowercase, hyphenated)" and wait for the user to type it.

## Workflow

1. **Resolve vault path** (check in order, use the first match):
   1. Read `.claude/CLAUDE.md` for a `vault:` line (written by `/teams-deploy`)
   2. Check if `./wiki/` exists in the current directory
   3. Ask the user to type a path
   Do not scan the home directory, environment variables, hooks, or session context for vault locations.

2. **Check existing**: if `{vault}/wiki/domains/{domain}.md` exists, show it and ask "Update or start fresh?"

3. **Create domain file** at `{vault}/wiki/domains/{domain}.md` with this template:

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

4. **Wire to index**: append `- [[{domain}]]` to `{vault}/wiki/index.md` under `## Domains` (create section if missing). Just the wikilink, nothing else.

5. **Report**:

```
Domain **{domain}** created at `wiki/domains/{domain}.md`

This file is empty. Only you can fill it — write the context that isn't in the code:
  - Mission, ownership boundaries, how things actually work
  - What breaks and why, vendor landscape, team knowledge
  - Conventions, stakeholders, current focus

Then run `/teams-deploy {domain}` to wire it into your repos.

Agent pipelines (python-dev, go-dev, etc.) pick up domain context automatically via SessionStart.
```

## Constraints

- Use HTML comments as placeholders, not lorem ipsum
- Never generate fake domain content
- Keep frontmatter flat YAML
- Do NOT create agent stubs or agent files. Agents come from other plugins (e.g. spoton-ai-dev-enablement). This skill only creates the knowledge layer.
- Always check for existing domain before creating

Usage:
- `/teams-new <domain>` — scaffold a domain
