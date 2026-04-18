# vault-os Architecture

## What It Is

A Claude Code plugin that turns any directory into a persistent, compounding Obsidian wiki vault. Fork of claude-obsidian with an opinionated harness layer.

## Plugin Structure

```
vault-os/
├── .claude-plugin/        Plugin manifests (vault-os branded)
│   ├── plugin.json        Plugin identity, version, author
│   └── marketplace.json   Marketplace distribution config
├── skills/                Claude Code skills (from upstream)
│   ├── wiki/              Main wiki orchestrator
│   ├── wiki-ingest/       Source ingestion
│   ├── wiki-query/        Query wiki content
│   ├── wiki-lint/         Health checks
│   ├── save/              Save conversation as note
│   ├── autoresearch/      Autonomous research loop
│   └── canvas/            Visual canvas layer
├── hooks/                 Claude Code hooks (from upstream)
├── agents/                Agent definitions (from upstream)
│   ├── wiki-ingest/       Parallel batch ingestion agent
│   └── wiki-lint/         Wiki health check agent
├── commands/              CLI commands (from upstream)
├── harness/               [Phase 2] vault-os custom layer
├── bin/                   Setup and utility scripts
├── docs/                  Project documentation
└── CLAUDE.md              Agent dev instructions
```

## Upstream vs Custom

| Layer | Source | Can modify? |
|-------|--------|-------------|
| skills/, hooks/, agents/, commands/ | Upstream (claude-obsidian) | No — sync breaks |
| .claude-plugin/, README, ATTRIBUTION | Branded | Yes — our 4 files |
| harness/ | vault-os custom | Yes — new dir |
| docs/ | vault-os custom | Yes — new dir |

## Per-Vault Runtime (not committed)

When a user installs the plugin and runs `/wiki`, these are created in their project:

```
.raw/            Source documents (immutable, Claude reads only)
wiki/            Generated wiki pages
_templates/      Obsidian Templater templates
_attachments/    Images and PDFs
```

## How Ingest Works

1. User drops source into `.raw/`
2. `ingest [file]` triggers wiki-ingest skill
3. Skill classifies source → extracts entities/concepts
4. Calls `create-note.sh` / `update-note.sh` to write wiki pages
5. Updates `wiki/index.md` and `wiki/hot.md`

Token cost: ~$0.10-0.50 per source depending on size.
Use `sonnet` for bulk ingest, `opus` for complex synthesis.

## Fork Sync

Upstream improvements flow in via:
```bash
git fetch upstream
git merge upstream/main
```

Conflicts only hit the 4 branded files. Custom work in harness/ is never touched.
