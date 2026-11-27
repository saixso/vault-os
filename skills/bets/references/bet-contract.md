# Bet contract

The shape of a bet note, and who writes what. The `bets` skill and
`scripts/bets.py` follow this.

## Where notes live

- One note per bet: `bets/<Bet name>.md`. Characters Obsidian rejects in file
  names (`/ \ : * ? " < > | # ^ [ ]`) become spaces; the full name stays in
  the `bet` field and the heading.
- A note is a bet when its frontmatter has `type: bet`. Other notes in `bets/`
  are ignored.
- The radar is `bets/Bet Radar.md` (`type: bet-radar`), rewritten on every
  `score` run. Nobody edits it by hand.
- Template: the vault's `templates/bet.md` if it has one, else
  `skills/bets/templates/bet.md`.

## Frontmatter

| Field | Who | Meaning |
|---|---|---|
| `bet` | user | Name of the bet |
| `owner` | user | One person who answers for it |
| `area` | user | `work` or `life` |
| `cycle` | user | Cycle label, optional. It does not set the status |
| `status` | user | `in progress`, `paused`, or `done` |
| `rating` | user | `won`, `lost`, or `push`. Blank until the user rates it |
| `why` | user | Why the bet was placed |
| `value` | user | The business number that says whether it paid off. Blank if there is no number yet |
| `source` | agent | `backfill` for notes made from memory |

`score` reads `status` and `rating`. It does not write them.

Anything outside the three status words (`off-track`, `drifting`, a blank)
shows on the radar as not set. The note is left as it is until the user sets one.

## Body

```
## Why

{{why}}

## Value

{{value}}

## Notes
```

## Follow-ups

Each names the bet's owner:

- no owner: name one
- status is not one of the three: set in progress, paused, or done
- status is done and rating is blank: rate it won, lost, or push

## Radar

`bets/Bet Radar.md` groups bets into In progress, Paused, Done, and Not set.
Each row shows the owner, the rating, and the value. Follow-ups are listed
under that. A Dataview block reads the same fields.
