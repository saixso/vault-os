
# vault-os

Opinionated Claude Code + Obsidian knowledge companion. A persistent, compounding wiki vault with harness and hooks.

**Fork of [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) by [AgriciDaniel](https://github.com/AgriciDaniel).** Based on [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-8B5CF6)](https://code.claude.com/docs/en/discover-plugins)
[![Upstream](https://img.shields.io/badge/upstream-claude--obsidian-orange)](https://github.com/AgriciDaniel/claude-obsidian)

---

## What Changed From Upstream

- Rebranded to `vault-os`
- Opinionated defaults for infrastructure/platform engineering workflows
- Harness and hooks layer (coming in v2.1)
- Upstream syncs via `git fetch upstream`

Everything else is the same as [claude-obsidian v1.4.3](https://github.com/AgriciDaniel/claude-obsidian).

---

## Quick Start

### Install as Claude Code plugin

```bash
# Add the marketplace
claude plugin marketplace add saixso/vault-os

# Install the plugin
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

## Commands

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

---

## Skills

10 skills included: wiki orchestrator, wiki-ingest, wiki-query, wiki-lint, save, autoresearch, canvas, obsidian-markdown, obsidian-bases, defuddle.

See [upstream docs](https://github.com/AgriciDaniel/claude-obsidian) for full skill documentation.

---

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
