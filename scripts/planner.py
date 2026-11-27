#!/usr/bin/env python3
"""Deterministic helpers for the vault-os planner skills (daily, weekly, monthly).

The agent reads mail, calendar and meetings and decides what to write.
This script does the parts that must not drift: creating notes from the
vault's own templates, writing only inside planner blocks, and counting
the scorecard numbers. Standard library only.

The vault is --vault, else $VAULT_OS_VAULT_ROOT, else the current directory.
Notes are created from the vault's templates/daily.md, weekly.md and monthly.md;
when the vault has none, the starter templates in skills/planner/templates are used.

Usage:
  planner.py render daily|weekly|monthly YYYY-MM-DD
  planner.py block-set FILE NAME          < text   (replace block content)
  planner.py block-add FILE NAME          < lines  (append lines not already there)
  planner.py scorecard FILE [--meeting-hours H]
  planner.py open-items YYYY-MM-DD        (JSON: carried, promises and to-dos due, bets to review)
  planner.py time-strip [--start 8 --end 17] < JSON   (meeting hours and longest open block per day)
  planner.py focus-candidates YYYY-MM-DD   (JSON: goals, due promises, to-dos, meeting outcomes, ranked)
  planner.py focus-fill FILE      < lines  (fill Focus only while all its boxes are empty)
  planner.py stats START END              (JSON: totals over daily notes in range)
  planner.py week-review START END        (JSON: done, came due and still open, stale, My review per day)
  planner.py my-review FILE               (JSON: the user's My review section of one daily note)
  planner.py tick FILE TEXT --evidence E [--date D]  (tick one open task, stamp evidence and the done date)
  planner.py paths YYYY-MM-DD             (JSON: daily, weekly, monthly note paths)
"""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import json
import os
import re
import sys

DAILY_DIR = "reviews/daily"
WEEKLY_DIR = "reviews/weekly"
MONTHLY_DIR = "reviews/monthly"
TEMPLATES = {"daily": "templates/daily.md", "weekly": "templates/weekly.md", "monthly": "templates/monthly.md"}
# Starter templates shipped with the plugin, used when the vault has no template of its own.
BUNDLED_TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "planner", "templates")

# Heading used when an older note has no planner block yet.
BLOCK_HEADINGS = {
    "prep": "Prep",
    "focus": "Focus",
    "meetings": "Meetings",
    "promises": "Promises",
    "todo": "To-dos",
    "decisions": "Decisions",
    "ideas": "Ideas",
    "scorecard": "Scorecard",
    "last-week": "Last Week (planner)",
    "suggested-goals": "Suggested goals",
    "week-ahead": "This week",
    "ideas-moved": "Ideas moved",
    "month-scorecard": "Scorecard",
    "moved": "What Moved (planner)",
    "stalled": "What Stalled (planner)",
}

TASK_RE = re.compile(r"^\s*[-*] \[( |x|X)\] (.*)$")
LIST_RE = re.compile(r"^\s*[-*] (?:\[[ xX]\] )?(.*)$")
FIELD_RE = re.compile(r"\[(\w+)::\s*([^\]]*)\]")
# Obsidian Tasks emoji format, which the vault uses: due, scheduled and done dates.
DUE_EMOJI_RE = re.compile(r"\U0001F4C5\ufe0f?\s*(\d{4}-\d{2}-\d{2})")
SCHED_EMOJI_RE = re.compile(r"\u23f3\ufe0f?\s*(\d{4}-\d{2}-\d{2})")
DONE_EMOJI_RE = re.compile(r"\u2705\ufe0f?\s*(\d{4}-\d{2}-\d{2})")
# The user's own sections in the daily note. The planner reads them and never writes there.
ADD_HERE = "Add here"
MY_REVIEW = "My review"
REVIEW_LABELS = {"day rating": "rating", "what i saw in reality": "saw", "notes for claude": "notes"}


# ---------- dates (mirror moment.js "en" locale, which Templater uses) ----------

def parse_date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def week_start(d: dt.date) -> dt.date:
    """Sunday on or before d (moment en: startOf('week'))."""
    return d - dt.timedelta(days=(d.weekday() + 1) % 7)


