---
description: Track bets in the vault. Status is in progress, paused, or done. Rating is won, lost, or push. Both are set by the user.
---

Read the `bets` skill and its `references/bet-contract.md`. Then run the flow that fits.

Usage:
- `/bets` — rewrite the radar and summarize it by status
- `/bets backfill` — interview me about bets already made and create a note for each
- `/bets new` — draft a new bet with me, then create it
- `/bets life` — the radar for personal bets only (`--area life`)

If the vault has no `bets/` folder yet, the first `new` creates it.
