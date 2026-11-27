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
| `odds` | user | How likely the user thinks the bet is to work, a whole percent from 0 to 100. Written when the bet is placed. `60%` and `0.6` are stored as `60` |
| `wrong_if` | user | What would prove the bet wrong. Written when the bet is placed |
| `decision` | user | `good` or `bad`: the decision judged on what was known when the bet was placed, not on how it turned out. Blank until the user rates it |
| `rating` | user | The result: `won`, `lost`, or `push`. Blank until the user rates it |
| `why` | user | Why the bet was placed |
| `value` | user | The business number that says whether it paid off. Blank if there is no number yet |
| `source` | agent | `backfill` for notes made from memory |

`score` reads `status`, `odds`, `decision` and `rating`. It does not write them.

The decision and the result are two ratings, not one. A good decision can
lose and a bad one can win, so neither is ever filled in from the other.

Anything outside the three status words (`off-track`, `drifting`, a blank)
shows on the radar as not set. The note is left as it is until the user sets one.

## Body

```
## Why

{{why}}

## Proved wrong if

{{wrong_if}}

## Value

{{value}}

## Notes
```

## Follow-ups

Each names the bet's owner:

- no owner: name one
- status is not one of the three: set in progress, paused, or done
- status is in progress and odds or wrong_if is blank: write both. Not asked
  once a bet is paused or done, because odds written after the result only
  record hindsight
- status is done and rating or decision is blank: rate whichever is missing,
  the result and the decision apart

## Radar

`bets/Bet Radar.md` groups bets into In progress, Paused, Done, and Not set.
Each row shows the owner, the odds, the decision, the rating, and the value.

Under that:

- **Decision against result.** Done bets with both ratings, in a grid of
  decision (good, bad) by result (won, push, lost): earned it, bad luck, got
  lucky, learn from it, and the two pushes.
- **Odds against results.** For done bets with odds and a won or lost result:
  the average odds and the share that won. Under 10 bets, the radar says the
  gap says little yet.
- **Follow-ups**, then two Dataview blocks: every bet with these fields, and
  done bets grouped by decision and result.