def week_number(d: dt.date) -> int:
    """moment en 'ww': weeks start Sunday, week 1 contains Jan 1."""
    sat = week_start(d) + dt.timedelta(days=6)
    year = sat.year
    first = week_start(dt.date(year, 1, 1))
    return (week_start(d) - first).days // 7 + 1


def add_months(d: dt.date, n: int) -> dt.date:
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return dt.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


TOKEN_RE = re.compile(r"\[[^\]]*\]|YYYY|MMMM|MM|dddd|DD|ww|D")


def fmt(d: dt.date, pattern: str) -> str:
    def rep(m: re.Match) -> str:
        t = m.group(0)
        if t.startswith("["):
            return t[1:-1]
        return {
            "YYYY": f"{d.year:04d}",
            "MMMM": d.strftime("%B"),
            "MM": f"{d.month:02d}",
            "dddd": d.strftime("%A"),
            "DD": f"{d.day:02d}",
            "ww": f"{week_number(d):02d}",
            "D": str(d.day),
        }[t]

    return TOKEN_RE.sub(rep, pattern)


def weekly_name(d: dt.date) -> str:
    return f"Weekly Review {fmt(d, 'YYYY')}-W{fmt(d, 'ww')}"


def note_paths(d: dt.date) -> dict:
    return {
        "daily": f"{DAILY_DIR}/{d.isoformat()}.md",
        "weekly": f"{WEEKLY_DIR}/{weekly_name(week_start(d))}.md",
        "monthly": f"{MONTHLY_DIR}/Monthly Review {fmt(d, 'YYYY-MM')}.md",
    }


# ---------- Templater rendering (only the expressions these templates use) ----------

NOW_RE = re.compile(r"""tp\.date\.now\(\s*(["'])(.*?)\1\s*(?:,\s*(["']?)([-\w]+)\3\s*)?(?:,\s*tp\.file\.title\s*)?\)""")
MOMENT_RE = re.compile(r"""moment\(\)\.(startOf|endOf)\(\s*["'](week|month)["']\s*\)\.format\(\s*(["'])(.*?)\3\s*\)""")


def render_template(text: str, base: dt.date) -> str:
    text = re.sub(r"^<%\s*await tp\.file\.move\(.*?\)\s*%>\n", "", text, flags=re.M)

    def now(m: re.Match) -> str:
        pattern, offset = m.group(2), m.group(4)
        d = base
        if offset:
            mo = re.fullmatch(r"P(-?\d+)M", offset)
            d = add_months(base, int(mo.group(1))) if mo else base + dt.timedelta(days=int(offset))
        return fmt(d, pattern)

    def mom(m: re.Match) -> str:
        edge, unit, pattern = m.group(1), m.group(2), m.group(4)
        if unit == "week":
            d = week_start(base) + (dt.timedelta(days=6) if edge == "endOf" else dt.timedelta())
        else:
            d = base.replace(day=1)
            if edge == "endOf":
                d = d.replace(day=calendar.monthrange(d.year, d.month)[1])
        return fmt(d, pattern)

    def expr(m: re.Match) -> str:
        inner = m.group(1)
        inner = NOW_RE.sub(now, inner)
        inner = MOMENT_RE.sub(mom, inner)
        return inner.strip()

    out = re.sub(r"<%\s*(.*?)\s*%>", expr, text)
    # Expressions inside dataviewjs strings were rendered by the same pass.
    if "<%" in out or re.search(r"\btp\.", out):
        raise SystemExit("render: template has an expression this script does not handle")
    return out


def template_path(vault: str, kind: str) -> str:
    own = os.path.join(vault, TEMPLATES[kind])
    return own if os.path.exists(own) else os.path.join(BUNDLED_TEMPLATES, f"{kind}.md")


def resolve_vault(arg: str | None) -> str:
    v = os.path.abspath(arg or os.environ.get("VAULT_OS_VAULT_ROOT") or os.getcwd())
    if not any(os.path.isdir(os.path.join(v, d)) for d in (".obsidian", "reviews", "templates")):
        raise SystemExit(f"planner: {v} does not look like an Obsidian vault (no .obsidian/, reviews/ or templates/); pass --vault")
    return v


