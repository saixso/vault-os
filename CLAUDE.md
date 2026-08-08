# vault-os Development

vault-os is an independent Claude Code + Cursor plugin and Obsidian wiki companion, maintained by saixso.

## Ownership

The whole plugin tree is vault-os owned. Edit any path when the change serves this product.

| Directory | Notes |
|-----------|-------|
| `skills/`, `agents/`, `commands/`, `hooks/` | First-class product surface |
| `.claude-plugin/`, `.cursor-plugin/` | Marketplace manifests |
| `rules/`, `scripts/`, `bin/`, `docs/` | Tooling and docs |
| `wiki/`, `.raw/` | Dogfood vault (`.raw/` remains immutable at runtime) |

Prefer additive skills (`skills/<new-name>/`) when introducing a capability.

## Dev Workflow

This repo **is** the plugin. Claude Code and Cursor auto-discover skills/agents/hooks from the project directory.

### Dev mode
1. Work inside this repo — local auto-discovery loads all skills
2. Disable marketplace plugin (`vault-os@vault-os-marketplace` in `~/.claude/settings.json`) to avoid duplicates
3. Create a new skill: `skills/<name>/SKILL.md` (see `docs/templates/SKILL-TEMPLATE.md`)
4. Optionally add `agents/<name>.md` or `commands/<name>.md`
5. Test live — invoke it, verify behavior, iterate

### Publish
Push to `saixso/vault-os` on GitHub — the marketplace serves from this repo.

## Branch Convention

`feat/<name>` off `main`. PR to `saixso/vault-os`.

## Release Checklist

1. Bump version in `.claude-plugin/plugin.json` and `.cursor-plugin/plugin.json`
2. Test locally
3. Update `CHANGELOG.md`
4. Push / merge to `main`
5. Verify marketplace serves the update

## Docs

- `docs/architecture.md` — plugin structure
- `docs/roadmap.md` — phases and milestones
- `docs/templates/` — skill and agent starters
- `CONTRIBUTING.md` — contributor guide
