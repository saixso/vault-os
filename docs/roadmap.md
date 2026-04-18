# vault-os Roadmap

## Phase 1 — Minimum Viable Fork (DONE)

- [x] Fork upstream `AgriciDaniel/claude-obsidian`
- [x] Rebrand: plugin.json, marketplace.json, README, ATTRIBUTION
- [x] Upstream remote configured for sync
- [x] Branch `feat/sai-v1` → merged to main

## Phase 2 — Harness & Hooks Layer

- [ ] `harness/` directory — custom orchestration layer
- [ ] Opinionated defaults for infra/platform engineering workflows
- [ ] Custom hooks: pre-ingest validation, post-ingest graph health
- [ ] Custom skills: `/forge` integration, project scaffolding
- [ ] Token-aware ingest (model selection, cost tracking)
- [ ] Auto-commit and vault health monitoring

## Phase 3 — First Public Release

- [ ] End-to-end install test (fresh machine)
- [ ] Plugin marketplace submission
- [ ] Documentation: setup guide, customization guide
- [ ] Release notes and changelog
- [ ] Community templates (infra wiki, SaaS brain, research vault)