def cmd_render(vault: str, kind: str, d: dt.date) -> str:
    base = {"daily": d, "weekly": week_start(d), "monthly": d.replace(day=1)}[kind]
    path = os.path.join(vault, note_paths(d)[kind])
    if os.path.exists(path):
        return path
    with open(template_path(vault, kind), encoding="utf-8") as f:
        body = render_template(f.read(), base)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


# ---------- planner blocks ----------

def _markers(name: str) -> tuple[str, str]:
    return f"<!-- planner:{name} -->", f"<!-- /planner:{name} -->"


def _ensure_block(text: str, name: str) -> str:
    start, end = _markers(name)
    if start in text and end in text:
        return text
    heading = BLOCK_HEADINGS.get(name, name.title())
    return text.rstrip("\n") + f"\n\n---\n\n## {heading}\n\n{start}\n{end}\n"


def read_block(text: str, name: str) -> list[str]:
    start, end = _markers(name)
    if start not in text:
        return []
    inner = text.split(start, 1)[1].split(end, 1)[0]
    return [l for l in inner.strip("\n").split("\n") if l.strip()]


def _write_block(text: str, name: str, lines: list[str]) -> str:
    text = _ensure_block(text, name)
    start, end = _markers(name)
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    inner = "\n".join(lines)
    return f"{before}{start}\n{inner}\n{end}{after}" if inner else f"{before}{start}\n{end}{after}"


def _norm(line: str) -> str:
    line = re.sub(r"^\s*[-*] (\[[ xX]\] )?", "", line)
    line = FIELD_RE.sub("", line)
    return re.sub(r"\W+", " ", line).strip().lower()


def block_set(path: str, name: str, content: str) -> None:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = [l.rstrip() for l in content.strip("\n").split("\n")] if content.strip() else []
    with open(path, "w", encoding="utf-8") as f:
        f.write(_write_block(text, name, lines))


def block_add(path: str, name: str, content: str) -> int:
    """Append lines whose text is not already anywhere in the note. Keeps ticks the user made."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    seen = {_norm(l) for l in text.split("\n") if l.strip()}
    existing = read_block(text, name)
    added = 0
    for line in content.strip("\n").split("\n"):
        if line.strip() and _norm(line) not in seen:
            existing.append(line.rstrip())
            seen.add(_norm(line))
            added += 1
    with open(path, "w", encoding="utf-8") as f:
        f.write(_write_block(text, name, existing))
    return added


# ---------- parsing daily notes ----------

def section_lines(text: str, heading: str) -> list[str]:
    out, inside = [], False
    for line in text.split("\n"):
        if line.startswith("## "):
            inside = line[3:].strip().lower() == heading.lower()
            continue
        if inside and line.strip() == "---":
            break
        if inside:
            out.append(line)
    return out


def fields(line: str) -> dict:
    out = {k.lower(): v.strip() for k, v in FIELD_RE.findall(line)}
    m = DUE_EMOJI_RE.search(line)
    if m and not out.get("due"):
        out["due"] = m.group(1)
    m = SCHED_EMOJI_RE.search(line)
    if m and not out.get("scheduled"):
        out["scheduled"] = m.group(1)
    m = DONE_EMOJI_RE.search(line)
    if m:
        out["done_on"] = m.group(1)
    return out


def happens(item: dict) -> dt.date | None:
    """Tasks plugin 'happens': the earlier of the scheduled and due dates."""
    ds = [d for d in (_date_or_none(item.get("scheduled")), _date_or_none(item.get("due"))) if d]
    return min(ds) if ds else None


def has_tag(line: str, tag: str) -> bool:
    return re.search(r"(^|\s)#" + re.escape(tag) + r"(?![\w/-])", line) is not None


def daily_files(vault: str) -> list[tuple[dt.date, str]]:
    folder = os.path.join(vault, DAILY_DIR)
    out = []
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})\.md", name)
        if m:
            out.append((parse_date(m.group(1)), os.path.join(folder, name)))
    return out


def all_todos(vault: str) -> list[dict]:
    """Every #todo task across daily notes (the user's own to-dos, no recipient), plus the
    untagged tasks in each note's Add here section, which the user and other agents write."""
    out = []
    for day, path in daily_files(vault):
        heading = ""
        with open(path, encoding="utf-8") as f:
            for line in f.read().split("\n"):
                if line.startswith("## "):
                    heading = line[3:].strip()
                    continue
                t = TASK_RE.match(line)
                if not t or not t.group(2).strip():
                    continue
                added = heading == ADD_HERE and not any(has_tag(line, x) for x in ("todo", "promise", "outcome"))
                if has_tag(line, "todo") or added:
                    out.append({"day": day.isoformat(), "done": t.group(1) != " ", "text": t.group(2).strip(),
                                "added": added, **fields(line)})
    return out


