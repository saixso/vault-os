---
name: monthly-planner
description: >
  Month-end run for the planner's Obsidian monthly review. Rolls the daily and weekly
  notes up into a month scorecard (focus hit rate, promise follow-through,
  decision verdicts), lists what moved and what stalled, and lists the bets
  whose review dates fell in the month. Use for "monthly review", "how did my
  month go", or when a scheduled run names this skill.
---

# monthly-planner

Read `../planner/references/note-contract.md` first. `P` is the planner script, as in daily-planner.

Input: `MONTH_DAY`, any date in the month being closed (in the user's time zone).

## Steps

1. `P render monthly MONTH_DAY`.
2. `P stats <first day> <last day>` for the month, and the same for each week inside it.
3. Write `month-scorecard` with `P block-set`: a small table, one row per week, columns Focus %, Kept / due, Decisions, Meeting h; then one total line and the verdict counts (skill, luck, bad-luck, bad-call).
4. Write `moved` with `P block-set`: 3 to 5 lines drawn from the weekly notes' "What Got Done" and kept promises. One line each, own words.
5. Write `stalled` with `P block-set`: promises open more than 14 days and Focus items left unticked in 3 or more daily notes. One line each with how long it has been open.
6. Do not fill "Next Month Priorities"; that is the user's.
7. Commit only this note, message `planner: month YYYY-MM`. Push only where the run's instructions say to.
