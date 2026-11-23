---
tags:
  - daily
status: active
created: <% tp.date.now("YYYY-MM-DD") %>
publish: false
focus_done:
focus_total:
promises_made:
promises_due:
promises_kept:
decisions_logged:
meeting_hours:
carried:
outcomes_hit:
outcomes_total:
---
<% await tp.file.move("/reviews/daily/" + tp.file.title) %>
# <% tp.date.now("dddd, MMMM D, YYYY", 0, tp.file.title) %>

## Direction

![[Weekly Review <% tp.date.now("YYYY", 0, tp.file.title) %>-W<% tp.date.now("ww", 0, tp.file.title) %>#<% tp.date.now("YYYY", 0, tp.file.title) %>-W<% tp.date.now("ww", 0, tp.file.title) %> Goals]]

---

## Due

<!-- Open to-dos and promises from the daily notes: overdue first, then the next 3 days, with a countdown. -->
```tasks
not done
path includes reviews/daily
(tags include #todo) OR (tags include #promise)
filter by function task.due.moment?.isSameOrBefore(moment().add(3, 'days'), 'day') ?? false
group by function task.due.category.groupText
group by function task.due.category.name === 'Today' ? '' : task.due.fromNow.groupText
sort by due
short mode
```

---

## Prep

<!-- planner:prep -->
<!-- /planner:prep -->

---

## Meetings

<!-- One card per meeting you're needed in. Purpose, Outcome, type (inform, discuss or decide, and who decides),
the one question to get answered, and what's still open from last time.
After it: tick #outcome if you got the outcome, then add any new promises or decisions below. -->
<!-- planner:meetings -->
<!-- /planner:meetings -->

---

## Focus

<!-- Top 3 in order; #1 is the one thing. The planner fills these only while all three are empty, so anything you write stays. -->
<!-- planner:focus -->
- [ ]
- [ ]
- [ ]
<!-- /planner:focus -->

---

## Log



---

## To-dos

<!-- One line each: - [ ] #todo what 📅 YYYY-MM-DD [est:: 30m] [src:: where]. Add your own below the block. -->
<!-- planner:todo -->
<!-- /planner:todo -->

---

## Promises

<!-- One line each: - [ ] #promise what [to:: who] 📅 YYYY-MM-DD [src:: where] -->
<!-- planner:promises -->
<!-- /planner:promises -->

---

## Decisions

<!-- One line each: - #decision what [expect:: outcome you bet on] [confidence:: 0-100] [review:: YYYY-MM-DD] [src:: where] -->
<!-- planner:decisions -->
<!-- /planner:decisions -->

---

## Done

-

---

## Scorecard

<!-- planner:scorecard -->
<!-- /planner:scorecard -->

---

## Notes

-