def my_review(text: str) -> dict:
    """The user's My review section: day rating, what they saw, notes for Claude.
    A line that starts with a label opens that field; lines after it continue it."""
    out = {"rating": "", "saw": "", "notes": ""}
    key = None
    for line in section_lines(text, MY_REVIEW):
        s = re.sub(r"^\s*[-*] ", "", line).strip()
        label, sep, rest = s.partition(":")
        k = REVIEW_LABELS.get(re.sub(r"\s*\(.*\)\s*$", "", label).strip().lower()) if sep else None
        if k:
            key, s = k, rest.strip()
        if key and s:
            out[key] = (out[key] + " " + s).strip()
    m = re.search(r"\b([1-5])\b", out["rating"])
    out["score"] = int(m.group(1)) if m else None
    out["written"] = any(out[k] for k in ("rating", "saw", "notes"))
    return out


def all_items(vault: str) -> tuple[list[dict], list[dict]]:
    """Every #promise task and #decision line across daily notes."""
    promises, decisions = [], []
    for day, path in daily_files(vault):
        with open(path, encoding="utf-8") as f:
            lines = f.read().split("\n")
        for line in lines:
            t = TASK_RE.match(line)
            if t and has_tag(line, "promise"):
                promises.append({"day": day.isoformat(), "done": t.group(1) != " ", "text": t.group(2).strip(), **fields(line)})
            elif has_tag(line, "decision"):
                l = LIST_RE.match(line)
                if l:
                    decisions.append({"day": day.isoformat(), "text": l.group(1).strip(), **fields(line)})
    return promises, decisions


def focus_items(text: str) -> list[tuple[bool, str]]:
    out = []
    for line in section_lines(text, "Focus"):
        t = TASK_RE.match(line)
        if t and t.group(2).strip():
            out.append((t.group(1) != " ", t.group(2).strip()))
    return out


def _date_or_none(s: str | None) -> dt.date | None:
    try:
        return parse_date(s[:10]) if s else None
    except ValueError:
        return None


# ---------- frontmatter ----------

def set_frontmatter(text: str, values: dict) -> str:
    if not text.startswith("---\n"):
        return text
    head, body = text[4:].split("\n---", 1)
    lines = head.split("\n")
    for key, val in values.items():
        new = f"{key}: {'' if val is None else val}".rstrip()
        for i, line in enumerate(lines):
            if re.match(rf"^{re.escape(key)}:", line):
                lines[i] = new
                break
        else:
            lines.append(new)
    return "---\n" + "\n".join(lines) + "\n---" + body


# ---------- commands ----------

def outcome_items(text: str) -> list[tuple[bool, str]]:
    """The #outcome checkboxes in the Meetings section: one per meeting, ticked when it got what it was for."""
    out = []
    for line in text.splitlines():
        m = TASK_RE.match(line)
        if m and "#outcome" in m.group(2):
            out.append((m.group(1).lower() == "x", m.group(2)))
    return out


