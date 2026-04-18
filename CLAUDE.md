# vault-os Development

Fork of [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) by AgriciDaniel.

## Rules

- Keep upstream-overlapping changes to branded files only (plugin.json, marketplace.json, README, ATTRIBUTION)
- New features go in new files/dirs — never modify upstream skill/hook/agent files
- Branch per feature off main (`feat/<name>`)
- Always credit AgriciDaniel/claude-obsidian as upstream
- Test plugin install flow before any release

## Fork Sync

```bash
git fetch upstream
git merge upstream/main
```

## Docs

Project docs live in `docs/` — see `docs/roadmap.md` for phases and `docs/architecture.md` for plugin structure.
