# Bets

One note per bet. The user sets the status and the rating. `scripts/bets.py`
creates the note and rewrites a Bet Radar grouped by status. It does not
decide that a bet is done, and it does not rate one.

| Part | Path |
|---|---|
| Skill | `skills/bets/SKILL.md` |
| Contract | `skills/bets/references/bet-contract.md` |
| Template | `skills/bets/templates/bet.md` |
| Script | `scripts/bets.py` (standard library only) |
| Command | `/bets` |
| Tests | `tests/test_bets.py`, `make test-bets` |

## Run it locally

```
export VAULT_OS_VAULT_ROOT=/path/to/your/vault
python3 scripts/bets.py new < my-bets.json
python3 scripts/bets.py set "Self-serve onboarding" status=done rating=won
python3 scripts/bets.py score
```

A minimal `my-bets.json`:

```json
[
  {
    "bet": "Self-serve onboarding",
    "owner": "Sam",
    "area": "work",
    "why": "New accounts wait days for a setup call.",
    "value": "Days to first use, from 6.",
    "status": "in progress"
  }
]
```

Status is `in progress`, `paused`, or `done`. If `status` is left out, a new
note starts at `in progress`. Rating is `won`, `lost`, or `push`, and it stays
blank until someone sets it. An existing note is never overwritten by `new`.

`score` rewrites `bets/Bet Radar.md` and does not change the status or rating
on the notes. `--area life` limits the radar to personal bets. `--out NOTE`
writes it somewhere else.

## The radar note

Four groups: In progress, Paused, Done, Not set. Each row is the bet, the
owner, the rating, and the value. Follow-ups ask for a missing owner, a
missing status, or a rating on a bet the user has marked done.

## Test

```
make test-bets
```

Hermetic: builds a temp vault from the starter template with fake bets.