def cmd_scorecard(vault: str, path: str, meeting_hours: float | None) -> dict:
    day = parse_date(os.path.basename(path)[:10])
    with open(path, encoding="utf-8") as f:
        text = f.read()
    focus = focus_items(text)
    outcomes = outcome_items(text)
    promises, decisions = all_items(vault)
    due_today = [p for p in promises if _date_or_none(p.get("due")) == day]
    made_today = [p for p in promises if p["day"] == day.isoformat()]
    logged_today = [d for d in decisions if d["day"] == day.isoformat()]
    s = {
        "focus_done": sum(1 for done, _ in focus if done),
        "focus_total": len(focus),
        "promises_made": len(made_today),
        "promises_due": len(due_today),
        "promises_kept": sum(1 for p in due_today if p["done"]),
        "decisions_logged": len(logged_today),
        "meeting_hours": meeting_hours,
        "carried": sum(1 for done, _ in focus if not done),
        "outcomes_hit": sum(1 for done, _ in outcomes if done),
        "outcomes_total": len(outcomes),
    }
    text = set_frontmatter(text, s)
    line = (
        f"Focus {s['focus_done']}/{s['focus_total']} · "
        f"Promises kept {s['promises_kept']}/{s['promises_due']} due, {s['promises_made']} new · "
        f"Decisions {s['decisions_logged']} · "
        f"Meetings {meeting_hours if meeting_hours is not None else '?'} h, "
        f"outcomes {s['outcomes_hit']}/{s['outcomes_total']} · "
        f"Carried {s['carried']}"
    )
    text = _write_block(text, "scorecard", [line])
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return s


def previous_note(vault: str, d: dt.date) -> str | None:
    before = [p for day, p in daily_files(vault) if day < d]
    return before[-1] if before else None


def cmd_open_items(vault: str, d: dt.date) -> dict:
    promises, decisions = all_items(vault)
    prev = previous_note(vault, d)
    carried = []
    if prev:
        with open(prev, encoding="utf-8") as f:
            carried = [t for done, t in focus_items(f.read()) if not done]
    due = [p for p in promises if not p["done"] and (_date_or_none(p.get("due")) or dt.date.max) <= d]
    undated = [p for p in promises if not p["done"] and not _date_or_none(p.get("due"))]
    review = [x for x in decisions if not x.get("verdict") and (_date_or_none(x.get("review")) or dt.date.max) <= d]
    todos = [t for t in all_todos(vault) if not t["done"]]
    soon = d + dt.timedelta(days=3)
    review_prev = None
    if prev:
        with open(prev, encoding="utf-8") as f:
            review_prev = my_review(f.read())
    return {
        "date": d.isoformat(),
        "carried_from": os.path.relpath(prev, vault) if prev else None,
        "carried": carried,
        "my_review": review_prev,
        "promises_due": sorted(due, key=lambda p: p.get("due", "")),
        "promises_undated": undated,
        "decisions_to_review": sorted(review, key=lambda x: x.get("review", "")),
        "todos_due_soon": sorted([t for t in todos if (happens(t) or dt.date.max) <= soon], key=lambda t: happens(t).isoformat()),
        "todos_undated": [t for t in todos if not happens(t)],
        "added_undated": [t for t in todos if t["added"] and not happens(t)],
    }


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _clock(mins: int) -> str:
    h, m = divmod(mins, 60)
    return f"{(h - 1) % 12 + 1}:{m:02d}"


def cmd_time_strip(days: dict, start_h: int = 8, end_h: int = 17) -> str:
    """One line per day: a bar of meeting hours (one cell per hour), the hours,
    and the longest open block. days = {"Mon": [["09:30", "09:45"], ...], ...}
    holding counted events only; overlaps are merged. A day may also be given
    as {"events": [...], "note": "Thanksgiving"}."""
    lo, hi = start_h * 60, end_h * 60
    cells = end_h - start_h
    rows = []
    for day, spec in days.items():
        events = spec["events"] if isinstance(spec, dict) else spec
        note = spec.get("note", "") if isinstance(spec, dict) else ""
        iv = sorted((max(lo, _minutes(a)), min(hi, _minutes(b))) for a, b in events)
        merged: list[list[int]] = []
        for a, b in iv:
            if b <= a:
                continue
            if merged and a <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        busy = sum(b - a for a, b in merged)
        gaps, cur = [], lo
        for a, b in merged:
            gaps.append((cur, a)); cur = b
        gaps.append((cur, hi))
        g = max(gaps, key=lambda x: x[1] - x[0])
        filled = round(busy / 60)
        bar = "\u2588" * filled + "\u2591" * (cells - filled)
        gap = f"open {_clock(g[0])}\u2013{_clock(g[1])}" if g[1] > g[0] else "no open block"
        tail = f" \u00b7 {note}" if note else ""
        rows.append(f"{day:<4}{bar}  {busy / 60:4.1f} h  \u00b7 {gap}{tail}")
    return "\n".join(["```", *rows, "```"])


