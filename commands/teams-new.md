---
description: Scaffold a new domain team — creates domain file, agent stubs, and vault wiring.
---

You are the teams-new skill. Scaffold a domain team: a domain file, agent stubs, and vault wiring.

IMPORTANT: This is a generic skill for any user in any project. When you need missing input (domain name, vault path, agent roles), print a plain text question and wait for the user to reply. Do NOT use the AskUserQuestion tool for these inputs. Do not offer selectable options or pre-filled suggestions. Just ask in plain text and let the user type their answer.

## Inputs

- **domain name** (required): lowercase, hyphenated (e.g., `payments`, `onboarding`). Taken from the user's command arguments.
- **vault path** (optional): resolved automatically (see vault resolution below).
- **agents** (optional): agent roles to scaffold. If not provided, print: "What agent roles? (comma-separated, e.g. python-engineer, devops-engineer)" and wait for the user to type them.

If no domain name was provided, print: "What domain name? (lowercase, hyphenated)" and wait for the user to type it.

## Workflow

1. **Resolve vault path** (check in order, use the first match):
   1. Read `.claude/CLAUDE.md` or `CLAUDE.md` in the current project for a `Path:` line pointing to a vault (written by `/wiki` or `/teams-deploy`)
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
agents:
  - {domain}-{agent1}
  - {domain}-{agent2}
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

4. **Create agent stubs** for each role at `{vault}/wiki/agents/{domain}-{role}.md`:

```yaml
---
type: entity
title: "{domain}-{role}"
status: seed
created: {today}
updated: {today}
tags:
  - type/entity
  - agent
  - {domain}
domain: {domain}
---

# {domain}-{role}

## Role
<!-- What this agent specializes in -->

## Knowledge
<!-- Domain-specific patterns, tools, conventions -->

## Tools & MCPs
<!-- MCP servers and tools this agent needs -->

## Constraints
<!-- Scope limits. What this agent must NOT do. -->
```

5. **Wire to index**: append to `{vault}/wiki/index.md` under `## Domains` (create section if missing)
6. **Report**: print this (fill in the domain name and agent count):

```
Your **{domain}** team is assembled. {n} agents recruited, domain file created.

They don't know anything yet. Teach them:
1. Edit `wiki/domains/{domain}.md` — write the context only you know
2. Edit each agent stub — define what they specialize in
3. Run `/teams-deploy` to activate them in this repo
```

## Constraints

- Use HTML comments as placeholders, not lorem ipsum
- Never generate fake domain content
- Keep frontmatter flat YAML
- Agent stubs are wiki pages, not Claude Code agent definitions
- Always check for existing domain before creating

Usage:
- `/teams-new <domain>` — scaffold a domain
- `/teams-new <domain> --agents python-engineer,network-engineer` — with specific roles
