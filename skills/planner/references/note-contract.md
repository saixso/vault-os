# Note contract

What the planner may write, and in what shape. Every skill follows this.

## Ownership

- The user owns everything outside a planner block. Never edit Log, Done, Notes, Goals, or any line they wrote.
- The planner writes only between `<!-- planner:NAME -->` and `<!-- /planner:NAME -->`.
- Write blocks only through `scripts/planner.py` (`block-set` replaces a block, `block-add` appends lines that are not already in the note). Never hand-edit a block.
- Exception: ticking a `#promise` box. Allowed only with clear evidence (a sent mail or a meeting where it was done), and the line gets `[evidence:: one line]` so the user can see why.

## Blocks

| Note | Block | Written by | How |
|---|---|---|---|
| daily | `prep` | daily-planner, evening before | block-set |
| daily | `focus` | daily-planner, evening before, only while all 3 boxes are empty (see focus.md) | focus-fill |
| daily | `meetings` | daily-planner, evening before (see meeting-prep.md) | block-set |
| daily | `todo` | daily-planner, same evening | block-add |
| daily | `promises` | daily-planner, same evening | block-add |
| daily | `decisions` | daily-planner, same evening | block-add |
| daily | `scorecard` | `planner.py scorecard` | automatic |
| weekly | `last-week`, `suggested-goals`, `week-ahead` | weekly-planner | block-set |
| monthly | `month-scorecard`, `moved`, `stalled` | monthly-planner | block-set |

## Line formats

Due dates use the Obsidian Tasks emoji format the vault already uses, `📅 YYYY-MM-DD`, so the Tasks "Due" queries in the daily and weekly notes can group and count down. Dataview reads the same date as `due`. Other fields are Dataview inline fields. Older lines with `[due:: ]` still count.

To-do the user owns, with no one waiting on it, filed on the day it came up:

```
- [ ] #todo Answer the Friday 1:1 invite 📅 2026-11-24 [est:: 5m] [src:: Calendar, Nov 23]
- [ ] #outcome Vendor picked [mtg:: Sam 1:1]   (one per meeting card; only the user ticks it)
```

- `📅` only when a date was said, plainly implied, or set by a meeting it must happen before (then say which in `src`). Otherwise leave it out; it lands under Undated, which asks the user for a date.
- `est` is optional, a rough time like `15m` or `2h`, only when the work is clear enough to size.

Promise the user made, filed on the day it was made:

```
- [ ] #promise Send the vendor the pilot results [to:: Alex Rivera] 📅 2026-11-27 [src:: Pilot sync, Nov 24]
```

- `to` is who is owed. `📅` only when a date was said or plainly implied ("by Friday"); otherwise leave it out.
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

## Daily frontmatter numbers

Set only by `planner.py scorecard`: `focus_done`, `focus_total`, `promises_made`, `promises_due`, `promises_kept`, `decisions_logged`, `meeting_hours`, `carried`, `outcomes_hit`, `outcomes_total`. The weekly and monthly Dataview tables read these.

## Weeks

Week names follow Obsidian's Periodic Notes format `YYYY-[W]ww` (moment "en": weeks start Sunday, week 1 holds Jan 1). `planner.py paths DATE` gives the right file names; never compute them by hand.
