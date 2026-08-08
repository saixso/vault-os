# Contributing to vault-os

vault-os is maintained by [saixso](https://github.com/saixso). PRs welcome.

## Repo Anatomy

```
vault-os/
├── .claude-plugin/        Plugin + marketplace manifests
├── .cursor-plugin/        Cursor plugin manifests
├── skills/                Agent skills (add new dirs under skills/<name>/)
├── agents/                Agent definitions
├── hooks/                 Claude + Cursor hooks
├── commands/              Slash commands
├── rules/                 Cursor always-on rules
├── scripts/               Vault tooling (hot-sync, retrieve, locks, …)
├── bin/                   Setup scripts
├── docs/                  Project docs and templates
├── wiki/                  Dogfood vault knowledge
└── CLAUDE.md / AGENTS.md  Agent instructions
```

The whole tree is product-owned. Prefer additive `skills/<new-name>/` for new capabilities so history stays readable.

## Skill Anatomy

A skill is a `SKILL.md` file that tells the agent how to behave when triggered.

```
skills/<name>/
├── SKILL.md           # Required
└── references/        # Optional supporting docs
```

See `docs/templates/SKILL-TEMPLATE.md`.

## Dev Workflow

1. Branch `feat/<name>` off `main`
2. Build and test locally (`make test` where relevant)
3. Open a PR to `saixso/vault-os`

## Release

1. Bump version in `.claude-plugin/plugin.json` and `.cursor-plugin/plugin.json`
2. Update `CHANGELOG.md`
3. Merge to `main` and verify marketplace install from a clean project

## License

MIT. See [LICENSE](LICENSE) and [ATTRIBUTION.md](ATTRIBUTION.md).
