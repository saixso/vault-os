# Bets

Track the bets a team or a person commits to for a cycle: a Shape Up bet from
the betting table, a quarter goal, a personal project. Each bet is one note
with an owner, milestones, a KPI and a dated log of signals. `scripts/bets.py`
scores every bet by fixed rules and writes a Bet Radar note: what is on track,
what needs attention and why, follow-ups per owner, and a scorecard of delivery
against outcome.

The agent does the talking (backfill interviews, drafting new bets, turning an
update into a signal). The script does everything that must give the same
answer twice: note format, status, delivery, KPI result, follow-ups.

| Part | Path |
|---|---|
| Skill | `skills/bets/SKILL.md` (flows: backfill, new bet, record, KPI reading, radar) |
| Contract | `skills/bets/references/bet-contract.md` (note shape, status rules, who writes what) |
| Template | `skills/bets/templates/bet.md` |
| Script | `scripts/bets.py` (standard library only) |
| Command | `/bets` |
| Tests | `tests/test_bets.py`, `make test-bets` |

The planner's "Did the bet pay off?" lines are single decisions with a review
date. `bets` is for work that runs over a cycle. The rule engine in `bets.py`
(`evaluate()` over an ordered list of rules) is written so decision notes can
reuse it with their own rules.

## Run it locally

From a checkout of vault-os, against your vault:

```
export VAULT_OS_VAULT_ROOT=/path/to/your/vault
python3 scripts/bets.py new < my-bets.json      # create notes (one object or a list)
python3 scripts/bets.py score                   # status fields + bets/Bet Radar.md
python3 scripts/bets.py follow-ups              # JSON: asks per owner
```

In Claude Code or Cursor with the plugin installed, ask "backfill our bets" or
run `/bets backfill`, and the skill interviews you and calls the script.

A minimal `my-bets.json`:

```json
[
  {
    "bet": "Self-serve onboarding",
    "owner": "Sam",
    "area": "work",
    "cycle": "Cycle 6",
    "cycle_start": "2026-11-02",
    "cycle_end": "2026-12-11",
    "problem": "New accounts wait days for a setup call.",
    "milestones": [{"text": "Pilot with 5 accounts", "due": "2026-11-27"}],
    "kpis": [{"metric": "Days to first use", "baseline": "6", "target": "1", "read_by": "2027-01-15"}],
    "signals": [{"date": "2026-11-20", "text": "Pilot accounts picked"}]
  }
]
```

Other fields: `appetite`, `started`, `shipped`, `dropped`, `outcome`
(`hit|partial|missed`), `source`, `readings` (`[{"date", "kpi", "value"}]`),
`blockers` (`[{"text", "opened"}]`). An existing note is never overwritten.

## Day to day

```
python3 scripts/bets.py signal "Self-serve onboarding" "Pilot slipped a week" --call off-track
python3 scripts/bets.py blocker "Self-serve onboarding" "Waiting on billing access"
python3 scripts/bets.py tick "Self-serve onboarding" "billing access"
python3 scripts/bets.py reading "Self-serve onboarding" "Days to first use" 2
python3 scripts/bets.py set "Self-serve onboarding" shipped=2026-12-10
python3 scripts/bets.py score --today 2026-12-14
```

`--date` sets the day on signals, blockers, readings and ticks (default today).
`score --area life` limits the radar to personal bets; `--out NOTE` writes it
somewhere else.

## Status rules

First match wins. Shipped, dropped and upcoming bets skip the rules.

| Status | When |
|---|---|
| off track | owner's latest call is `#off-track`; an open milestone's date passed; cycle ended without shipping |
| drifting | a blocker open 7 days or more; work not started and the next date under 14 days away |
| stalled | no owner; no signal for more than 7 days |
| on track | none of the above |

Change the day counts in `bets/bets-config.json`:

```json
{"blocker_days": 7, "stale_days": 7, "warn_days": 14}
```

or per run with `--blocker-days`, `--stale-days`, `--warn-days`.

## The radar note

`bets/Bet Radar.md` has five parts:

1. **Needs attention:** off track, drifting and stalled bets, with the reason.
2. **Follow-ups:** grouped by owner (missing KPI readings, blockers, updates, scope calls).
3. **Active bets:** owner, area, cycle end, next date, status, last signal.
4. **Scorecard:** finished bets in a delivery by outcome grid (shipped on time, late,
   not shipped, dropped; against hit, partial, missed, not read), then one row per bet.
5. **Live view:** a Dataview table over the status fields, for sorting and filtering in Obsidian.

The tables are plain Markdown, so the radar reads the same on GitHub or without
Dataview.

## Requirements

- Python 3, standard library only.
- In the vault: Dataview for the live view (optional) and Tasks if you want the
  `📅` milestone dates in Tasks queries (optional).

## Test

```
make test-bets
```

Hermetic: builds a temp vault from the starter template with fake bets.
