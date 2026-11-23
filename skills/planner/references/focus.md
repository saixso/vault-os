# Focus: the top 3

The daily Focus is never left empty. The planner fills it in the evening prep (or on demand) while all three boxes are empty. Once the user writes or edits any of them, the planner leaves Focus alone.

## Candidates

`planner.py focus-candidates DATE` lists them with a first-cut rank:

- This week's goals (the ones the user wrote, or the suggested goals while none are written)
- Promises overdue or due that day
- `#todo` items overdue or due that day
- That day's open `#outcome` lines from the meeting cards
- Focus items left unticked the day before (`open-items` lists them as carried)

Add by judgment anything the sources show waiting only on the user today (a yes someone asked for, a reply that unblocks a team).

## Ranking

1. **Eisenhower.** Important first, then urgent. Important = tied to a week goal, or owed to a person. Urgent = overdue, due that day, or a meeting that day. The script's quadrants are a first cut; the agent makes the call.
2. **Ivy Lee.** Exactly 3, in order. Work them top to bottom.
3. **The one thing (Keller).** Item 1 is the one that makes the others easier, or matters most if nothing else gets done. Mark it `**The one thing:**`.

## Line format

```
- [ ] **The one thing:** what, as an action 📅 YYYY-MM-DD [why:: one line: what it unblocks or who waits]
- [ ] what 📅 YYYY-MM-DD [why:: ...]
- [ ] what 📅 YYYY-MM-DD [why:: ...]
```

The deadline is when it has to be done, not when it was first due. Overdue items get today's date, and the why says how late. What ranked 4th to 6th goes on one "Ranked next" line in Prep, nothing more.

Write with `planner.py focus-fill FILE` (stdin, 3 lines). It prints "kept yours" and changes nothing if Focus already has items.