def cmd_stats(vault: str, start: dt.date, end: dt.date) -> dict:
    keys = ["focus_done", "focus_total", "promises_made", "promises_due", "promises_kept", "decisions_logged", "meeting_hours", "carried", "outcomes_hit", "outcomes_total"]
    tot = {k: 0.0 for k in keys}
    days = 0
    for day, path in daily_files(vault):
        if not (start <= day <= end):
            continue
        with open(path, encoding="utf-8") as f:
            head = f.read().split("\n---", 1)[0]
        days += 1
        for k in keys:
            m = re.search(rf"^{k}:\s*([0-9.]+)\s*$", head, re.M)
            if m:
                tot[k] += float(m.group(1))
    promises, decisions = all_items(vault)
    missed = [p for p in promises if not p["done"] and (d := _date_or_none(p.get("due"))) and start <= d <= end]
    reviewed = [x for x in decisions if x.get("verdict") and (r := _date_or_none(x.get("review"))) and start <= r <= end]
    rate = lambda a, b: round(100 * a / b) if b else None
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "days_with_notes": days,
        "totals": {k: (int(v) if float(v).is_integer() else round(v, 1)) for k, v in tot.items()},
        "focus_hit_rate_pct": rate(tot["focus_done"], tot["focus_total"]),
        "promise_kept_rate_pct": rate(tot["promises_kept"], tot["promises_due"]),
        "meeting_outcome_rate_pct": rate(tot["outcomes_hit"], tot["outcomes_total"]),
        "promises_missed": missed,
        "decisions_reviewed": reviewed,
        "verdicts": {v: sum(1 for x in reviewed if x.get("verdict") == v) for v in ("skill", "luck", "bad-luck", "bad-call")},
    }


def _vault_task_lines(vault: str):
    """(relative path, line number, line) for every task line in the vault outside templates and dot folders."""
    for root, dirs, files in os.walk(vault):
        dirs[:] = sorted(x for x in dirs if not x.startswith(".") and os.path.relpath(os.path.join(root, x), vault) != "templates")
        for name in sorted(files):
            if not name.endswith(".md"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8") as f:
                for i, line in enumerate(f.read().split("\n")):
                    if TASK_RE.match(line):
                        yield os.path.relpath(path, vault), i, line


def cmd_week_review(vault: str, start: dt.date, end: dt.date) -> dict:
    """What the weekly review needs: tasks done in the range (by the Tasks plugin's done date),
    ticked boxes in the range's daily notes with no done date, tasks that came due and are still
    open, older open tasks whose dates have passed, and each day's My review."""
    done, done_undated, due_open, stale = [], [], [], 0
    in_range = {day.isoformat() for day, _ in daily_files(vault) if start <= day <= end}
    for rel, _, line in _vault_task_lines(vault):
        t = TASK_RE.match(line)
        text = t.group(2).strip()
        if not text:
            continue
        f = fields(line)
        is_done = t.group(1) != " "
        daily = rel.startswith(DAILY_DIR + "/")
        day = os.path.basename(rel)[:10] if daily else None
        item = {"file": rel, "text": text, **f}
        if is_done:
            on = _date_or_none(f.get("done_on"))
            if on and start <= on <= end:
                done.append(item)
            elif not on and day in in_range and not has_tag(line, "outcome"):
                done_undated.append(item)
            continue
        if not daily:
            continue
        due = _date_or_none(f.get("due"))
        if due and start <= due <= end:
            due_open.append(item)
        h = happens(f)
        if h and h < start - dt.timedelta(days=14):
            stale += 1
    reviews = []
    for day, path in daily_files(vault):
        if start <= day <= end:
            with open(path, encoding="utf-8") as fh:
                r = my_review(fh.read())
            if r["written"]:
                reviews.append({"day": day.isoformat(), **r})
    scores = [r["score"] for r in reviews if r["score"]]
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "done": sorted(done, key=lambda x: x.get("done_on", "")),
        "done_without_date": done_undated,
        "came_due_still_open": sorted(due_open, key=lambda x: x.get("due", "")),
        "stale_open_count": stale,
        "reviews": reviews,
        "ratings": scores,
        "rating_avg": round(sum(scores) / len(scores), 1) if scores else None,
    }


