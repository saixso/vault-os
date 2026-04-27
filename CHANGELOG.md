# Changelog

All notable changes to vault-os and upstream claude-obsidian. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

## [2.3.1] - 2026-04-27 (vault-os)

### Fixed

- `skills/teams-sync`: renamed `ratchet` mode to `update` for clarity.

## [2.3.0] - 2026-04-27 (vault-os)

### Added

- `skills/teams-sync`: `brief` and `ratchet` modes for faster domain syncs.
- Domain template now includes agent instructions section.

## [2.2.0] - 2026-04-27 (vault-os)

### Changed

- `skills/teams-new`: knowledge-only scaffolding — no longer generates agent stubs. Agent definitions come from other plugins.

## [2.1.4] - 2026-04-27 (vault-os)

### Added

- Vault path persisted in `.claude/CLAUDE.md` after first resolution. Defaults to cwd for repo-local vaults.

## [2.1.3] - 2026-04-27 (vault-os)

### Changed

- `skills/teams-deploy`: domain context loads immediately after deploy (no session restart required).

## [2.1.2] - 2026-04-27 (vault-os)

### Fixed

- `skills/teams-deploy`: domain line always written to `.claude/CLAUDE.md`, not the project root CLAUDE.md.

## [2.1.1] - 2026-04-27 (vault-os)

### Added

- `skills/teams-deploy`: supports wiring a domain into multiple repos in one invocation. Checks for existing CLAUDE.md entries before writing.

## [2.1.0] - 2026-04-27 (vault-os)

### Fixed

- `skills/wiki-lint`: clean index entries and consistent report message formatting.

## [2.0.9] - 2026-04-27 (vault-os)

### Changed

- Domain template expanded with mission, ownership, vendors, team, and stakeholders sections.

## [2.0.2–2.0.8] - 2026-04-27 (vault-os)

### Fixed

- `skills/teams-new`: prevent context-based domain name inference; use plain text prompts instead of AskUserQuestion; vault resolution checks CLAUDE.md Path first, then `./wiki/`, then asks.
- Inline command workflows; remove hardcoded references.
- Friendlier completion message on teams-new.

## [2.0.0] - 2026-04-27 (vault-os)

### Added

- `skills/teams-new`: scaffold a new domain (knowledge-layer only).
- `skills/teams-deploy`: wire a domain into a repository via CLAUDE.md.
- `skills/teams-sync`: check what is new in the wiki for a domain, or update the domain file.
- `skills/publish`: commit, version-bump, and push vault-os to the marketplace.
- `skills/feature-request`: file feature ideas as GitHub issues on saixso/vault-os.
- `docs/`: dev workflow, contributing guide, skill and agent templates.
- `CLAUDE.md`: ownership model table, dev mode vs consumer mode workflow, release checklist.

### Changed

- README rewritten with context bus vision and three-tier architecture (local harness / structured knowledge API / vault).
- Rebrand from claude-obsidian fork to vault-os with context bus as the north star.

## [1.4.3] - prior (upstream baseline)

## [1.6.0] - 2026-04-24

### Added (DragonScale Mechanism 4, opt-in)

- **Boundary-first autoresearch**: `scripts/boundary-score.py` computes `(out_degree - in_degree) * recency_weight` across the wikilink graph and emits top-K frontier pages. `/autoresearch` invoked without a topic now offers the top-5 frontier pages as research candidates when the vault has adopted DragonScale.
- `tests/test_boundary_score.py` — 35 unit tests covering frontmatter parsing, recency weight, wikilink extraction (with code-block guard), graph construction, scoring, CLI interface.
- `make test-boundary` target + integration into `make test`.

### Changed

- `skills/autoresearch/SKILL.md` — new Topic Selection section with three paths: explicit (A), boundary-first (B, opt-in), user-ask (C, default without DragonScale).
- `commands/autoresearch.md` — no-topic usage documented for both modes.
- `wiki/concepts/DragonScale Memory.md` — Mechanism 4 flipped from NOT IMPLEMENTED to shipped; exact scoring formula and "what is NOT included" callout added. Version bumped to v0.4.
- Version synced to 1.6.0 across plugin.json and marketplace.json.

