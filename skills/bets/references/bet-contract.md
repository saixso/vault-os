# Bet contract

The shape of a bet note, the rules that score it, and who writes what. The
`bets` skill and `scripts/bets.py` follow this.

## Where notes live

- One note per bet: `bets/<Bet name>.md`. Characters Obsidian rejects in file
  names (`/ \ : * ? " < > | # ^ [ ]`) become spaces; the full name stays in
  the `bet` field and the heading.
- A note is a bet when its frontmatter has `type: bet`. Other notes in `bets/`
  are ignored.
- The radar is `bets/Bet Radar.md` (`type: bet-radar`), rewritten on every
  `score` run. Nobody edits it by hand.
- Template: the vault's `templates/bet.md` if it has one, else
  `skills/bets/templates/bet.md`. Placeholders are `{{field}}`; a vault's own
  template keeps `type: bet` and the section headings below.

## Frontmatter

| Field | Who | Meaning |
|---|---|---|
| `bet` | user | Name of the bet |
| `owner` | user | One person who answers for it. For a personal bet, the user |
| `area` | user | `work` or `life` |
| `cycle` | user | Cycle label, optional |
| `appetite` | user | Time budget in words ("6 weeks"), optional |
| `cycle_start`, `cycle_end` | user | `YYYY-MM-DD` |
| `started` | user | Date work started. Blank means not started, unless a milestone is ticked |
| `shipped` | user | Date it shipped |
| `dropped` | user | Date it was stopped |
| `outcome` | user | `hit`, `partial` or `missed`: the user's own call. Blank means the KPI decides |
| `source` | agent | `backfill` for notes made from memory |
| `status`, `status_reason`, `delivery`, `kpi_result`, `last_signal` | `bets.py score` | Overwritten on each run |

## Body lines

Each kind has its own section. `bets.py` appends to the right one.

```
## Milestones
- [ ] #milestone Pilot at 5 sites 📅 2026-12-04
- [x] #milestone Spec agreed 📅 2026-11-13 [done:: 2026-11-12]

## KPIs
- #kpi Repeat tickets per week [baseline:: 40] [target:: 25] [read_by:: 2027-01-15]

## Readings
- 2026-12-08 #reading Repeat tickets per week [value:: 32]

## Blockers
- [ ] #blocker Waiting on the vendor quote [opened:: 2026-11-20]

## Signals
- 2026-11-23 Pilot hardware arrived
- 2026-11-30 Install slipped a week #off-track
```

- Dates are `YYYY-MM-DD`. Milestone dates use the Obsidian Tasks `📅` format.
- `direction:: up|down` on a KPI is optional; without it, a target below the
  baseline means lower is better.
- A reading's metric must match a KPI line in the same note (case does not matter).
- `#off-track` and `#on-track` on a signal record the owner's own call.

## Status rules

Run on every bet that is not shipped, dropped or upcoming. The first rule that
matches sets the status and its reason.

| Status | When |
|---|---|
| off-track | The owner's latest call is `#off-track` |
| off-track | An open milestone's date has passed |
| off-track | The cycle has ended and it has not shipped |
| drifting | A blocker has been open `blocker_days` (7) or more |
| drifting | Work has not started and the next date (milestone or cycle end) is under `warn_days` (14) away |
| stalled | No owner |
| stalled | No signal for more than `stale_days` (7); with no signals, counted from `started` or `cycle_start` |
| on-track | None of the above |

Before the rules:

- `dropped` set: **dropped**.
- `shipped` set: **shipped**.
- `cycle_start` in the future and an owner named: **upcoming**.

Thresholds come from `bets/bets-config.json`
(`{"blocker_days": 7, "stale_days": 7, "warn_days": 14}`), and the flags
`--blocker-days`, `--stale-days`, `--warn-days` win over the file.

## Delivery and outcome

Delivery, from the dates:

| Delivery | When |
|---|---|
| on-time | `shipped` on or before `cycle_end` |
| late | `shipped` after `cycle_end` |
| not-shipped | `cycle_end` has passed, nothing shipped |
| dropped | `dropped` set |
| in-progress, upcoming | the cycle is running or has not started |

KPI result, from each KPI's latest reading:

| Result | When |
|---|---|
| hit | the reading reached the target |
| partial | it moved from the baseline toward the target but did not reach it |
| missed | it did not move past the baseline |
| not-read | no reading yet |

A bet with several KPIs is `hit` when every read KPI hit, `missed` when every
read KPI missed, and `partial` otherwise. The radar shows the user's `outcome`
when set, and the KPI result otherwise.

## Follow-ups

Each names the bet's owner, for the user to chase:

- no owner: name one;
- off track: agree a scope cut, a new date or a stop;
- a KPI whose `read_by` date has passed with no reading on or after it: get the reading;
- a blocker open `blocker_days` or more: ask what clears it;
- stalled with an owner: ask for an update.

Dropped bets get none. Shipped bets get only KPI readings.
