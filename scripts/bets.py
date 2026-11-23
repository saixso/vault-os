#!/usr/bin/env python3
"""Deterministic helpers for the vault-os bets skill.

A bet is a piece of work someone committed to for a cycle (a Shape Up bet,
a quarter goal, a personal project). Each bet is one note in the vault's
bets/ folder. The agent talks to the user and decides what to record; this
script does the parts that must not drift: creating notes from the template,
appending signals, blockers, milestones, KPIs and readings in a fixed format,
and setting each bet's status by fixed rules, not by model judgment.
Standard library only.

The vault is --vault, else $VAULT_OS_VAULT_ROOT, else the current directory.
Notes are created from the vault's templates/bet.md, or the starter template
in skills/bets/templates/bet.md when the vault has none.

Usage:
  bets.py new                         < JSON   (one bet object, or a list, for backfill)
  bets.py signal FILE TEXT [--date D] [--call off-track|on-track]
  bets.py blocker FILE TEXT [--date D]
  bets.py milestone FILE TEXT --due D
  bets.py tick FILE MATCH [--date D]  (tick the one open milestone or blocker containing MATCH)
  bets.py kpi FILE METRIC --target T [--baseline B] [--read-by D] [--direction up|down]
  bets.py reading FILE METRIC VALUE [--date D]
  bets.py set FILE key=value ...      (owner, area, cycle, appetite, cycle_start, cycle_end,
                                       started, shipped, dropped, outcome)
  bets.py list [--today D]            (JSON: every bet, parsed and scored)
  bets.py follow-ups [--today D]      (JSON: asks for each owner)
  bets.py score [--today D] [--area work|life] [--out NOTE]
                                      (write status fields to each bet and the radar note)

Thresholds (days, on list, follow-ups and score): --blocker-days 7, --stale-days 7,
--warn-days 14, or set them
in BETS_DIR/bets-config.json as {"blocker_days": 7, "stale_days": 7, "warn_days": 14}.
Flags win over the file.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from planner import FIELD_RE, TASK_RE, fields, has_tag, set_frontmatter  # noqa: E402

BETS_DIR = "bets"
RADAR_NOTE = "Bet Radar.md"
CONFIG_NAME = "bets-config.json"
TEMPLATE = "templates/bet.md"
BUNDLED_TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "bets", "templates", "bet.md")

# Frontmatter the user (or the agent, on the user's word) owns.
USER_FIELDS = ["bet", "owner", "area", "cycle", "appetite", "cycle_start", "cycle_end",
               "started", "shipped", "dropped", "outcome", "source"]
DATE_FIELDS = {"cycle_start", "cycle_end", "started", "shipped", "dropped"}
SETTABLE = [f for f in USER_FIELDS if f not in ("bet", "source")]
# Frontmatter only `score` writes.
SCORE_FIELDS = ["status", "status_reason", "delivery", "kpi_result", "last_signal"]

AREAS = ("work", "life")
OUTCOMES = ("hit", "partial", "missed")
CALLS = ("off-track", "on-track")

SECTIONS = {"milestone": "Milestones", "kpi": "KPIs", "reading": "Readings",
            "blocker": "Blockers", "signal": "Signals"}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SIGNAL_RE = re.compile(r"^\s*[-*] (\d{4}-\d{2}-\d{2}) (.*)$")
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


@dataclasses.dataclass
class Thresholds:
    blocker_days: int = 7   # an open blocker older than this makes a bet drifting
    stale_days: int = 7     # no signal for this long makes a bet stalled
    warn_days: int = 14     # a date this close with work not started makes a bet drifting


# ---------- vault and files ----------

def resolve_vault(arg: str | None) -> str:
    v = os.path.abspath(arg or os.environ.get("VAULT_OS_VAULT_ROOT") or os.getcwd())
    if not any(os.path.isdir(os.path.join(v, d)) for d in (".obsidian", BETS_DIR, "templates")):
        raise SystemExit(f"bets: {v} does not look like an Obsidian vault (no .obsidian/, {BETS_DIR}/ or templates/); pass --vault")
    return v


def bets_dir(vault: str) -> str:
    return os.path.join(vault, BETS_DIR)


def load_thresholds(vault: str, overrides: dict) -> Thresholds:
    t = Thresholds()
    path = os.path.join(bets_dir(vault), CONFIG_NAME)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for k, val in json.load(f).items():
                if hasattr(t, k):
                    setattr(t, k, int(val))
    for k, val in overrides.items():
        if val is not None:
            setattr(t, k, int(val))
    return t


def safe_name(name: str) -> str:
    """A file name Obsidian accepts: no / \\ : * ? " < > | # ^ [ ]."""
    s = re.sub(r'[\\/:*?"<>|#^\[\]]', " ", name).strip(" .-")
    return re.sub(r"\s+", " ", s) or "Untitled bet"


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ---------- frontmatter ----------

