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

Read `../planner/references/note-contract.md`, `../planner/references/sources.md`, `../planner/references/meeting-prep.md` and `../planner/references/focus.md` first. They hold the write rules and the privacy rules.

`P` below means `python3 PLUGIN/scripts/planner.py --vault VAULT`, as `../planner/SKILL.md` defines them (`PLUGIN` is `${CLAUDE_PLUGIN_ROOT}` in Claude Code, or the vault-os checkout). Note paths given to `P` are relative to the vault.

Inputs: `TODAY` (a date in the user's time zone). `NEXT` is the next workday: Friday preps Monday.

## 1. Close today

1. `P render daily TODAY` (creates the note from `templates/daily.md` if missing; never overwrites).
2. Read today's counted calendar events, Wispr Flow meetings, and sent mail (see sources.md).
3. Promises the user made today: write them with `P block-add <today note> promises`, one line each, in the contract format. Their own action items with no one waiting go to `P block-add <today note> todo` as `#todo` lines. Give each a `📅` date when one was said or implied, and an `[est:: ]` when it is easy to size. The note's Due section groups and counts these down by itself; do not copy them into Prep.
4. Decisions the user made today: `P block-add <today note> decisions`.
5. Open promises from earlier days (`P open-items TODAY`, plus undated ones): if today's sent mail or a meeting shows one done, tick it in the note where it lives and add `[evidence:: ...]`. If unsure, leave it.
6. For each meeting card: if notes or mail show the outcome was reached and the user hasn't ticked it, say so in the report; never tick `#outcome` yourself. Add the meeting's new promises and decisions as in steps 3 and 4.
7. `P scorecard <today note> --meeting-hours H` (also counts meeting outcomes).

## 2. Prep NEXT

1. `P render daily NEXT`.
2. `P open-items NEXT` gives carried Focus items, promises due by NEXT (overdue first), to-dos due within 3 days, and decisions whose review date has come.
3. Read NEXT's calendar. For each meeting, build a card as `../planner/references/meeting-prep.md` says: purpose and outcome, type and who decides, the one question, and what is still open from the last one or two Wispr Flow instances of that series (plus promises to those people and their open asks in mail). Write all cards with `P block-set <NEXT note> meetings`. Optional meetings get one "skip?" line.
4. For each decision due for review, look for evidence in mail and meetings since it was made. One line of evidence, or "no evidence yet".
5. Write the prep block with `P block-set <NEXT note> prep`, in this shape and nothing more:

```
**Today:** 3 meetings you need, 1.5 h, open from 11:00 to 3:00. Cards are under Meetings.
**Due**
- Send Alex the draft plan (to Alex, due Nov 24, from [[2026-11-20]]): in the Due list; listed here only because the 8:00 1:1 needs it
**Did the bet pay off?**
- Pilot option B first (Nov 24, 60%): expected fewer repeat tickets. Evidence: no data yet.
**Carried**
- Call the vendor
**Ranked next** (after the top 3): call the vendor, book the offsite room.
```

6. Fill Focus: `P focus-candidates NEXT`, rank as `focus.md` says (Eisenhower, Ivy Lee 3, the one thing first, each with a why and a 📅 deadline), then `P focus-fill <NEXT note>`. If it says "kept yours", leave Focus as it is.

Rules for prep: empty sections are left out, and the whole block stays under about 15 lines. Focus is written only through `focus-fill`.

## 3. Finish

- Commit only the notes you wrote, message `planner: close TODAY, prep NEXT`. Push only where the run's own instructions say to.
- Report in two or three lines: counts written, any source that was unreachable, anything skipped for privacy.
