# Planner

Daily, weekly and monthly notes for an Obsidian vault, filled from calendar,
meeting notes and mail. The agent decides what to write; `scripts/planner.py`
creates notes from templates, writes only inside `<!-- planner:NAME -->`
blocks, and counts the scorecard.

| Skill | When | Writes |
|---|---|---|
| `planner` | "set up the planner", or any planner ask | routes to the three below; setup |
| `daily-planner` | weekday evenings | today's promises, to-dos, decisions, scorecard; next workday's prep, meeting cards and top 3 |
| `weekly-planner` | Sunday evening | last week's summary, the week ahead, suggested goals |
| `monthly-planner` | last day of the month | month scorecard, what moved, what stalled |

Rules every run follows: `skills/planner/references/note-contract.md` (blocks,
line formats, ownership) and `skills/planner/references/sources.md` (what to
read, what to leave out). Daily runs also read `meeting-prep.md` and `focus.md`.

## Requirements

- Python 3, standard library only.
- Connectors for the sources: a calendar, meeting notes (Wispr Flow in the
  reference setup), and mail. A missing connector is named in the run's report;
  the run carries on with the rest.
- In the vault: Templater, Dataview and Tasks, and `templates/daily.md`,
  `weekly.md`, `monthly.md` with the planner blocks. Starter templates are in
  `skills/planner/templates/`; the script falls back to them when the vault has
  no template of its own.

## Finding the vault

`planner.py` takes the vault from `--vault`, then `$VAULT_OS_VAULT_ROOT`, then
the current directory, and refuses a folder that has none of `.obsidian/`,
`reviews/`, `templates/`. Notes go to `reviews/daily/`, `reviews/weekly/` and
`reviews/monthly/` under it.

## Scheduled runs

A scheduled run starts in a fresh session with no plugin installed. It needs
both repositories checked out: vault-os (the planner) and the vault (the notes).

1. Paths: `PLUGIN` is the vault-os checkout, `VAULT` is the vault checkout.
2. Read the skill file and follow it:
   - daily: `PLUGIN/skills/daily-planner/SKILL.md`
   - weekly: `PLUGIN/skills/weekly-planner/SKILL.md`
   - monthly: `PLUGIN/skills/monthly-planner/SKILL.md`
   Each one reads `PLUGIN/skills/planner/references/*.md` first.
3. Script: `python3 PLUGIN/scripts/planner.py --vault VAULT <command>`, or
   `export VAULT_OS_VAULT_ROOT=VAULT` once and drop `--vault`.
4. Commit and push in the vault repo only. The run never writes to vault-os.

Inside Claude Code with the plugin installed, `PLUGIN` is `${CLAUDE_PLUGIN_ROOT}`
and the skills are discovered by name. In Cursor, the plugin's skills are
discovered the same way; use the plugin's install folder as `PLUGIN`.

## Test

```
make test-planner
```

Hermetic: renders the starter templates into a temp vault with fake notes. To
check a real vault's own templates, run
`PLANNER_TEMPLATES_DIR=/path/to/vault/templates python3 tests/test_planner.py`.
