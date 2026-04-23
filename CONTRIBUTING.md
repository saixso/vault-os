# Contributing to vault-os

vault-os is a fork of [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) by AgriciDaniel. It ships all upstream wiki skills plus custom extensions as one Claude Code plugin.

## Repo Anatomy

```
vault-os/
├── .claude-plugin/        ← Branded (vault-os identity, marketplace config)
├── skills/                ← Upstream + custom skills
│   ├── wiki/              ← Upstream — DO NOT MODIFY
│   ├── wiki-ingest/       ← Upstream — DO NOT MODIFY
│   ├── save/              ← Upstream — DO NOT MODIFY
│   ├── autoresearch/      ← Upstream — DO NOT MODIFY
│   ├── canvas/            ← Upstream — DO NOT MODIFY
│   ├── obsidian-markdown/ ← Upstream — DO NOT MODIFY
│   ├── obsidian-bases/    ← Upstream — DO NOT MODIFY
│   ├── wiki-query/        ← Upstream — DO NOT MODIFY
│   ├── wiki-lint/         ← Upstream — DO NOT MODIFY
│   ├── defuddle/          ← Upstream — DO NOT MODIFY
│   ├── feature-request/   ← Upstream — DO NOT MODIFY
│   └── <your-skill>/      ← Custom — ADD NEW DIRS HERE
├── agents/                ← Upstream + custom agents
│   ├── wiki-ingest.md     ← Upstream — DO NOT MODIFY
│   ├── wiki-lint.md       ← Upstream — DO NOT MODIFY
│   └── <your-agent>.md    ← Custom — ADD NEW FILES HERE
├── hooks/                 ← Upstream — DO NOT MODIFY
├── commands/              ← Upstream + custom commands
├── bin/                   ← Setup scripts
├── docs/                  ← Project docs and templates
└── CLAUDE.md              ← Agent instructions (editable)
```

**The rule:** upstream files are read-only. Custom features go in **new** files and directories. This keeps `git merge upstream/main` conflict-free.

## Skill Anatomy

A skill is a `SKILL.md` file that tells Claude Code how to behave when triggered.

```
skills/<name>/
├── SKILL.md              # Required — the skill definition
└── references/           # Optional — supporting docs the skill reads at runtime
    ├── patterns.md
    └── examples.md
```

### SKILL.md Structure

```yaml
---
name: my-skill
description: >
  One-sentence pitch. What it does and when.
  Triggers on: "phrase 1", "phrase 2", "/my-skill".
allowed-tools: Read Write Edit Glob Grep Bash WebFetch
---

# my-skill: Human-Readable Title

One paragraph explaining the purpose and philosophy.

---

## Workflow

1. Step one — what to do first
2. Step two — core logic
3. Step three — output and cleanup

## Output Format

Describe what the skill produces (files, messages, etc).

## Constraints

- What NOT to do
- Token budgets, safety rails
```

**Frontmatter fields:**
- `name` — lowercase, hyphenated, matches directory name
- `description` — multi-line, includes trigger phrases for Claude to match
- `allowed-tools` — space-separated list of Claude Code tools the skill may use

**Body sections:** Role/intro → Workflow → Output → Constraints. Decision tables and examples are encouraged.

### References

Put supporting docs in `skills/<name>/references/`. The skill body can instruct Claude to read these at runtime. Use for schemas, patterns, or long reference material that would bloat the SKILL.md.

## Agent Anatomy

An agent is a `.md` file that defines a subagent Claude can dispatch for parallel or specialized work.

```yaml
---
name: my-agent
description: >
  What it does. When to dispatch.
  <example>Context: ... assistant: "..."</example>
model: sonnet
maxTurns: 30
tools: Read, Write, Edit, Glob, Grep
---

You are a [role]. Your job is to [primary purpose].

You will be given:
- Input 1
- Input 2

## Your Process

1. Step one
2. Step two

## Output Format

Report: "Field: value | Field: value"

## Rules

- What you must NOT do
- Scope limits
```

**Frontmatter fields:**
- `name` — matches filename (without `.md`)
- `description` — when Claude should dispatch this agent, with examples
- `model` — `sonnet` for bulk work, `opus` for complex reasoning
- `maxTurns` — conversation depth limit (30 is typical)
- `tools` — comma-separated list of tools the agent can use

## Slash Commands

A command is a lightweight router in `commands/<name>.md` that points to a skill:

```yaml
---
description: One-line description of what /name does.
---

Read the `<skill-name>` skill. Then run the workflow.

Usage:
- `/<name>` — default behavior
- `/<name> [args]` — with arguments
```

Commands contain no logic — they just load the skill and pass through arguments.

## Step-by-Step: Adding a New Skill

1. **Branch:** `git checkout -b feat/<skill-name> main`
2. **Create directory:** `skills/<skill-name>/`
3. **Write SKILL.md:** Copy from `docs/templates/SKILL-TEMPLATE.md`, fill in your logic
4. **Add references (optional):** `skills/<skill-name>/references/`
5. **Add command (optional):** `commands/<skill-name>.md` to create a `/slash-command`
6. **Test locally:** You're in the repo, so Claude auto-discovers the skill. Invoke it and iterate.
7. **PR:** Push branch, open PR to `main` on `saixso/vault-os`

## Step-by-Step: Adding a New Agent

1. **Branch:** `git checkout -b feat/<agent-name> main`
2. **Write agent:** `agents/<agent-name>.md` — copy from `docs/templates/AGENT-TEMPLATE.md`
3. **Test locally:** Trigger it via a skill or directly
4. **PR:** Push branch, open PR to `main`

## Testing

### Dev mode (local auto-discovery)

1. Work inside the vault-os repo directory
2. Disable marketplace plugin to avoid duplicates:
   ```json
   // ~/.claude/settings.json → enabledPlugins
   "vault-os@vault-os-marketplace": false
   ```
3. Invoke your skill — Claude discovers it from `./skills/`
4. Iterate: edit SKILL.md, re-invoke, repeat

### Consumer mode (marketplace)

1. `cd` to a different project directory
2. Re-enable the marketplace plugin:
   ```json
   "vault-os@vault-os-marketplace": true
   ```
3. Invoke the skill — Claude loads it from the published GitHub repo
4. Verify it works identically to local

### What to verify

- Skill triggers on expected phrases
- Correct tools are available (check `allowed-tools`)
- Output matches expected format
- No upstream files were modified (`git diff --name-only upstream/main`)

## Fork Sync

Pull upstream improvements without breaking custom work:

```bash
git fetch upstream
git merge upstream/main
```

Conflicts only hit branded files (`.claude-plugin/`, `README.md`, `ATTRIBUTION.md`). Custom skills in new directories are never touched.

If upstream adds a skill with the same name as one of yours, rename yours before merging.

## Release Checklist

1. Bump `version` in `.claude-plugin/plugin.json`
2. Update `.claude-plugin/marketplace.json` if metadata changed
3. Test all new skills locally (dev mode)
4. Test from a consumer project (marketplace mode)
5. Run `git diff --name-only upstream/main` — confirm no upstream files modified
6. Push to `main` on `saixso/vault-os`
7. Verify marketplace serves the update
