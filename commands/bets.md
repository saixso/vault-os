---
description: Track bets in the vault. Status is in progress, paused, or done. Odds and what would prove it wrong are written when the bet is placed. At the close the decision (good, bad) and the result (won, lost, push) are rated apart. The user sets all of them.
---

Read the `bets` skill and its `references/bet-contract.md`. Then run the flow that fits.

Usage:
- `/bets` — rewrite the radar and summarize it by status
- `/bets backfill` — interview me about bets already made and create a note for each
- `/bets new` — ask me about the bet one question at a time (what, owner, why, expected value, odds, what would prove it wrong), then write my answers to a new note
- `/bets close` — ask me one question at a time to close a bet: the result (won, lost, push), then the decision (good, bad) apart from the result, and write my answers to the note
- `/bets life` — the radar for personal bets only (`--area life`)

If the vault has no `bets/` folder yet, the first `new` creates it.