## [1.5.1] - 2026-04-24 (Phase 3.6 hardening)

### Fixed

- `scripts/tiling-check.py`: `--report PATH` now resolved against VAULT_ROOT and rejected if it escapes (security: prevents hostile or accidental writes outside the vault).
- `.vault-meta/legacy-pages.txt`: rollout baseline corrected from 2026-04-24 to 2026-04-23 (matches earliest addressed page in the seed vault).
- `AGENTS.md`: wiki-fold listed in the skills table; stale claim that "all skills use only name/description" narrowed to newer skills (older skills still carry allowed-tools for Claude Code compatibility).
- `skills/wiki-ingest/SKILL.md`: resolves the internal contradiction between "immutable .raw/" and "maintain .raw/.manifest.json" — user-dropped source documents remain immutable; only the manifest is wiki-ingest-maintained.
- `docs/install-guide.md`: version 1.2.0 -> 1.5.0 with a DragonScale optional-install callout.

## [1.5.0] - 2026-04-24

### Added (DragonScale Memory extension, opt-in)

- **Mechanism 1 — Fold operator** (`skills/wiki-fold/`): extractive, structurally-idempotent rollups of `wiki/log.md` entries into per-batch meta-pages under `wiki/folds/`. Dry-run via stdout by default (does not trigger PostToolUse auto-commit hook); commit mode explicit.
- **Mechanism 2 — Deterministic page addresses** (opt-in): `scripts/allocate-address.sh` flock-guarded atomic allocator; new `address: c-NNNNNN` frontmatter convention; re-ingest idempotency via `.raw/.manifest.json address_map`. `wiki-ingest` and `wiki-lint` skills feature-detect DragonScale setup.
- **Mechanism 3 — Semantic tiling lint** (opt-in): `scripts/tiling-check.py` uses local `nomic-embed-text` via ollama to flag candidate duplicate pages by cosine similarity. Banded thresholds (error/review/pass) documented as conservative seeds with manual calibration procedure.
- `wiki/concepts/DragonScale Memory.md` — full design spec (v0.3) with four mechanisms, scope boundary, and primary-source citations.
- `bin/setup-dragonscale.sh` — idempotent installer that provisions `.vault-meta/` counter, thresholds, and legacy-pages manifest.
- `tests/` — shell + python test suite for the allocator and tiling-check. Run via `make test`.
- `Makefile` — developer targets (`test`, `setup-dragonscale`, `clean-test-state`).

### Changed

- `hooks/hooks.json` PostToolUse now stages `.vault-meta/` in addition to `wiki/` and `.raw/` so DragonScale runtime state is captured by the auto-commit hook.
- `skills/wiki-ingest/SKILL.md` and `skills/wiki-lint/SKILL.md` gained opt-in DragonScale sections behind feature-detection guards; original behavior unchanged for vaults that have not run `setup-dragonscale.sh`.
- `agents/wiki-ingest.md` explicitly forbids parallel sub-agents from calling the allocator (single-writer rule for address assignment).
- `agents/wiki-lint.md` extended to describe Address Validation and Semantic Tiling checks.
- Stale `allowed-tools` frontmatter removed from `wiki-ingest` and `wiki-lint` SKILL.md (kepano convention: only `name` and `description`).
- Version strings synced across `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and documentation.

### Security

- `scripts/tiling-check.py` locks `OLLAMA_URL` to localhost by default. Remote endpoints require `--allow-remote-ollama`. Symlinks and vault-root escapes are rejected before any read.

### Not in this release

- **Mechanism 4 — Boundary-first autoresearch**: documented in the spec as a future proposal; no code shipped. `skills/autoresearch/SKILL.md` unchanged.

## [1.4.3] - prior

Previous state. See git log for details.
