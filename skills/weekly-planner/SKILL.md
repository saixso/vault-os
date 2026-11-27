---
name: weekly-planner
description: >
  Sunday-evening run for the planner's Obsidian weekly review. Summarizes last week from
  the daily scorecards, the Tasks done dates and the user's own day reviews (done,
  came due and still open, focus hit rate, promises kept and missed, decisions,
  day ratings) and sets up the coming week (meetings by day with clashes,
  promises due, bets due for review, up to three suggested goals). Use for
  "weekly summary", "plan my week", or when a scheduled run names this skill.
---

# weekly-planner

Read `../planner/references/note-contract.md`, `../planner/references/sources.md` and `../planner/references/ideas.md` first. `P` is the planner script, as in daily-planner.

Input: `SUNDAY`, the Sunday that starts the coming week (in the user's time zone). Last week is the seven days before it.

## Steps

1. `P render weekly SUNDAY`. If the note exists, keep everything the user wrote.
2. `P stats <SUNDAY-7> <SUNDAY-1>` for last week's numbers, including `meeting_outcome_rate_pct` (meetings that got their outcome).
3. `P week-review <SUNDAY-7> <SUNDAY-1>`: everything done last week by its `✅` date (anywhere in the vault but templates), boxes ticked in last week's daily notes with no done date, tasks that came due and are still open, the count of open tasks dated more than two weeks before the week, and each day's My review (rating, what the user saw, notes for Claude).
4. Write `last-week` with `P block-set <note> last-week`, at most 6 lines:

```
- Done 23 (4 ticked with no date). Came due and still open 3: vendor record (Jordan), budget sheet (Kim), room booking.
- Focus 9/15 (60%). Promises kept 7/10 due. Decisions logged 4; reviewed 1: pilot option B, verdict skill.
- Your days: 4, 3, 2, 4, 5 (avg 3.6). Your notes: keep Mondays light; Brandon first.
- Meetings 21 h over 5 days; the 2-rated day had 6 h of meetings. (inferred)
- 108 open tasks are dated more than two weeks back. Re-date or drop them?
```

   The ratings line uses the user's own scores and a few words from their notes, nothing else of what they wrote. The pattern line is one observed pattern, marked `(inferred)`; leave it out if nothing stands out. The stale line appears only when the count is above zero. Act on the notes for Claude in the week ahead.

5. Read the coming week's calendar (Mon to Fri), open promises and to-dos (`P open-items <SATURDAY>`), and decisions due for review. Write `week-ahead` with `P block-set`. It is not a meeting list; each day's meetings go in that day's note. Use this shape, at most about 20 lines:

```
**Turns on**
1. Vendor decision record. Owed to Jordan since Nov 13; Tuesday's 1:1 is the one slot.
**Risks, and the move**
- Thursday planning call: 4 of 6 declined. Cancel it or make it async.
- Friday 1:1 invite still unanswered and overlaps the optional demo. Answer it today.
**Owed**
- You owe: Jordan (decision record, 10 days late), Kim (budget sheet, no date).
- Owed to you: Sam (draft labels, since Nov 13).
**Time**
<output of P time-strip>
**Bets due**
- None this week. Pilot option B comes up Dec 11.
**Pattern** (inferred)
- Mon and Tue hold most of the meeting hours; Wednesday from 11:30 is the longest open block.
```

   - Turns on: up to 3 items, each with why this week. Draw from overdue promises, goals, and meetings where a decision gets made.
   - Risks: absences, declines, clashes, holidays and unanswered invites. Each gets one move that clears it.
   - Time: build the JSON for `P time-strip` from counted events only (accepted or organized, plus unanswered ones; not declined, not 1:1s the other person declined, not reminders). Add `"note"` for a holiday.
   - Owed to you: only what someone said they would do for the user, with the date they said it.
   - Write any new to-do that comes out of a risk (answer an invite, cancel a meeting) into Monday's daily note with `P block-add <monday note> todo`, with a `⏳` day and a `📅` only for a real deadline.

6. Write `suggested-goals` with `P block-set`: up to 3 lines, each starting `Suggestion:` and tied to a due promise, a bet to review, or last week's "highest-leverage" answer. Never fill the Goals checkboxes; those are the user's.
7. Write `ideas-moved` with `P block-set <note> ideas-moved`, in the shape `ideas.md` gives: ideas moved last week, new ones, ones untouched 14+ days, and a link map of last week's new links (12 nodes at most). Leave it empty when the vault has no ideas folder.
8. Commit only this note, message `planner: week YYYY-Www`. Push only where the run's instructions say to. Report counts and any unreachable source.
