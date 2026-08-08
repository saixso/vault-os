# vault-os

A persistent, compounding Obsidian wiki for AI agents. Ingest sources, query what you know, save decisions, keep session context honest.

Built by [saixso](https://github.com/saixso). Inspired by [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-8B5CF6)](https://code.claude.com/docs/en/discover-plugins)
[![Cursor](https://img.shields.io/badge/Cursor-plugin-1e1e1e)](https://cursor.com/docs/plugins)

Works with Claude Code, Cursor, and other agents that load Agent Skills. Knowledge compounds in `wiki/` instead of restarting from a blank chat every session.

---

## What it does (core)

| Command | What it does |
|---------|--------------|
| `/wiki` | Setup, scaffold, or continue where you left off |
| `ingest [file]` | Read a source, create wiki pages, update the index |
| `what do you know about X?` | Query the wiki and synthesize an answer |
| `/save` | File the current conversation as a wiki note |
| `/hot-sync` | Regenerate `wiki/hot.md` from ground truth (git + version) |
| `lint the wiki` | Health check: orphans, dead links, gaps |

Supporting core skills: `defuddle`, `canvas`, `obsidian-markdown`, `obsidian-bases`.

### Gated (real code, needs setup)

- **teams-new / teams-deploy / teams-sync** — cross-repo domain context. Needs `wiki/domains/` first (`/teams-new`).
- **publish / feature-request** — maintainer tooling for this repo.

### Dormant / advanced (shipped, not the daily path)

DragonScale (log folds, page addresses, semantic tiling), hybrid retrieve, methodology modes (`wiki-mode`), `wiki-cli`, and `autoresearch` live under `skills/` and in [docs/dragonscale-guide.md](docs/dragonscale-guide.md) / [docs/compound-vault-guide.md](docs/compound-vault-guide.md). Use when you opt in; they are not required for the core loop.

Full inventory: [AGENTS.md](AGENTS.md).

---

## Quick Start

### Claude Code

```bash
claude plugin marketplace add saixso/vault-os
claude plugin install vault-os@vault-os-marketplace
```

### Cursor

```
Settings → Plugins → Add marketplace → saixso/vault-os
```

### Other agents (Codex CLI, OpenCode, Gemini CLI, Windsurf)

```bash
git clone https://github.com/saixso/vault-os.git
cd vault-os
bash bin/setup-multi-agent.sh
```

In any session: `/wiki`.

---

## How the vault works

```
vault/
├── .raw/     # immutable sources
├── wiki/     # agent-written knowledge (index, log, hot cache, pages)
└── skills/   # this plugin
```

- **Hot cache** (`wiki/hot.md`): injected at session start; Ground Truth owned by `scripts/hot-sync.sh`.
- **Log** (`wiki/log.md`): append-only operations journal.
- **Index** (`wiki/index.md`): catalog of pages.

---

## Roadmap

1. **Wiki engine (done)** — ingest, query, lint, save, hot-sync.
2. **Domains** — seed real `wiki/domains/` so teams-* becomes part of the daily path.
3. **Context bus (future)** — optional `.vault-os.yml` for tiered context budgets. Not shipped today.
4. **Templates** — community vault shapes (infra, SaaS, research).

See [docs/roadmap.md](docs/roadmap.md).

---

## License

MIT. See [LICENSE](LICENSE) and [ATTRIBUTION.md](ATTRIBUTION.md).

*Built and maintained by [saixso](https://github.com/saixso).*
