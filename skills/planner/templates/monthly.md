---
tags:
  - monthly
month: <% tp.date.now("YYYY-MM") %>
month_start: <% moment().startOf("month").format("YYYY-MM-DD") %>
month_end: <% moment().endOf("month").format("YYYY-MM-DD") %>
---
# Monthly Review <% tp.date.now("YYYY-MM") %>

## Last Month

![[Monthly Review <% tp.date.now("YYYY-MM", "P-1M") %>#Next Month Priorities]]

---

## Weekly Goals This Month

```dataview
TASK
FROM "reviews/weekly"
WHERE file.name >= "Weekly Review <% moment().startOf("month").format("YYYY-[W]ww") %>"
AND file.name <= "Weekly Review <% moment().endOf("month").format("YYYY-[W]ww") %>"
```

---

## Scorecard

<!-- planner:month-scorecard -->
<!-- /planner:month-scorecard -->

---

## How the bets paid off

<!-- Decisions reviewed this month. verdict:: is yours: skill, luck, bad-call, bad-luck -->

```dataview
TABLE WITHOUT ID
  L.text AS Decision,
  L.confidence AS "Conf %",
  L.outcome AS Outcome,
  L.verdict AS Verdict
FROM "reviews/daily"
FLATTEN file.lists AS L
WHERE contains(L.tags, "#decision") AND L.review
  AND date(L.review) >= date(this.month_start) AND date(L.review) <= date(this.month_end)
SORT L.review ASC
```

---

## Active Bets

```dataview
TABLE status, target_date, owner
FROM "bets"
WHERE status = "active" OR status = "planning"
SORT target_date ASC
```

---

## What Moved This Month

<!-- 3-5 bullets — what actually shifted, shipped, or became clearer -->

-

<!-- planner:moved -->
<!-- /planner:moved -->

---

## What Stalled & Why

-

<!-- planner:stalled -->
<!-- /planner:stalled -->

---

## Next Month Priorities

- [ ]
- [ ]
- [ ]
