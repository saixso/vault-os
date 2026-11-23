---
description: Track bets in the vault (backfill, new bet, signals, KPI readings) and refresh the Bet Radar.
---

Read the `bets` skill and its `references/bet-contract.md`. Then run the flow that fits.

Usage:
- `/bets` — score every bet and summarize the radar: what needs attention, follow-ups by owner
- `/bets backfill` — interview me about bets already made and create a note for each
- `/bets new` — draft a new bet with me, then create it
- `/bets reading` — record a KPI reading
- `/bets life` — the radar for personal bets only (`--area life`)

If the vault has no `bets/` folder yet, the first `new` creates it.