def read_frontmatter(text: str) -> dict:
    """Flat `key: value` frontmatter. List items and nested keys are skipped."""
    if not text.startswith("---\n") or "\n---" not in text[3:]:
        return {}
    head = text[4:].split("\n---", 1)[0]
    out = {}
    for line in head.split("\n"):
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m:
            continue
        val = m.group(2).strip()
        if len(val) >= 2 and val[0] == val[-1] == '"':
            try:
                val = json.loads(val)
            except ValueError:
                val = val[1:-1]
        elif len(val) >= 2 and val[0] == val[-1] == "'":
            val = val[1:-1].replace("''", "'")
        out[m.group(1)] = val
    return out


def yaml_value(val) -> str:
    """A scalar that stays a plain string in YAML: quote it when it would not."""
    if val is None:
        return ""
    s = str(val).replace("\n", " ").strip()
    if s == "" or DATE_RE.match(s) or re.fullmatch(r"-?\d+(\.\d+)?", s):
        return s
    if re.search(r":\s|\s#|^[\[\]{}&*!|>'\"%@`,?-]|^(true|false|yes|no|null|~)$", s, re.I):
        return json.dumps(s, ensure_ascii=False)
    return s


def write_fields(text: str, values: dict) -> str:
    return set_frontmatter(text, {k: yaml_value(v) for k, v in values.items()})


# ---------- dates and numbers ----------

def to_date(s) -> dt.date | None:
    if not s:
        return None
    try:
        return dt.date.fromisoformat(str(s).strip()[:10])
    except ValueError:
        return None


def check_date(s: str, what: str) -> str:
    if s and not to_date(s):
        raise SystemExit(f"bets: {what} must be YYYY-MM-DD, got {s!r}")
    return s


def to_num(s) -> float | None:
    if s is None:
        return None
    m = NUM_RE.search(str(s).replace(",", ""))
    return float(m.group(0)) if m else None


def fmt_num(x: float | None) -> str:
    if x is None:
        return "?"
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


def short(d: dt.date | None) -> str:
    return f"{d:%b} {d.day}, {d.year}" if d else ""


# ---------- parsing a bet note ----------