def tick(path: str, match: str, evidence: str, on: dt.date) -> str:
    """Tick the one open task in the note whose text holds `match`, adding [evidence:: ] and
    the Tasks plugin's done date, so the weekly review counts it like a tick made in Obsidian."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    hits = [i for i, l in enumerate(lines) if (t := TASK_RE.match(l)) and t.group(1) == " " and match.lower() in t.group(2).lower()]
    if len(hits) != 1:
        raise SystemExit(f"tick: {len(hits)} open tasks match {match!r}; give text that matches exactly one")
    i = hits[0]
    line = re.sub(r"\[ \]", "[x]", lines[i], count=1).rstrip()
    if not FIELD_RE.search(line) or "evidence" not in dict((k.lower(), v) for k, v in FIELD_RE.findall(line)):
        line += f" [evidence:: {evidence.strip()}]"
    if not DONE_EMOJI_RE.search(line):
        line += f" \u2705 {on.isoformat()}"
    lines[i] = line
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return line


# ---------- focus ----------

STOP = set("a an and the to for of on in with by from your you is it this that be at or".split())


def _words(t: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", FIELD_RE.sub("", t).lower()) if len(w) > 2 and w not in STOP}


def week_goals(vault: str, d: dt.date) -> tuple[list[str], bool]:
    """Goals the user wrote in the weekly note, or the planner's suggestions while none are written."""
    path = os.path.join(vault, note_paths(d)["weekly"])
    if not os.path.exists(path):
        return [], False
    with open(path, encoding="utf-8") as f:
        text = f.read()
    heading = next((l[3:].strip() for l in text.split("\n") if l.startswith("## ") and l.endswith("Goals")), "")
    mine = [m.group(2).strip() for l in section_lines(text, heading) if (m := TASK_RE.match(l)) and m.group(2).strip()]
    if mine:
        return mine, True
    start, end = _markers("suggested-goals")
    block = text.split(start, 1)[1].split(end, 1)[0] if start in text and end in text else ""
    return [re.sub(r"^\s*[-*] (Suggestion:\s*)?", "", l).strip() for l in block.split("\n") if l.strip().startswith("- ")], False


def cmd_focus_candidates(vault: str, d: dt.date) -> dict:
    """First-cut Eisenhower ranking. Important: tied to a week goal, or owed to someone.
    Urgent: overdue, due today, or a meeting today. The agent makes the final call and picks the one thing."""
    goals, goals_are_his = week_goals(vault, d)
    goal_words = [_words(g) for g in goals]

    def goal_for(t: str) -> str | None:
        w = _words(t)
        best = max(range(len(goals)), key=lambda i: len(w & goal_words[i]), default=None)
        return goals[best] if best is not None and len(w & goal_words[best]) >= 2 else None

    promises, _ = all_items(vault)
    cands = []
    for p in promises:
        if p["done"]:
            continue
        due = _date_or_none(p.get("due"))
        cands.append({"kind": "promise", "text": p["text"], "to": p.get("to"), "due": p.get("due"),
                      "overdue_days": (d - due).days if due and due < d else 0,
                      "urgent": bool(due and due <= d), "important": True})
    for t in all_todos(vault):
        due = _date_or_none(t.get("due"))
        if t["done"] or not due or due > d:
            continue
        cands.append({"kind": "todo", "text": t["text"], "due": t.get("due"),
                      "overdue_days": (d - due).days if due < d else 0, "urgent": True, "important": False})
    path = os.path.join(vault, note_paths(d)["daily"])
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for done, text in outcome_items(f.read()):
                if not done:
                    cands.append({"kind": "meeting-outcome", "text": text, "due": d.isoformat(),
                                  "overdue_days": 0, "urgent": True, "important": False})
    for c in cands:
        c["goal"] = goal_for(c["text"])
        c["important"] = c["important"] or bool(c["goal"])
        c["quadrant"] = {(True, True): "do first", (True, False): "schedule",
                         (False, True): "fit in or hand off", (False, False): "drop"}[(c["important"], c["urgent"])]
    order = {"do first": 0, "schedule": 1, "fit in or hand off": 2, "drop": 3}
    cands.sort(key=lambda c: (order[c["quadrant"]], -c["overdue_days"], c.get("due") or "9999", c["kind"] != "promise"))
    return {"date": d.isoformat(), "goals": goals, "goals_are_his": goals_are_his, "candidates": cands}


