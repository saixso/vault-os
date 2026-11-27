---
name: daily-planner
description: >
  Evening run for the planner's Obsidian daily notes. Closes today (promises
  made, decisions made, promises kept, scorecard) and preps tomorrow (a prep card per
  meeting carried from past Wispr notes, promises due, bets due for review, carried Focus items).
  Reads Google Calendar, Wispr Flow meetings and Gmail. Use for "close my day",
  "prep tomorrow", "daily summary", or when a scheduled run names this skill.
---

# daily-planner

Read `../planner/references/note-contract.md`, `../planner/references/sources.md`, `../planner/references/meeting-prep.md`, `../planner/references/focus.md` and `../planner/references/ideas.md` first. They hold the write rules and the privacy rules.

`P` below means `python3 PLUGIN/scripts/planner.py --vault VAULT`, as `../planner/SKILL.md` defines them (`PLUGIN` is `${CLAUDE_PLUGIN_ROOT}` in Claude Code, or the vault-os checkout). Note paths given to `P` are relative to the vault.

Inputs: `TODAY` (a date in the user's time zone). `NEXT` is the next workday: Friday preps Monday.

## 1. Close today

1. `P render daily TODAY` (creates the note from `templates/daily.md` if missing; never overwrites).
2. Read today's counted calendar events, Wispr Flow meetings, and sent mail (see sources.md).
3. Read today's **Add here** and **My review** sections (`P my-review <today note>`); they are the user's and are never edited. Act on the review's "Notes for Claude" in this run and the next prep, and say in the report what you did with them.
4. Promises the user made today: write them with `P block-add <today note> promises`, one line each, in the contract format. Their own action items with no one waiting go to `P block-add <today note> todo` as `#todo` lines. Skip anything already in Add here. Give each a `⏳` day to work on it, a `📅` only when a deadline was said or implied, and an `[est:: ]` when it is easy to size. The Today query shows these by date; never copy them into Prep.
5. Decisions the user made today: `P block-add <today note> decisions`.
6. Open promises from earlier days (`P open-items TODAY`, plus undated ones): if today's sent mail or a meeting shows one done, tick it with `P tick <note where it lives> "text" --evidence "one line" --date TODAY`. If unsure, leave it.
7. For each meeting card: if notes or mail show the outcome was reached and the user hasn't ticked it, say so in the report; never tick `#outcome` yourself. Add the meeting's new promises and decisions as in steps 4 and 5.
8. Ideas: run the idea pass in `../planner/references/ideas.md` on today's meetings (link finder `PLUGIN/scripts/idea-links.py`, read-only), then write `P block-set <today note> ideas`, 3 to 5 lines. Skip it when the run's instructions name no ideas folder and the vault has no `ideas/`.
9. `P scorecard <today note> --meeting-hours H` (also counts meeting outcomes).

## 2. Prep NEXT

1. `P render daily NEXT`.
2. `P open-items NEXT` gives carried Focus items, promises due by NEXT (overdue first), to-dos happening within 3 days, Add here tasks with no date (`added_undated`), decisions whose review date has come, and the last note's My review (`my_review`).
3. Read NEXT's calendar. For each meeting, build a card as `../planner/references/meeting-prep.md` says: 3 lines, with the one question, what to bring, what is still open from the last one or two Wispr Flow instances of that series, and the `#outcome` box. Write all cards with `P block-set <NEXT note> meetings`. Optional meetings get one "skip?" line.
4. For each decision due for review, look for evidence in mail and meetings since it was made. Add a to-do to NEXT: `- [ ] #todo Review bet: <decision> ⏳ NEXT [src:: Decisions, <date>]`, and put the evidence line in the report.
5. Write the prep block with `P block-set <NEXT note> prep`: one line of 15 words or fewer, in this shape and nothing more:

```
Mon Nov 30 · 4 meetings, 2 h · open from 1:00
```

   Nothing else goes in Prep: the Today query shows what is due, and Focus shows what is first.
6. Fill Focus: `P focus-candidates NEXT`, rank as `focus.md` says (Eisenhower, Ivy Lee 3, the one thing first), then `P focus-fill <NEXT note>` with 3 short lines, each with `⏳ NEXT`. If it says "kept yours", leave Focus as it is. Give the why for each, and what ranked next, in the report.
7. Undated tasks in Add here: if the user's words or a source set a day, say it in the report and ask; never add a date to their line.

Rules for prep: keep to the word budgets in the note contract. Focus is written only through `focus-fill`.

## 3. Finish

- Commit only the notes you wrote (idea notes, aliases and Link Suggestions included), message `planner: close TODAY, prep NEXT`. If the run's instructions say idea notes go for review, put them on a branch instead and say so in the report. Push only where the run's own instructions say to.
- Report in two or three lines: counts written (idea notes created and updated, links, aliases), why each Focus item was picked, what you did with the My review notes, any source that was unreachable, anything skipped for privacy.
