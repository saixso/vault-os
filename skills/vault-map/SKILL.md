---
name: vault-map
description: >
  Draw an Obsidian vault as a strategy-game map: territories are communities
  of linked concept notes, terrain is each note's maturity, turns are months,
  roads run from idea to bet to built to finished, unexplored routes are pairs
  of territories that many links tie together and no idea joins, and fog is
  problems with no idea. Builds a JSON file and one self-contained HTML page,
  plus a short turn report for a weekly note. Reads links and frontmatter only.
  Triggers on: "vault map", "map of my vault", "show my territories",
  "where are my ideas forming", "refresh the map", "/vault-map".
allowed-tools: Read Write Bash Glob Grep
---

# vault-map: the vault as a strategy map

`scripts/vault-map/build.py` turns the vault's links and frontmatter into a map,
the same way every run. The agent runs it, reads the turn report, and talks the
user through what changed. The agent never edits notes to make the map look
better; gaps on the map are findings to show the user.

## Paths

- **Plugin root** (`PLUGIN`): `${CLAUDE_PLUGIN_ROOT}` in Claude Code. In Cursor
  or a plain checkout of vault-os, the folder two levels above this file.
- **Script** (`M`): `python3 PLUGIN/scripts/vault-map/build.py --vault VAULT`.
- **Vault** (`VAULT`): `--vault`, then `$VAULT_OS_VAULT_ROOT`, then the current
  directory. The script refuses a folder with none of `.obsidian/`, `wiki/`, `templates/`.
- **Outputs** (only where the user wants them; suggested):
  `VAULT/dashboards/vault-map.json` and `VAULT/dashboards/vault-map.html`.
- **Config** (optional): `VAULT/dashboards/vault-map-config.json`, or `--config`.

## What the map reads

| Kind | Default folders | Fields used |
|---|---|---|
| concept | `wiki/concepts/`, `concepts/` | `status`, `created`, `related`, links |
| idea | `wiki/ideas/`, `ideas/`, `* Ideas/` | `created`, `solves`, `became_bet`, links |
| problem | `wiki/problems/`, `problems/`, `* Problems/` | `ideas`, links |
| bet | `bets/`, `wiki/pitches/` | `started`, `cycle_start`, `shipped`, `dropped`, `delivery`, `kpi_result`, `outcome`, `from_ideas` |
| insight, decision | `insights/`, `wiki/decisions/` and `* Insights/`, `* Decisions/` | links (an insight joining two territories closes their route) |

A `type:` of `concept`, `idea`, `problem`, `bet`, `pitch`, `decision` or
`insight` places a note anywhere. Any other `type:` (a radar, a plan) leaves it
out, and so do notes with no frontmatter, notes tagged `moc` or `dashboard`,
`README`/`_index`-style files, and `inbox/`, `wiki/sources/`, `wiki/entities/`,
`meetings/`, `people/`, `Archives/`, `templates/`, `reviews/`, `dashboards/`.
Note text is never read for meaning, printed or copied: only link targets.

## Route

| Ask | Flow |
|---|---|
| show me the map, refresh it | 1. Build |
| the weekly note, weekly review | 2. Turn report |
| rename or join territories | 3. Config |
| claim a route, "what idea joins X and Y?" | 4. Claim |
| why don't my bets show roads? | 5. Roads |

## 1. Build

1. `M --json VAULT/dashboards/vault-map.json --html VAULT/dashboards/vault-map.html --summary`.
   Ask before the first write to the vault; later refreshes can rewrite the same two files.
2. Tell the user where the page is and give the turn report in a few lines:
   what grew, ideas formed, bets started and shipped, the top route, the fog count.
3. Commit the two files only if the user's vault rules say generated files are
   committed. Never commit anything else with them.

## 2. Turn report

`M --summary` prints about six Markdown lines and writes nothing. To put it in a
weekly note, paste it under the user's own heading or a planner block the user
set up. Mention a spike once: many concepts in one turn usually means an import,
not growth.

## 3. Config

The default territory name is its most-linked concept. When the user wants
other names, or two territories joined, write `dashboards/vault-map-config.json`
with only the keys that change, then rebuild:

```json
{"names": {"Hub concept note": "Territory name"},
 "merge": {"Hub concept note": "Hub concept note it joins"},
 "resolution": 1.0, "min_territory": 8, "max_territories": 10}
```

Other keys: `kinds` and `types` (folders and types per kind), `skip`, `skip_names`,
`skip_tags`, `need_frontmatter`, `maturity` (status value to core, developing or
seed), `min_unlock_links`, `max_unlocks`, `vault_name` (for `obsidian://` links).
An unknown key is an error, so a typo never passes silently.

## 4. Claim

A route's **Claim** button only copies a prompt; the page writes nothing. When
the user asks to claim one:

1. Read the two hub notes and the route's shared-ground notes.
2. Draft one seed idea note (120 words or fewer) that links both hubs, in the
   vault's idea format, and show it to the user.
3. Create it only on the user's yes, in the vault's ideas folder. Rebuild; the
   route closes once an idea links both territories.

## 5. Roads

A road from idea to bet exists only when the vault records it: `from_ideas:` on
the bet, `became_bet:` on the idea, or a plain link between them. Shipped and
finished come from the bet's `shipped`, `delivery`, `kpi_result` and `outcome`
(the `bets` skill keeps these). When the pipeline shows bets with no idea, tell
the user how many and offer to add `from_ideas:` to the bets they name, one at a
time. Never fill fields in bulk or guess which idea a bet came from.

## Constraints

- Read-only on notes. The script writes only the output paths it is given.
- Never modify `.obsidian/`, never move, rename or delete notes.
- Outputs hold note names and paths, never note text.
- Same notes in, same map out: no randomness, no model calls in the script.
