# Bets

One note per bet. The user sets the status, the odds they give the bet, what
would prove it wrong, and at the close two ratings kept apart: the decision
(good or bad) and the result (won, lost, or push). `scripts/bets.py` creates
the note and rewrites a Bet Radar grouped by status. It does not decide that a
bet is done, and it does not rate a decision or a result.

The odds and the two ratings follow Thinking in Bets: judge a decision on what
was known when it was made, not on how it turned out.

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
python3 scripts/bets.py set "Self-serve onboarding" status=done rating=lost decision=good
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
    "odds": 60,
    "wrong_if": "Days to first use is still above 4 after a full cycle.",
    "stake": "medium",
    "stake_note": "One cycle of two engineers.",
    "status": "in progress"
  }
]
```

Status is `in progress`, `paused`, or `done`. If `status` is left out, a new
note starts at `in progress`. Stake is `small`, `medium`, or `large`, with
`stake_note` for what would be lost. Odds is a whole percent from 0 to 100 (`60%` and
`0.6` become `60`). Decision is `good` or `bad`, and rating is `won`, `lost`,
or `push`; both stay blank until someone sets them. An existing note is never
overwritten by `new`.

`score` rewrites `bets/Bet Radar.md` and does not change any field on the notes. `--area life` limits the radar to personal bets. `--out NOTE`
writes it somewhere else.

## The radar note

Four groups: In progress, Paused, Done, Not set. Each row is the bet, the
owner, the odds, the stake, the decision, the rating, and the value.

- **Decision against result:** done bets in a grid of decision (good, bad) by
  result (won, push, lost). A good call that lost is bad luck; a bad call that
  won is luck, not a lesson to repeat.
- **Odds against results:** the average odds of done bets with a won or lost
  result, against how many won. Odds well above the win rate means the bets
  were called with too much confidence.
- **Results by stake:** win rate and average odds for small, medium and large
  bets, so big bets are judged apart from small ones.
- **Follow-ups:** a missing owner or status; odds, "proved wrong if" or the
  stake on a bet in progress; a decision or result rating on a bet marked done.
- **Live view:** two Dataview blocks with the same fields.

## Test

```
make test-bets
```

Hermetic: builds a temp vault from the starter template with fake bets.
