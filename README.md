
# vault-os

A schema-agnostic context bus for AI agents. Load the right knowledge, from the right sources, in the right order — so every token in the context window earns its keep.

**Fork of [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) by [AgriciDaniel](https://github.com/AgriciDaniel).** Based on [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-8B5CF6)](https://code.claude.com/docs/en/discover-plugins)
[![Upstream](https://img.shields.io/badge/upstream-claude--obsidian-orange)](https://github.com/AgriciDaniel/claude-obsidian)

---

## The Problem

AI agents start blank. Every session, you re-explain the same context: what your company does, why you're building this way, who owns what, what constraints matter. The agent writes correct code but not the *right* code — because it's missing the human layer.

Docs tell agents *how*. Repo configs tell agents *where*. Nothing tells them *why*.

## The Vision

vault-os is a **context bus** — a plugin that composes agent context windows from three non-overlapping tiers:

| Tier | Owns | Answers | Source |
|------|------|---------|--------|
| **Local harness** | Repo-specific facts — file paths, configs, conventions | *Where* | CLAUDE.md, `.vault-os.yml` |
| **Structured knowledge API** | Domain reference — docs, runbooks, how-to | *How* | Any MCP server or docs API |
| **Vault** | Human layer — biz context, axioms, intent, priorities | *Why* | Obsidian vault |

The vault fills the gap no other layer covers: the stuff in people's heads and Slack threads. The context people forget to give. With all three tiers composed, 5-turn disambiguation loops collapse into single turns.

### Schema-agnostic by design

The plugin has zero opinions on how you organize your vault. It's a context loader with a resolution engine — you bring the meaning.

A repo declares what context it needs:

```yaml
# .vault-os.yml
vault: ~/Documents/my-vault
context:
  - path: _axioms.md
  - path: _biz-context.md
  - path: domains/infrastructure/_axioms.md
  - path: domains/infrastructure/subdomains/frontdoor/_context.md
  - api: infra-docs
budget:
  per_source: 2000
  total: 10000
```

Someone else's might look completely different:

```yaml
vault: ~/Documents/startup-brain
context:
  - path: principles.md
  - path: product/north-star.md
  - api: context7
```

Same plugin. Same metal. Different philosophy. You define the schema — DDD bounded contexts, flat files, topic clusters, whatever fits your mental model.

### The metal-level pattern

Swap the middle tier (structured API) and the same architecture serves completely different use cases:

| Use case | Local | Structured API | Vault context |
|----------|-------|---------------|---------------|
| Infrastructure | repo CLAUDE.md | infra-docs MCP | biz priorities, team ownership |
| ML project | model repo configs | context7 / HuggingFace | why this model, dataset constraints |
| Personal project | project CLAUDE.md | library docs | goals, design taste, decided tradeoffs |
| Incident response | runbook repo | Grafana MCP | who's on call, what changed, blast radius |

The vault is the constant. The structured API is swappable. The local harness is throwaway.

### Compounding, not accumulating

Most knowledge systems accumulate notes and RAG from scratch every time. vault-os compounds — source #30 produces better output than source #5 because the engine reads 29 existing wiki pages before extracting. Context-aware read-before-write.

---

## What It Does Today

vault-os is a Claude Code plugin that manages a persistent, compounding wiki vault in Obsidian.

### Commands

| You say | Claude does |
|---------|------------|
| `/wiki` | Setup check, scaffold, or continue where you left off |
| `ingest [file]` | Read source, create wiki pages, update index and log |
| `ingest all of these` | Batch process multiple sources with parallel agents |
| `what do you know about X?` | Read index > relevant pages > synthesize answer |
| `/save` | File the current conversation as a wiki note |
| `/autoresearch [topic]` | Autonomous research loop: search, fetch, synthesize, file |
| `/canvas` | Visual canvas layer for images, text, PDFs, wiki pages |
| `lint the wiki` | Health check: orphans, dead links, gaps, suggestions |

### Skills

10 skills included: wiki orchestrator, wiki-ingest, wiki-query, wiki-lint, save, autoresearch, canvas, obsidian-markdown, obsidian-bases, defuddle.

See [upstream docs](https://github.com/AgriciDaniel/claude-obsidian) for full skill documentation.

---

## Roadmap

### Phase 1 — Wiki Engine (done)
Ingest, query, lint, index. Context-aware extraction with compounding knowledge base. Hot cache for cross-project context sharing.

### Phase 2 — Plugin + Skills (current)
Claude Code plugin packaging. 10 skills for vault operations. Obsidian-native markdown, canvas, and bases support.

### Phase 3 — Context Bus
The three-tier architecture. `.vault-os.yml` declaration format. Schema-agnostic context loading with resolution order and token budgets. Repo-side integration where thin harnesses point at the vault instead of duplicating context.

### Phase 4 — Public Release
End-to-end install experience. Documentation. Community templates. "Drop vault-os on any vault" as a one-command setup.

---

## Quick Start

### Install as Claude Code plugin

```bash
claude plugin marketplace add saixso/vault-os
claude plugin install vault-os@vault-os-marketplace
```

In any Claude Code session: `/wiki`. Claude walks you through vault setup.

### Clone as vault

```bash
git clone https://github.com/saixso/vault-os
cd vault-os
bash bin/setup-vault.sh
```

Open in Obsidian. Open Claude Code in the same folder. Type `/wiki`.

---

## What Changed From Upstream

- Rebranded to `vault-os`
- Opinionated defaults for infrastructure/platform engineering workflows
- Harness and hooks layer (coming in Phase 3)
- Upstream syncs via `git fetch upstream`

Everything else builds on [claude-obsidian v1.4.3](https://github.com/AgriciDaniel/claude-obsidian).

## Syncing With Upstream

```bash
git fetch upstream
git merge upstream/main
```

---

## Attribution

This project is a fork of [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) by [AgriciDaniel](https://github.com/AgriciDaniel), licensed under MIT. See [ATTRIBUTION.md](ATTRIBUTION.md) for full credits.

---

*Built by [saixso](https://github.com/saixso). Forked from [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) by [AgriciDaniel](https://agricidaniel.com/about).*
