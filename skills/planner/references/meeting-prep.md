# Meeting prep

Goal: the user walks into every meeting knowing why they're there, what "done" looks like, and the one question they need answered. The cards go in the daily note's `meetings` block. After each meeting they tick one box, and that feeds the scorecard.

## Which meetings get a card

- A card for every meeting where the user is a required attendee or the organizer.
- Optional, large-audience or status-only meetings get one line: what it covers and "optional, skip?".
- A cancelled meeting gets one line saying it's cancelled, so the day reads true.
- Focus blocks, out-of-office and holds get nothing.

## The card (3 to 5 lines, never more)

```
**10:30 Sam 1:1** · discuss, you decide
- **Purpose:** why the meeting exists today. **Outcome:** what is true when it ends.
- **From Nov 6:** decisions made last time, and who still owes what.
- **Ask:** "the one question they must get answered"
- [ ] #outcome the outcome, in a few words [mtg:: Sam 1:1]
```

Header: time (ET), the meeting's plain name, its type, and who decides.

The frameworks, in the order they're used:

1. **Purpose and Outcome** (from POP: Purpose, Outcome, Process). The purpose says why now. The outcome is a state you can check: "a date for the write-up", not "discuss the write-up". Process stays out unless the user runs the meeting and it matters.
2. **Type:** inform, discuss or decide. For a decide, name who decides (DACI: Driver, Approver, Contributors, Informed), only the decider in the header.
3. **The one question.** If they leave with only one answer, this is it. Quote it as they would ask it.
4. **Open loops from last time.** For a recurring meeting, read the last one or two instances in Wispr Flow (`search_meetings` by title, sorted by start, then `list_meeting_series` and `get_meeting`). Carry forward their decisions, open action items and who owes what, in your own words. Check mail and the vault for which of those are done since.
5. **Bring:** only when there's news since last time that changes the conversation.

When there is no history (a first meeting, or no Wispr notes) and no agenda, say so, and make the card's ask "find out what they need before it starts".

## After the meeting

- Tick `#outcome` if they got the outcome. Leave it open if not.
- New promises go in the Promises block, decisions in the Decisions block, as usual. The evening run adds any they didn't.
- `planner.py scorecard` counts `outcomes_hit / outcomes_total` into the frontmatter and the scorecard line. `planner.py stats` gives `meeting_outcome_rate_pct` for the week and month.

## Privacy

Summaries only, in your own words. No transcript text, no quotes from other people, no share links, nothing about anyone's performance, health or private life. Name the topic ("the review you said you'd send"), not the detail.
