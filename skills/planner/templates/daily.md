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

<!-- planner:prep -->
<!-- /planner:prep -->

## Focus

<!-- planner:focus -->
- [ ]
- [ ]
- [ ]
<!-- /planner:focus -->

---

## Today

```tasks
not done
path includes reviews/daily
happens after <% tp.date.now("YYYY-MM-DD", -15, tp.file.title) %>
happens before <% tp.date.now("YYYY-MM-DD", 4, tp.file.title) %>
tags do not include #outcome
filter by function task.heading !== 'Focus'
group by function task.happens.category.groupText
sort by happens
short mode
limit 15
```

---

## Meetings

<!-- planner:meetings -->
<!-- /planner:meetings -->

---

## Add here

- [ ]

---

## Ideas

<!-- planner:ideas -->
<!-- /planner:ideas -->

---

## My review

Day rating:
What I saw in reality:
Notes for Claude:

---

## Record

### To-dos

<!-- planner:todo -->
<!-- /planner:todo -->

### Promises

<!-- planner:promises -->
<!-- /planner:promises -->

### Decisions

<!-- planner:decisions -->
<!-- /planner:decisions -->

### Scorecard

<!-- planner:scorecard -->
<!-- /planner:scorecard -->