def section_bounds(lines: list[str], heading: str) -> tuple[int, int] | None:
    """(index of the heading line, index where the section ends)."""
    start = next((i for i, l in enumerate(lines) if l.strip().lower() == f"## {heading}".lower()), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ") or lines[i].startswith("# ")), len(lines))
    return start, end


def section_lines(lines: list[str], heading: str) -> list[str]:
    b = section_bounds(lines, heading)
    return lines[b[0] + 1:b[1]] if b else []


def parse_bet(path: str) -> dict | None:
    text = _read(path)
    fm = read_frontmatter(text)
    if fm.get("type") != "bet":
        return None
    lines = text.split("\n")
    milestones, kpis, readings, blockers, signals = [], [], [], [], []
    for line in lines:
        t = TASK_RE.match(line)
        if t and has_tag(line, "milestone"):
            f = fields(line)
            milestones.append({"done": t.group(1) != " ", "text": _clean(t.group(2), "milestone"), "due": f.get("due"), "done_on": f.get("done")})
        elif t and has_tag(line, "blocker"):
            f = fields(line)
            blockers.append({"open": t.group(1) == " ", "text": _clean(t.group(2), "blocker"), "opened": f.get("opened"), "cleared": f.get("done")})
        elif has_tag(line, "kpi") and re.match(r"^\s*[-*] ", line):
            f = fields(line)
            kpis.append({"metric": _clean(re.sub(r"^\s*[-*] ", "", line), "kpi"), "baseline": f.get("baseline"),
                         "target": f.get("target"), "read_by": f.get("read_by"), "direction": f.get("direction")})
        elif has_tag(line, "reading"):
            m = SIGNAL_RE.match(line)
            if m:
                readings.append({"date": m.group(1), "metric": _clean(m.group(2), "reading"), "value": fields(line).get("value")})
    for line in section_lines(lines, SECTIONS["signal"]):
        m = SIGNAL_RE.match(line)
        if m:
            body = m.group(2)
            call = next((c for c in CALLS if has_tag(body, c)), None)
            signals.append({"date": m.group(1), "text": FIELD_RE.sub("", re.sub(r"#(off-track|on-track)\b", "", body)).strip(), "call": call})
    stem = os.path.splitext(os.path.basename(path))[0]
    return {
        "file": path, "note": stem,
        **{k: fm.get(k, "") for k in USER_FIELDS},
        "bet": fm.get("bet") or stem,
        "milestones": milestones, "kpis": kpis, "readings": readings,
        "blockers": blockers, "signals": signals,
    }


def _clean(text: str, tag: str) -> str:
    text = re.sub(r"(^|\s)#" + re.escape(tag) + r"(?![\w/-])", " ", text)
    text = FIELD_RE.sub("", text)
    text = re.sub("\U0001F4C5\ufe0f?\\s*\\d{4}-\\d{2}-\\d{2}", "", text)
    return re.sub(r"\s+", " ", text).strip()


def all_bets(vault: str) -> list[dict]:
    folder = bets_dir(vault)
    out = []
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if name.endswith(".md"):
            b = parse_bet(os.path.join(folder, name))
            if b:
                out.append(b)
    return out


# ---------- the rules ----------

def kpi_result(kpi: dict, readings: list[dict]) -> dict:
    """Latest reading of one KPI against its baseline and target.
    hit: reached the target. partial: moved from the baseline toward it. missed: did not move."""
    mine = sorted((r for r in readings if r["metric"].lower() == kpi["metric"].lower() and to_num(r["value"]) is not None),
                  key=lambda r: r["date"])
    base, target = to_num(kpi.get("baseline")), to_num(kpi.get("target"))
    out = {"metric": kpi["metric"], "baseline": base, "target": target, "read_by": kpi.get("read_by"),
           "reading": None, "read_on": None, "result": "not-read"}
    if not mine:
        return out
    last = mine[-1]
    r = to_num(last["value"])
    out.update(reading=r, read_on=last["date"])
    if target is None:
        out["result"] = "no-target"
        return out
    direction = (kpi.get("direction") or "").lower()
    if direction not in ("up", "down"):
        direction = "down" if base is not None and target < base else "up"
    better = (lambda a, b: a > b) if direction == "up" else (lambda a, b: a < b)
    if r == target or better(r, target):
        out["result"] = "hit"
    elif base is not None and better(r, base):
        out["result"] = "partial"
    else:
        out["result"] = "missed"
    return out


def combine_results(results: list[str]) -> str:
    read = [r for r in results if r in ("hit", "partial", "missed")]
    if not results:
        return "no-kpi"
    if not read:
        return "not-read"
    if all(r == "hit" for r in read):
        return "hit"
    if all(r == "missed" for r in read):
        return "missed"
    return "partial"


def delivery(bet: dict, today: dt.date) -> str:
    end, shipped = to_date(bet["cycle_end"]), to_date(bet["shipped"])
    if to_date(bet["dropped"]):
        return "dropped"
    if shipped:
        return "on-time" if not end or shipped <= end else "late"
    if end and end < today:
        return "not-shipped"
    if to_date(bet["cycle_start"]) and to_date(bet["cycle_start"]) > today:
        return "upcoming"
    return "in-progress"


def last_signal(bet: dict) -> dict | None:
    return max(bet["signals"], key=lambda s: s["date"]) if bet["signals"] else None


def started(bet: dict) -> bool:
    return bool(to_date(bet["started"])) or any(m["done"] for m in bet["milestones"])


# Each rule: (status, check). A check returns a reason, or None when it does not apply.
# Rules run in order and the first reason wins. Another kind of note (decisions, later)
# can bring its own list and reuse evaluate().

def _owner_call(b, ctx):
    calls = [s for s in b["signals"] if s["call"]]
    if calls:
        last = max(calls, key=lambda s: s["date"])
        if last["call"] == "off-track":
            return f"owner called it off track on {short(to_date(last['date']))}"
    return None


def _milestone_passed(b, ctx):
    late = sorted((m for m in b["milestones"] if not m["done"] and to_date(m["due"]) and to_date(m["due"]) < ctx["today"]),
                  key=lambda m: m["due"])
    return f"milestone \"{late[0]['text']}\" was due {short(to_date(late[0]['due']))}" if late else None


def _cycle_over(b, ctx):
    end = to_date(b["cycle_end"])
    return f"cycle ended {short(end)} and it has not shipped" if end and end < ctx["today"] else None


def _old_blocker(b, ctx):
    limit = ctx["today"] - dt.timedelta(days=ctx["t"].blocker_days)
    old = sorted((x for x in b["blockers"] if x["open"] and to_date(x["opened"]) and to_date(x["opened"]) <= limit),
                 key=lambda x: x["opened"])
    if old:
        days = (ctx["today"] - to_date(old[0]["opened"])).days
        return f"blocker open {days} days: {old[0]['text']}"
    return None


def _close_date_not_started(b, ctx):
    if started(b):
        return None
    dates = [to_date(m["due"]) for m in b["milestones"] if not m["done"]] + [to_date(b["cycle_end"])]
    ahead = sorted(d for d in dates if d and d >= ctx["today"])
    if ahead and (ahead[0] - ctx["today"]).days < ctx["t"].warn_days:
        return f"{short(ahead[0])} is {(ahead[0] - ctx['today']).days} days away and work has not started"
    return None


def _no_owner(b, ctx):
    return "no owner" if not b["owner"].strip() else None


def _no_signal(b, ctx):
    s = last_signal(b)
    since = to_date(s["date"]) if s else (to_date(b["started"]) or to_date(b["cycle_start"]))
    if since is None:
        return "no signal yet and no start date"
    days = (ctx["today"] - since).days
    if days > ctx["t"].stale_days:
        return f"no signal for {days} days" if s else f"no signal since the cycle started {short(since)}"
    return None


ACTIVE_RULES = [
    ("off-track", _owner_call),
    ("off-track", _milestone_passed),
    ("off-track", _cycle_over),
    ("drifting", _old_blocker),
    ("drifting", _close_date_not_started),
    ("stalled", _no_owner),
    ("stalled", _no_signal),
]


def evaluate(rules, item, ctx, default=("on-track", "")) -> tuple[str, str]:
    for status, check in rules:
        reason = check(item, ctx)
        if reason:
            return status, reason
    return default


def score_bet(bet: dict, today: dt.date, t: Thresholds) -> dict:
    ctx = {"today": today, "t": t}
    deliv = delivery(bet, today)
    if deliv == "dropped":
        status, reason = "dropped", f"dropped {short(to_date(bet['dropped']))}"
    elif deliv in ("on-time", "late"):
        status, reason = "shipped", f"shipped {short(to_date(bet['shipped']))}" + (" (late)" if deliv == "late" else "")
    elif deliv == "upcoming" and bet["owner"].strip():
        status, reason = "upcoming", f"cycle starts {short(to_date(bet['cycle_start']))}"
    else:
        status, reason = evaluate(ACTIVE_RULES, bet, ctx)
    kpis = [kpi_result(k, bet["readings"]) for k in bet["kpis"]]
    computed = combine_results([k["result"] for k in kpis if k["result"] != "no-target"]) if kpis else "no-kpi"
    users = bet["outcome"].strip().lower()
    s = last_signal(bet)
    return {
        **bet,
        "status": status, "status_reason": reason, "delivery": deliv,
        "kpi_results": kpis, "kpi_result": computed,
        "final_outcome": users if users in OUTCOMES else computed,
        "outcome_by": "user" if users in OUTCOMES else "kpi",
        "last_signal": s["date"] if s else "",
        "next_date": _next_date(bet, today),
    }


def _next_date(bet: dict, today: dt.date) -> str:
    dates = [to_date(m["due"]) for m in bet["milestones"] if not m["done"]] + [to_date(bet["cycle_end"])]
    ahead = sorted(d for d in dates if d and d >= today)
    return ahead[0].isoformat() if ahead else ""


def follow_ups(scored: list[dict], today: dt.date, t: Thresholds) -> list[dict]:
    """What to ask whom. One entry per ask, named to the bet's owner."""
    out = []
    for b in scored:
        owner = b["owner"].strip() or "(no owner)"

        def ask(kind, text, due=None):
            out.append({"owner": owner, "bet": b["bet"], "note": b["note"], "kind": kind, "ask": text,
                        "days_overdue": (today - to_date(due)).days if due else None})

        if b["status"] == "dropped":
            continue
        if not b["owner"].strip():
            ask("owner", "Name an owner for this bet")
        for k in b["kpi_results"]:
            due = to_date(k["read_by"])
            if due and due <= today and not (k["read_on"] and to_date(k["read_on"]) >= due):
                ask("kpi-reading", f"Get the KPI reading: {k['metric']} (due {short(due)})", k["read_by"])
        if b["status"] in ("dropped", "shipped", "upcoming"):
            continue
        if b["status"] == "off-track":
            ask("off-track", f"Agree a scope cut, a new date or a stop: {b['status_reason']}")
        for x in b["blockers"]:
            opened = to_date(x["opened"])
            if x["open"] and opened and (today - opened).days >= t.blocker_days:
                ask("blocker", f"Ask what clears the blocker: {x['text']}")
        if b["status"] == "stalled" and b["owner"].strip():
            ask("update", f"Ask for an update ({b['status_reason']})")
    order = {"owner": 0, "off-track": 1, "kpi-reading": 2, "blocker": 3, "update": 4}
    out.sort(key=lambda f: (f["owner"].lower(), order[f["kind"]], f["bet"].lower()))
    return out


# ---------- writing notes ----------

def render_bet(template: str, bet: dict) -> str:
    def lines(kind: str) -> str:
        return "\n".join(LINE_FORMATS[kind](x) for x in bet.get(LIST_KEYS[kind]) or [])

    values = {k: yaml_value(bet.get(k)) for k in USER_FIELDS}
    values["area"] = values["area"] or "work"
    body = template
    for k, v in values.items():
        body = body.replace("{{" + k + "}}", v)
    body = body.replace("{{problem}}", (bet.get("problem") or "").strip())
    for kind in LIST_KEYS:
        body = body.replace("{{" + LIST_KEYS[kind] + "}}", lines(kind))
    # The heading carries the plain name, not its YAML-quoted form.
    body = re.sub(r"^# .*$", lambda _: f"# {bet['bet']}", body, count=1, flags=re.M)
    body = re.sub(r"[ \t]+$", "", body, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", body)


def _milestone_line(m: dict) -> str:
    box = "x" if m.get("done") else " "
    due = f" \U0001F4C5 {check_date(m['due'], 'milestone due')}" if m.get("due") else ""
    done = f" [done:: {check_date(m['done_on'], 'milestone done')}]" if m.get("done_on") else ""
    return f"- [{box}] #milestone {m['text'].strip()}{due}{done}"


def _kpi_line(k: dict) -> str:
    parts = [f"- #kpi {k['metric'].strip()}"]
    for key in ("baseline", "target", "read_by", "direction"):
        if k.get(key) not in (None, ""):
            val = str(k[key]).strip()
            if key == "read_by":
                check_date(val, "read_by")
            if key == "direction" and val not in ("up", "down"):
                raise SystemExit("bets: direction must be up or down")
            parts.append(f"[{key}:: {val}]")
    return " ".join(parts)


def _reading_line(r: dict) -> str:
    return f"- {check_date(r['date'], 'reading date')} #reading {r['kpi'].strip()} [value:: {str(r['value']).strip()}]"


def _blocker_line(x: dict) -> str:
    box = " " if x.get("open", True) else "x"
    return f"- [{box}] #blocker {x['text'].strip()} [opened:: {check_date(x['opened'], 'blocker opened')}]"


def _signal_line(s: dict) -> str:
    call = f" #{s['call']}" if s.get("call") else ""
    return f"- {check_date(s['date'], 'signal date')} {s['text'].strip()}{call}"


LINE_FORMATS = {"milestone": _milestone_line, "kpi": _kpi_line, "reading": _reading_line,
                "blocker": _blocker_line, "signal": _signal_line}
LIST_KEYS = {"milestone": "milestones", "kpi": "kpis", "reading": "readings",
             "blocker": "blockers", "signal": "signals"}


def template_text(vault: str) -> str:
    own = os.path.join(vault, TEMPLATE)
    return _read(own if os.path.exists(own) else BUNDLED_TEMPLATE)


def validate_new(bet: dict) -> dict:
    if not isinstance(bet, dict) or not str(bet.get("bet") or "").strip():
        raise SystemExit("bets: each bet needs a \"bet\" name")
    bet = {**bet, "bet": str(bet["bet"]).strip()}
    for k in DATE_FIELDS:
        check_date(str(bet.get(k) or ""), k)
    if bet.get("area") and bet["area"] not in AREAS:
        raise SystemExit(f"bets: area must be one of {', '.join(AREAS)}")
    if bet.get("outcome") and bet["outcome"] not in OUTCOMES:
        raise SystemExit(f"bets: outcome must be one of {', '.join(OUTCOMES)}, or left out")
    return bet


def cmd_new(vault: str, payload) -> list[str]:
    items = payload if isinstance(payload, list) else [payload]
    bets = [validate_new(b) for b in items]
    os.makedirs(bets_dir(vault), exist_ok=True)
    template = template_text(vault)
    report = []
    for b in bets:
        rel = os.path.join(BETS_DIR, safe_name(b["bet"]) + ".md")
        path = os.path.join(vault, rel)
        if os.path.exists(path):
            report.append(f"exists: {rel}")
            continue
        _write(path, render_bet(template, b))
        report.append(f"created: {rel}")
    return report


def append_line(path: str, kind: str, line: str) -> bool:
    """Add a line at the end of its section (created if missing). False if the line is already there."""
    text = _read(path)
    if read_frontmatter(text).get("type") != "bet":
        raise SystemExit(f"bets: {path} is not a bet note (frontmatter type: bet)")
    lines = text.split("\n")
    if any(l.strip() == line.strip() for l in lines):
        return False
    heading = SECTIONS[kind]
    b = section_bounds(lines, heading)
    if b is None:
        notes = section_bounds(lines, "Notes")
        at = notes[0] if notes else len(lines)
        lines[at:at] = [f"## {heading}", "", line, ""]
    else:
        start, end = b
        last = start
        for i in range(start + 1, end):
            if lines[i].strip():
                last = i
        lines.insert(last + 1, line)
        if last == start:
            lines.insert(last + 1, "")
    _write(path, "\n".join(lines))
    return True


def cmd_tick(path: str, match: str, on: str) -> str:
    text = _read(path)
    lines = text.split("\n")
    hits = [i for i, l in enumerate(lines)
            if (t := TASK_RE.match(l)) and t.group(1) == " " and (has_tag(l, "milestone") or has_tag(l, "blocker"))
            and match.lower() in l.lower()]
    if len(hits) != 1:
        raise SystemExit(f"bets: {len(hits)} open milestones or blockers match {match!r}; give a closer match")
    i = hits[0]
    lines[i] = lines[i].replace("[ ]", "[x]", 1).rstrip() + f" [done:: {on}]"
    _write(path, "\n".join(lines))
    return lines[i].strip()


def cmd_set(path: str, pairs: list[str]) -> dict:
    text = _read(path)
    if read_frontmatter(text).get("type") != "bet":
        raise SystemExit(f"bets: {path} is not a bet note (frontmatter type: bet)")
    values = {}
    for p in pairs:
        if "=" not in p:
            raise SystemExit(f"bets: expected key=value, got {p!r}")
        k, v = p.split("=", 1)
        k, v = k.strip(), v.strip()
        if k not in SETTABLE:
            raise SystemExit(f"bets: {k} is not settable; use one of {', '.join(SETTABLE)}")
        if k in DATE_FIELDS:
            check_date(v, k)
        if k == "area" and v and v not in AREAS:
            raise SystemExit(f"bets: area must be one of {', '.join(AREAS)}")
        if k == "outcome" and v and v not in OUTCOMES:
            raise SystemExit(f"bets: outcome must be one of {', '.join(OUTCOMES)}, or empty")
        values[k] = v
    _write(path, write_fields(text, values))
    return values


def kpi_names(path: str) -> list[str]:
    b = parse_bet(path)
    return [k["metric"] for k in b["kpis"]] if b else []


# ---------- the radar note ----------

STATUS_ORDER = ["off-track", "drifting", "stalled", "on-track", "upcoming", "shipped", "dropped"]
STATUS_LABEL = {"off-track": "🔴 off track", "drifting": "🟠 drifting", "stalled": "🟡 stalled",
                "on-track": "🟢 on track", "upcoming": "⚪ upcoming", "shipped": "✅ shipped", "dropped": "⚫ dropped"}
DELIVERY_ROWS = [("on-time", "Shipped on time"), ("late", "Shipped late"), ("not-shipped", "Not shipped"), ("dropped", "Dropped")]
OUTCOME_COLS = [("hit", "Hit"), ("partial", "Partial"), ("missed", "Missed"), ("not-read", "Not read"), ("no-kpi", "No KPI")]


def _cell(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def _link(b: dict) -> str:
    return f"[[{b['note']}]]"


def _kpi_cell(b: dict) -> str:
    parts = []
    for k in b["kpi_results"]:
        read = f"read {fmt_num(k['reading'])} on {short(to_date(k['read_on']))}" if k["reading"] is not None else "not read"
        parts.append(f"{k['metric']}: {fmt_num(k['baseline'])} → {fmt_num(k['target'])}, {read}")
    return "; ".join(parts) or "none set"


def radar_text(scored: list[dict], fus: list[dict], today: dt.date, area: str | None) -> str:
    counts = {s: sum(1 for b in scored if b["status"] == s) for s in STATUS_ORDER}
    summary = " · ".join(f"{n} {STATUS_LABEL[s].split(' ', 1)[1]}" for s, n in counts.items() if n)
    scope = f" ({area})" if area else ""
    out = [
        "---", "type: bet-radar", f"updated: {today.isoformat()}", "---",
        f"# Bet Radar{scope}", "",
        f"Written by `bets.py score` on {short(today)}. Each run rewrites this note; edit the bet notes instead.", "",
        f"**{len(scored)} bets** · {summary or 'none yet'}", "",
    ]
    attention = sorted((b for b in scored if b["status"] in ("off-track", "drifting", "stalled")),
                       key=lambda b: (STATUS_ORDER.index(b["status"]), b["bet"].lower()))
    out += ["## Needs attention", ""]
    if attention:
        out += ["| Bet | Owner | Status | Why |", "|---|---|---|---|"]
        out += [f"| {_link(b)} | {_cell(b['owner'] or '—')} | {STATUS_LABEL[b['status']]} | {_cell(b['status_reason'])} |" for b in attention]
    else:
        out.append("Nothing. Every active bet is on track.")
    out += ["", "## Follow-ups", ""]
    if fus:
        owner = None
        for f in fus:
            if f["owner"] != owner:
                owner = f["owner"]
                out += ([""] if out[-1] else []) + [f"**{_cell(owner)}**"]
            late = f" ({f['days_overdue']} days overdue)" if f.get("days_overdue") else ""
            out.append(f"- {_cell(f['ask'])}{late} · [[{f['note']}]]")
    else:
        out.append("None.")
    active = [b for b in scored if b["status"] in ("off-track", "drifting", "stalled", "on-track", "upcoming")]
    active.sort(key=lambda b: (STATUS_ORDER.index(b["status"]), b["cycle_end"] or "9999", b["bet"].lower()))
    out += ["", "## Active bets", ""]
    if active:
        out += ["| Bet | Owner | Area | Cycle ends | Next date | Status | Last signal |", "|---|---|---|---|---|---|---|"]
        out += [f"| {_link(b)} | {_cell(b['owner'] or '—')} | {b['area'] or 'work'} | {short(to_date(b['cycle_end'])) or '—'} | "
                f"{short(to_date(b['next_date'])) or '—'} | {STATUS_LABEL[b['status']]} | {short(to_date(b['last_signal'])) or '—'} |" for b in active]
    else:
        out.append("No active bets.")
    finished = [b for b in scored if b["delivery"] in dict(DELIVERY_ROWS)]
    out += ["", "## Scorecard", "",
            "Bets whose cycle is over: did they ship, and did the KPI move? Outcome is the user's call when set, otherwise the KPI's.", ""]
    if finished:
        out += ["| Delivery \\ Outcome | " + " | ".join(lbl for _, lbl in OUTCOME_COLS) + " | Total |",
                "|---|" + "---|" * (len(OUTCOME_COLS) + 1)]
        for key, lbl in DELIVERY_ROWS:
            row = [sum(1 for b in finished if b["delivery"] == key and b["final_outcome"] == o) for o, _ in OUTCOME_COLS]
            if sum(row):
                out.append(f"| {lbl} | " + " | ".join(str(n) if n else "·" for n in row) + f" | {sum(row)} |")
        shipped = [b for b in finished if b["delivery"] in ("on-time", "late")]
        on_time = sum(1 for b in shipped if b["delivery"] == "on-time")
        read = [b for b in finished if b["final_outcome"] in OUTCOMES]
        hits = sum(1 for b in read if b["final_outcome"] == "hit")
        out += ["",
                f"Shipped on time: {on_time} of {len(finished)}. "
                f"Outcome hit: {hits} of {len(read)} with a result."
                + (f" {len(finished) - len(read)} still have no result." if len(finished) > len(read) else ""),
                "",
                "| Bet | Owner | Cycle | Delivery | Outcome | KPI |", "|---|---|---|---|---|---|"]
        finished.sort(key=lambda b: (b["cycle_end"] or "", b["bet"].lower()), reverse=True)
        for b in finished:
            outcome = b["final_outcome"] + (" (owner's call)" if b["outcome_by"] == "user" else "")
            out.append(f"| {_link(b)} | {_cell(b['owner'] or '—')} | {_cell(b['cycle'] or short(to_date(b['cycle_end'])) or '—')} | "
                       f"{b['delivery']} | {outcome} | {_cell(_kpi_cell(b))} |")
    else:
        out.append("No finished bets yet.")
    where = f'"{BETS_DIR}"'
    area_filter = f' AND area = "{area}"' if area else ""
    out += ["", "## Live view", "",
            "Dataview reads the status fields this script wrote into each bet note.", "",
            "```dataview",
            'TABLE WITHOUT ID file.link AS "Bet", owner AS "Owner", status AS "Status", status_reason AS "Why", '
            'delivery AS "Delivery", default(outcome, kpi_result) AS "Outcome"',
            f'FROM {where}',
            f'WHERE type = "bet"{area_filter}',
            "SORT status ASC, cycle_end ASC",
            "```", ""]
    return "\n".join(out)


def cmd_score(vault: str, today: dt.date, t: Thresholds, area: str | None, out_rel: str | None) -> dict:
    scored = [score_bet(b, today, t) for b in all_bets(vault)]
    changed = 0
    for b in scored:
        text = _read(b["file"])
        fm = read_frontmatter(text)
        values = {k: b[k] for k in SCORE_FIELDS}
        if any(str(fm.get(k, "")) != str(v) for k, v in values.items()):
            _write(b["file"], write_fields(text, values))
            changed += 1
    shown = [b for b in scored if not area or (b["area"] or "work") == area]
    fus = follow_ups(shown, today, t)
    rel = out_rel or os.path.join(BETS_DIR, RADAR_NOTE)
    path = os.path.join(vault, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _write(path, radar_text(shown, fus, today, area))
    return {"date": today.isoformat(), "radar": rel, "bets": len(shown), "notes_updated": changed,
            "status": {s: sum(1 for b in shown if b["status"] == s) for s in STATUS_ORDER},
            "follow_ups": len(fus)}


def public(b: dict) -> dict:
    return {k: v for k, v in b.items() if k != "file"}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", help="vault root (default: $VAULT_OS_VAULT_ROOT, then the current directory)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("new")
    s = sub.add_parser("signal"); s.add_argument("file"); s.add_argument("text"); s.add_argument("--date"); s.add_argument("--call", choices=CALLS)
    b = sub.add_parser("blocker"); b.add_argument("file"); b.add_argument("text"); b.add_argument("--date")
    m = sub.add_parser("milestone"); m.add_argument("file"); m.add_argument("text"); m.add_argument("--due", required=True)
    tk = sub.add_parser("tick"); tk.add_argument("file"); tk.add_argument("match"); tk.add_argument("--date")
    k = sub.add_parser("kpi"); k.add_argument("file"); k.add_argument("metric"); k.add_argument("--target", required=True)
    k.add_argument("--baseline"); k.add_argument("--read-by"); k.add_argument("--direction", choices=("up", "down"))
    r = sub.add_parser("reading"); r.add_argument("file"); r.add_argument("metric"); r.add_argument("value"); r.add_argument("--date")
    st = sub.add_parser("set"); st.add_argument("file"); st.add_argument("pairs", nargs="+")
    for name in ("list", "follow-ups", "score"):
        p = sub.add_parser(name); p.add_argument("--today")
        for flag in ("--blocker-days", "--stale-days", "--warn-days"):
            p.add_argument(flag, type=int)
        if name == "score":
            p.add_argument("--area", choices=AREAS); p.add_argument("--out")
    a = ap.parse_args(argv)
    v = resolve_vault(a.vault)
    t = load_thresholds(v, {k: getattr(a, k, None) for k in ("blocker_days", "stale_days", "warn_days")})
    today_s = dt.date.today().isoformat()

    def resolve(f: str) -> str:
        """A path, a note name in bets/, or a bet's name."""
        base = [f] if os.path.isabs(f) else [os.path.join(v, f), os.path.join(v, BETS_DIR, f), os.path.join(v, BETS_DIR, safe_name(f))]
        for p in base + [p + ".md" for p in base]:
            if os.path.isfile(p):
                return p
        named = [b["file"] for b in all_bets(v) if b["bet"].lower() == f.strip().lower()]
        if len(named) == 1:
            return named[0]
        raise SystemExit(f"bets: no bet note matches {f!r}")

    def day(s: str | None) -> str:
        return check_date(s, "--date") if s else today_s

    if a.cmd == "new":
        print("\n".join(cmd_new(v, json.load(sys.stdin))))
    elif a.cmd == "signal":
        added = append_line(resolve(a.file), "signal", _signal_line({"date": day(a.date), "text": a.text, "call": a.call}))
        print("added" if added else "already there")
    elif a.cmd == "blocker":
        added = append_line(resolve(a.file), "blocker", _blocker_line({"text": a.text, "opened": day(a.date)}))
        print("added" if added else "already there")
    elif a.cmd == "milestone":
        added = append_line(resolve(a.file), "milestone", _milestone_line({"text": a.text, "due": a.due}))
        print("added" if added else "already there")
    elif a.cmd == "tick":
        print(cmd_tick(resolve(a.file), a.match, day(a.date)))
    elif a.cmd == "kpi":
        line = _kpi_line({"metric": a.metric, "baseline": a.baseline, "target": a.target, "read_by": a.read_by, "direction": a.direction})
        print("added" if append_line(resolve(a.file), "kpi", line) else "already there")
    elif a.cmd == "reading":
        path = resolve(a.file)
        names = kpi_names(path)
        match = next((n for n in names if n.lower() == a.metric.strip().lower()), None)
        if not match:
            raise SystemExit(f"bets: no KPI named {a.metric!r} in this bet; KPIs: {', '.join(names) or 'none'}")
        if to_num(a.value) is None:
            raise SystemExit(f"bets: reading must contain a number, got {a.value!r}")
        added = append_line(path, "reading", _reading_line({"date": day(a.date), "kpi": match, "value": a.value}))
        print("added" if added else "already there")
    elif a.cmd == "set":
        print(json.dumps(cmd_set(resolve(a.file), a.pairs)))
    else:
        today = to_date(check_date(a.today, "--today")) if a.today else dt.date.today()
        if a.cmd == "score":
            print(json.dumps(cmd_score(v, today, t, a.area, a.out), indent=2))
        else:
            scored = [score_bet(b, today, t) for b in all_bets(v)]
            if a.cmd == "list":
                print(json.dumps([public(b) for b in scored], indent=2, ensure_ascii=False))
            else:
                print(json.dumps(follow_ups(scored, today, t), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
