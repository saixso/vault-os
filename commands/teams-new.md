---
description: Scaffold a new domain team — creates domain file, agent stubs, and vault wiring.
---

You are the teams-new skill. Scaffold a domain team: a domain file, agent stubs, and vault wiring.

IMPORTANT: This is a generic skill for any user in any project. When asking for input (domain name, vault path, agent roles), do NOT pre-fill suggestions based on the current repo, project name, file contents, session context, hooks, or environment. Always let the user type their own values. Only provide generic examples like `payments`, `onboarding`, `python-engineer`.

## Inputs

- **domain name** (required): lowercase, hyphenated (e.g., `payments`, `onboarding`). Taken from the user's command arguments.
- **vault path** (optional): resolved automatically (see vault resolution below).
- **agents** (optional): agent roles to scaffold. If not provided, ask: "What agent roles does this domain need? (e.g. `python-engineer`, `devops-engineer`)" Do not suggest roles based on the current repo, project name, or session context. Let the user type their own.

If no domain name was provided, ask: "What domain name? (lowercase, hyphenated, e.g. `payments`, `onboarding`)" Do not suggest domain names based on the current repo or project context. Let the user type their own.

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

## What this domain is
<!-- One sentence — the mission. What does this team own? -->

## How things work here
<!-- The mental model. How data flows. How components connect. -->

## What breaks and why
<!-- Patterns of failure. What to check first. -->

## Conventions
<!-- Rules not written anywhere else. Naming patterns, testing conventions. -->

## Current context
<!-- What's active right now. Open problems. Recent changes. -->

## Vault — query when needed
<!-- Link wiki pages agents should pull when they need depth. -->
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
6. **Report**: show created files and next steps (edit domain file, edit agent stubs, run `/teams-deploy`)

## Constraints

- Use HTML comments as placeholders, not lorem ipsum
- Never generate fake domain content
- Keep frontmatter flat YAML
- Agent stubs are wiki pages, not Claude Code agent definitions
- Always check for existing domain before creating

Usage:
- `/teams-new <domain>` — scaffold a domain
- `/teams-new <domain> --agents python-engineer,network-engineer` — with specific roles
