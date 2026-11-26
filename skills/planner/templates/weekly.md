---
tags:
  - weekly
week: <% tp.date.now("YYYY") %>-W<% tp.date.now("ww") %>
week_start: <% moment().startOf("week").format("YYYY-MM-DD") %>
week_end: <% moment().endOf("week").format("YYYY-MM-DD") %>
---
# Weekly Review <% tp.date.now("YYYY") %>-W<% tp.date.now("ww") %>

## Last Week

![[Weekly Review <% tp.date.now("YYYY", -7) %>-W<% tp.date.now("ww", -7) %>#<% tp.date.now("YYYY", -7) %>-W<% tp.date.now("ww", -7) %> Goals]]

<!-- planner:last-week -->
<!-- /planner:last-week -->

---

## <% tp.date.now("YYYY") %>-W<% tp.date.now("ww") %> Goals

- [ ]
- [ ]
- [ ]

<!-- planner:suggested-goals -->
<!-- /planner:suggested-goals -->

---

## Due

<!-- Every open to-do and promise in the daily notes: overdue, today, coming up with a countdown, then undated ones that need a date. -->
```tasks
not done
path includes reviews/daily
(tags include #todo) OR (tags include #promise)
group by function task.due.category.groupText
group by function task.due.category.name === 'Today' ? '' : task.due.fromNow.groupText
sort by due
short mode
```

---

## This week

<!-- planner:week-ahead -->
<!-- /planner:week-ahead -->

---

## Ideas moved

<!-- Ideas that moved, new ones, ones untouched for 14+ days, and a map of this week's new links. -->
<!-- planner:ideas-moved -->
<!-- /planner:ideas-moved -->

---

## Scorecard

```dataview
TABLE WITHOUT ID
  file.link AS Day,
  choice(focus_total, focus_done + "/" + focus_total, "-") AS "Focus",
  meeting_hours AS "Meeting h",
  promises_made AS "Promised",
  choice(promises_due, promises_kept + "/" + promises_due, "-") AS "Kept / due",
  decisions_logged AS "Decisions",
  carried AS "Carried"
FROM "reviews/daily"
WHERE file.day >= date(this.week_start) AND file.day <= date(this.week_end)
SORT file.day ASC
```

---

## Promises

### Kept this week

```dataview
TASK
FROM "reviews/daily"
WHERE contains(tags, "#promise") AND completed
  AND due >= date(this.week_start) AND due <= date(this.week_end)
```

---

## Decisions

### Made this week

```dataview
LIST WITHOUT ID L.text
FROM "reviews/daily"
FLATTEN file.lists AS L
WHERE contains(L.tags, "#decision")
  AND file.day >= date(this.week_start) AND file.day <= date(this.week_end)
```

### Due for review

```dataview
LIST WITHOUT ID L.text
FROM "reviews/daily"
FLATTEN file.lists AS L
WHERE contains(L.tags, "#decision") AND L.review AND !L.verdict
  AND date(L.review) <= date(this.week_end)
SORT L.review ASC
```

---

## What Got Done

<!-- Brief summary of the week — don't embed, just write it -->

-

---

## Week Recap

```dataviewjs
const start = dv.date("<% moment().startOf('week').format('YYYY-MM-DD') %>");
const end = dv.date("<% moment().endOf('week').format('YYYY-MM-DD') %>");

const pages = dv.pages('"reviews/daily"')
  .where(p => p.file.day >= start && p.file.day <= end);

async function collect(tag) {
  let results = [];
  for (let page of pages) {
    const content = await dv.io.load(page.file.path);
    for (let line of content.split('\n')) {
      const t = line.trim();
      if (new RegExp('#' + tag + '(?![|\\w])', 'i').test(t) && !t.startsWith('tags:') && t.length > 5) {
        results.push(`**${page.file.name}**: ${t}`);
      }
    }
  }
  return results;
}

const wins      = await collect('win');
const learnings = [...await collect('learning'), ...await collect('til')];
const ideas     = await collect('idea');
const blocked   = await collect('blocked');

function section(title, items) {
  dv.header(3, title);
  if (items.length > 0) dv.list(items);
  else dv.paragraph('_none_');
}

section('Wins', wins);
section('Learnings', learnings);
section('Ideas', ideas);
section('Still Blocked', blocked);
```

---

## What's the highest-leverage thing next week?

>
