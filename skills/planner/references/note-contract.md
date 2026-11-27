# Note contract

What the planner may write, and in what shape. Every skill follows this.

## Ownership

- The user owns everything outside a planner block. Never edit Add here, My review, Goals, or any line they wrote.
- The planner writes only between `<!-- planner:NAME -->` and `<!-- /planner:NAME -->`.
- **Add here** is the one place the user and other agents add tasks during the day, in the line format below. The planner reads it and never edits it; its untagged tasks count as to-dos.
- **My review** is the user's own: a day rating in their words, what they saw in reality, notes for Claude. The planner never writes there. The next daily run reads it (`P open-items` gives it as `my_review`) and acts on the notes; the weekly run sums it up (`P week-review`).
- Write blocks only through `scripts/planner.py` (`block-set` replaces a block, `block-add` appends lines that are not already in the note). Never hand-edit a block.
- Exception: ticking a `#promise` box. Allowed only with clear evidence (a sent mail or a meeting where it was done), and only with `P tick FILE "text" --evidence "one line" --date DAY`. It adds `[evidence:: ]` so the user can see why, and the `✅ DAY` done date the Tasks plugin would add, so the weekly review counts it.
- Exception: the idea pass (`ideas.md`) may create and update notes in the ideas folder, add an `aliases:` entry to an existing note (capped per run, never under `wiki/`), add an `ideas:` entry to a problem note, and append checkboxes to Link Suggestions. Nothing else outside a block.

## Blocks

| Note | Block | Written by | How |
|---|---|---|---|
| daily | `prep` | daily-planner, evening before: one header line under the title | block-set |
| daily | `focus` | daily-planner, evening before, only while all 3 boxes are empty (see focus.md) | focus-fill |
| daily | `meetings` | daily-planner, evening before (see meeting-prep.md) | block-set |
| daily | `todo` | daily-planner, same evening | block-add |
| daily | `promises` | daily-planner, same evening | block-add |
| daily | `decisions` | daily-planner, same evening | block-add |
| daily | `ideas` | daily-planner, same evening, 3 to 5 lines (see ideas.md) | block-set |
| daily | `scorecard` | `planner.py scorecard` | automatic |
| weekly | `last-week`, `suggested-goals`, `week-ahead` | weekly-planner | block-set |
| weekly | `ideas-moved` | weekly-planner: ideas moved, new, untouched 14+ days, link map (see ideas.md) | block-set |
| monthly | `month-scorecard`, `moved`, `stalled` | monthly-planner | block-set |

## Word budgets

The note is for working from, not reading. Keep to these:

| Part | Budget |
|---|---|
| Prep header line | 15 words: day, meetings, hours, open block |
| Focus line | 10 words before its dates, no why text (reasons go in the run's report) |
| Meeting card | 3 lines, 30 words (see meeting-prep.md) |
| Task line | 10 words before its dates and fields |
| Ideas block | 3 to 5 lines |

No prose lists of what is due or carried: the Today query shows overdue, today and the next 3 days by itself, and an open task stays there until it is ticked. Templates hold no instruction comments; the rules live here.

## Line formats

Dates use the Obsidian Tasks emoji format: `⏳ YYYY-MM-DD` is the day to work on it (scheduled), `📅 YYYY-MM-DD` is the deadline (due), `✅ YYYY-MM-DD` is the day it was done. The daily Today query shows a task on the earlier of ⏳ and 📅, so **every to-do, promise and Focus line the planner writes gets a ⏳**: the day it should be worked on. Add 📅 only when there is a real deadline. Dataview reads the same dates as `scheduled`, `due` and `completion`. Other fields are Dataview inline fields. Older lines with `[due:: ]` still count.

Add here line, for the user and any other agent:

```
- [ ] Draft January install announcement ⏳ 2026-11-30 📅 2026-12-02
- [ ] #promise Send Brandon the hardware doc [to:: Brandon] ⏳ 2026-11-27
```

An agent other than the planner that adds a task during the day writes it here, never inside a planner block.

To-do the user owns, with no one waiting on it, filed on the day it came up:

```
- [ ] #todo Answer the Friday 1:1 invite ⏳ 2026-11-24 [est:: 5m] [src:: Calendar, Nov 23]
- [ ] #outcome Vendor picked [mtg:: Sam 1:1]   (one per meeting card; only the user ticks it)
```

- `⏳` always: the day to work on it, at the latest the day before any `📅`. When nothing sets the day, use the next workday.
- `📅` only when a date was said, plainly implied, or set by a meeting it must happen before (then say which in `src`).
- `est` is optional, a rough time like `15m` or `2h`, only when the work is clear enough to size.

Promise the user made, filed on the day it was made:

```
- [ ] #promise Send the vendor the pilot results [to:: Alex Rivera] ⏳ 2026-11-26 📅 2026-11-27 [src:: Pilot sync, Nov 24]
```

- `to` is who is owed. `⏳` always, as for to-dos. `📅` only when a date was said or plainly implied ("by Friday").
- `src` names the meeting or mail thread by title and date, never a link or message id.

Decision the user made or owns, filed on the day it was made:

```
- #decision Pilot option B before option A [expect:: fewer repeat tickets by January] [confidence:: 60] [review:: 2026-12-24] [src:: Team sync, Nov 24]
```

- `expect` is the outcome being bet on, in plain words. If nobody said it, write `[expect:: ?]` and let the user fill it.
- `confidence` only when the user gave one. Do not invent a number.
- `review` defaults to 30 days after the decision unless the meeting named a date.
- At review, the planner may add `[evidence:: what happened]`. Only the user adds `[outcome:: ]` and `[verdict:: skill | luck | bad-luck | bad-call]`.

Verdict meanings (Thinking in Bets: judge the decision apart from the result):

| | Good result | Bad result |
|---|---|---|
| Sound decision | skill | bad-luck |
| Poor decision | luck | bad-call |

Idea line in the daily `ideas` block, one per idea that moved today:

```
- [[Idea - Alert sites before devices fail]] new, seed: draft alert rules owed (5 links)
- Weekly firmware pilot ring: first mention, no note yet
```

- Link the idea note when there is one; plain text when it is a first mention.
- After the name: what changed (new, or old stage → new stage) and 15 words or fewer on what moved.

## Daily frontmatter numbers

Set only by `planner.py scorecard`: `focus_done`, `focus_total`, `promises_made`, `promises_due`, `promises_kept`, `decisions_logged`, `meeting_hours`, `carried`, `outcomes_hit`, `outcomes_total`. The weekly and monthly Dataview tables read these.

## Weeks

Week names follow Obsidian's Periodic Notes format `YYYY-[W]ww` (moment "en": weeks start Sunday, week 1 holds Jan 1). `planner.py paths DATE` gives the right file names; never compute them by hand.
