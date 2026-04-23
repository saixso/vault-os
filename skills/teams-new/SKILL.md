---
name: teams-new
description: >
  Scaffold a new domain team — creates the domain file, agent stubs, and wiring.
  The domain file is where you write real-world context: how things work, what breaks,
  conventions that aren't in code. Agents pull from this + the wiki at runtime.
  Triggers on: "teams new", "teams:new", "/teams-new", "create a team",
  "scaffold a domain", "new domain".
allowed-tools: Read Write Edit Glob Grep Bash
---

# teams-new: Scaffold a Domain Team

Create the foundation for a domain team: a domain file you fill with real context, agent definitions, and the wiring that connects them to the vault.

The domain file is manually written — only you know the mental model, failure modes, and conventions that matter. This skill gives you the right structure and wires it to the wiki.

---

## Inputs

- **domain name** (required): lowercase, hyphenated (e.g., `payments`, `onboarding`, `billing`)
- **vault path** (optional): defaults to `./wiki/` in the current project, otherwise ask the user
- **agents** (optional): list of agent roles to scaffold (e.g., `python-engineer`, `network-engineer`)

If the user doesn't provide agents, ask: "What agent roles does this domain need?"

---

## Workflow

### 1. Resolve the vault path

Check in order:
1. `./wiki/` in current directory
2. Ask the user

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
<!-- The mental model. How data flows. How components connect.
What the pipeline actually does. The things that aren't obvious from reading the code. -->

## What breaks and why
<!-- Patterns of failure. What to check first.
The non-obvious failure modes. What broke last time. -->

## Conventions
<!-- Rules not written anywhere else.
Naming patterns, testing conventions, what never to do.
The shortcuts senior engineers take that juniors miss. -->

## Current context
<!-- What's active right now. Open problems. Recent changes.
What the team is focused on this sprint. -->

## Vault — query when needed
<!-- Link wiki pages agents should pull when they need depth.
These are NOT loaded at startup — agents lazy-load on demand. -->
```

### 4. Create agent stubs

For each agent role, write `{vault}/wiki/agents/{domain}-{role}.md`:

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
<!-- What this agent specializes in within the {domain} domain -->

## Knowledge
<!-- Domain-specific patterns, tools, and conventions this agent should know -->

## Tools & MCPs
<!-- Which MCP servers and tools this agent needs access to -->

## Constraints
<!-- What this agent must NOT do. Scope limits. -->
```

### 5. Wire the domain to the vault index

Append to `{vault}/wiki/index.md`:
```
## Domains
- [[{domain}]] — {one-line description}
```

If a `## Domains` section already exists, append under it.

### 6. Report

Tell the user:
```
Domain scaffolded:
  wiki/domains/{domain}.md        ← fill in your context here
  wiki/agents/{domain}-{role}.md  ← one per agent role

Next steps:
1. Edit wiki/domains/{domain}.md — write the real-world context only you know
2. Edit each agent stub — add role-specific knowledge
3. Run /teams-deploy {domain} <repo-path> to wire it into a repo
```

---

## Constraints

- Domain file MUST use HTML comments as placeholders, not lorem ipsum
- Never generate fake domain content — the user writes real context
- Keep frontmatter flat YAML (no nesting beyond one level for delivery)
- Agent stubs are wiki pages (in wiki/agents/), not Claude Code agent definitions
- Always check for existing domain before creating
- Token budget: domain file should stay under ~500 tokens when filled in