def focus_fill(path: str, content: str) -> bool:
    """Write the top 3 into Focus only while every Focus box is empty. Returns False and changes nothing otherwise."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if focus_items(text):
        return False
    lines = [l.rstrip() for l in content.strip("\n").split("\n") if l.strip()][:3]
    start, end = _markers("focus")
    if start not in text:
        # Older notes: swap the three empty boxes under ## Focus for the block.
        text = re.sub(r"(## Focus\n\n)(?:- \[ \][ \t]*\n)+", lambda m: f"{m.group(1)}{start}\n{end}\n", text, count=1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(_write_block(text, "focus", lines))
    return True


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", help="vault root (default: $VAULT_OS_VAULT_ROOT, then the current directory)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render"); r.add_argument("kind", choices=list(TEMPLATES)); r.add_argument("date")
    for name in ("block-set", "block-add"):
        b = sub.add_parser(name); b.add_argument("file"); b.add_argument("name")
    s = sub.add_parser("scorecard"); s.add_argument("file"); s.add_argument("--meeting-hours", type=float)
    o = sub.add_parser("open-items"); o.add_argument("date")
    st = sub.add_parser("stats"); st.add_argument("start"); st.add_argument("end")
    wr = sub.add_parser("week-review"); wr.add_argument("start"); wr.add_argument("end")
    mr = sub.add_parser("my-review"); mr.add_argument("file")
    tk = sub.add_parser("tick"); tk.add_argument("file"); tk.add_argument("text")
    tk.add_argument("--evidence", required=True); tk.add_argument("--date", help="done date (default today)")
    p = sub.add_parser("paths"); p.add_argument("date")
    fc = sub.add_parser("focus-candidates"); fc.add_argument("date")
    ff = sub.add_parser("focus-fill"); ff.add_argument("file")
    ts = sub.add_parser("time-strip"); ts.add_argument("--start", type=int, default=8); ts.add_argument("--end", type=int, default=17)
    a = ap.parse_args(argv)
    v = None if a.cmd in ("paths", "time-strip") else resolve_vault(a.vault)

    def resolve(f: str) -> str:
        return f if os.path.isabs(f) else os.path.join(v, f)

    if a.cmd == "render":
        print(os.path.relpath(cmd_render(v, a.kind, parse_date(a.date)), v))
    elif a.cmd == "block-set":
        block_set(resolve(a.file), a.name, sys.stdin.read())
    elif a.cmd == "block-add":
        print(f"added {block_add(resolve(a.file), a.name, sys.stdin.read())}")
    elif a.cmd == "scorecard":
        print(json.dumps(cmd_scorecard(v, resolve(a.file), a.meeting_hours)))
    elif a.cmd == "open-items":
        print(json.dumps(cmd_open_items(v, parse_date(a.date)), indent=2))
    elif a.cmd == "stats":
        print(json.dumps(cmd_stats(v, parse_date(a.start), parse_date(a.end)), indent=2))
    elif a.cmd == "week-review":
        print(json.dumps(cmd_week_review(v, parse_date(a.start), parse_date(a.end)), indent=2, ensure_ascii=False))
    elif a.cmd == "my-review":
        with open(resolve(a.file), encoding="utf-8") as f:
            print(json.dumps(my_review(f.read()), indent=2, ensure_ascii=False))
    elif a.cmd == "tick":
        print(tick(resolve(a.file), a.text, a.evidence, parse_date(a.date) if a.date else dt.date.today()))
    elif a.cmd == "paths":
        print(json.dumps(note_paths(parse_date(a.date))))
    elif a.cmd == "focus-candidates":
        print(json.dumps(cmd_focus_candidates(v, parse_date(a.date)), indent=2))
    elif a.cmd == "focus-fill":
        print("filled" if focus_fill(resolve(a.file), sys.stdin.read()) else "kept yours: Focus already has items")
    elif a.cmd == "time-strip":
        print(cmd_time_strip(json.load(sys.stdin), a.start, a.end))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
