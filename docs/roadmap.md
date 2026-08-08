# vault-os Roadmap

## Product stance (2026-08)

vault-os is an **independent product** (not an upstream fork UI). Historical credit: [ATTRIBUTION.md](../ATTRIBUTION.md).

Honest surface: a compounding Obsidian wiki plugin for agents. Context bus / `.vault-os.yml` is future work, not shipped.

## Core (shipped and daily)

- [x] Wiki loop: ingest, query, lint, save
- [x] Cursor + Claude Code plugin manifests
- [x] hot-sync (`scripts/hot-sync.sh` + SessionStart/Stop)
- [x] Supporting: defuddle, canvas, obsidian-markdown, obsidian-bases

## Gated (shipped, needs setup)

- [x] teams-new / teams-deploy / teams-sync (code exists)
- [ ] Seed real work domains under `wiki/domains/` so teams-* is usable
- [ ] Wire `/teams-deploy` into the repos you touch most
- [x] publish / feature-request (maintainer tools)

## Dormant / advanced (shipped, not promoted)

- [x] DragonScale: fold, addresses, tiling, boundary-first autoresearch (opt-in docs)
- [x] Compound Vault: wiki-retrieve, wiki-cli, wiki-mode
- Keep dormant until core + domains are habitual

## Next

- [ ] Archive inherited seed-wiki marketing pages (one-shot)
- [ ] Prefer Core skills in agent guidance (done in AGENTS.md / README)

## Later

- [ ] Context bus: `.vault-os.yml` tiered context budgets
- [ ] Token-aware ingest / cost tracking
- [ ] Community templates (infra wiki, SaaS brain)
