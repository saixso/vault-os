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

- [x] publish / feature-request (maintainer tools)

## Dormant / advanced (shipped, not promoted)

- [x] DragonScale: fold, addresses, tiling, boundary-first autoresearch (opt-in docs)
- [x] Compound Vault: wiki-retrieve, wiki-cli, wiki-mode
- Keep dormant until the core loop is habitual

## Next

- [ ] Archive inherited seed-wiki marketing pages (one-shot)
- [ ] Prefer Core skills in agent guidance (done in AGENTS.md / README)

## Not shipped

- [ ] **Cross-repo domain context.** `teams-new` / `teams-deploy` / `teams-sync` were removed in v2.4.2. The skills wrote `wiki/domains/<domain>.md` and a `domain: <name>` pointer into each repo's `.claude/CLAUDE.md`, but the "Domain Router" hook that resolved that pointer was never built — it existed only in prose in the skill bodies. Nothing loaded the domain file, so the whole chain was inert. If this returns, skip the pointer indirection: write the domain content straight into `{repo}/.claude/CLAUDE.md`, which Claude Code already auto-loads and which survives context compaction (hook STDOUT does not).

## Later

- [ ] Context bus: `.vault-os.yml` tiered context budgets
- [ ] Token-aware ingest / cost tracking
- [ ] Community templates (infra wiki, SaaS brain)
