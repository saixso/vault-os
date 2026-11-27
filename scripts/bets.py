#!/usr/bin/env python3
"""Deterministic helpers for the vault-os bets skill.

A bet is one note in the vault's bets/ folder. The person who owns the bet
sets its status (in progress, paused, or done) and, when they choose, a
rating (won, lost, or push). Following Thinking in Bets, they also write the
odds they give the bet, what would prove it wrong and what is at stake
(small, medium, or large, and what they would lose) when they place it, and
at the close they rate the decision (good or bad) apart from the result.
This script creates notes from the template, records those fields, and
rewrites the radar. It does not decide whether a bet is done, and it does not
rate a result or a decision.
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
  bets.py set FILE key=value ...      (owner, area, cycle, status, rating, why, value, odds,
                                       wrong_if, stake, stake_note, decision, and the
                                       older cycle fields still on existing notes)
  bets.py list [--today D]            (JSON: every bet)
  bets.py follow-ups [--today D]      (JSON: asks for each owner)
  bets.py score [--today D] [--area work|life] [--out NOTE]
                                      (rewrite the radar from the status and rating already on each note)

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
USER_FIELDS = ["bet", "owner", "area", "cycle", "status", "rating", "why", "value",
               "odds", "wrong_if", "stake", "stake_note", "decision",
               "appetite", "cycle_start", "cycle_end", "started", "shipped", "dropped",
               "outcome", "source"]
DATE_FIELDS = {"cycle_start", "cycle_end", "started", "shipped", "dropped"}
SETTABLE = [f for f in USER_FIELDS if f not in ("bet", "source")]

AREAS = ("work", "life")
STATUSES = ("in progress", "paused", "done")
RATINGS = ("won", "lost", "push")
DECISIONS = ("good", "bad")
STAKES = ("small", "medium", "large")
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
    """Read the status and rating the user wrote. Do not invent either."""
    odds = parse_odds(bet.get("odds"))
    return {
        **bet,
        "status": _canon(bet.get("status"), STATUSES),
        "rating": _canon(bet.get("rating"), RATINGS),
        "decision": _canon(bet.get("decision"), DECISIONS),
        "stake": _canon(bet.get("stake"), STAKES),
        "odds": "" if odds is None else odds,
    }


def _next_date(bet: dict, today: dt.date) -> str:
    dates = [to_date(m["due"]) for m in bet["milestones"] if not m["done"]] + [to_date(bet["cycle_end"])]
    ahead = sorted(d for d in dates if d and d >= today)
    return ahead[0].isoformat() if ahead else ""


def follow_ups(scored: list[dict], today: dt.date, t: Thresholds) -> list[dict]:
    """What to ask whom. Status, rating, odds and the decision call are the user's to set.
    Odds are asked for only while a bet is in progress: written after the result is
    known, they would only record hindsight."""
    out = []
    for b in scored:
        owner = b["owner"].strip() or "(no owner)"

        def ask(kind, text):
            out.append({"owner": owner, "bet": b["bet"], "note": b["note"], "kind": kind, "ask": text,
                        "days_overdue": None})

        if not b["owner"].strip():
            ask("owner", "Name an owner for this bet")
        if not b["status"]:
            ask("status", "Set the status: in progress, paused, or done")
        elif b["status"] == "in progress" and (b["odds"] == "" or not str(b.get("wrong_if") or "").strip()):
            ask("odds", "Write the odds you give it and what would prove it wrong")
        elif b["status"] == "in progress" and not b["stake"]:
            ask("stake", "Say what is at stake: small, medium, or large, and what you would lose")
        elif b["status"] == "done" and not b["rating"] and not b["decision"]:
            ask("rating", "Rate the result (won, lost, or push) and, apart from it, the decision (good or bad)")
        elif b["status"] == "done" and not b["rating"]:
            ask("rating", "Rate the result: won, lost, or push")
        elif b["status"] == "done" and not b["decision"]:
            ask("decision", "Rate the decision as it was made, apart from the result: good or bad")
    order = {"owner": 0, "status": 1, "odds": 2, "stake": 3, "rating": 4, "decision": 5}
    out.sort(key=lambda f: (f["owner"].lower(), order[f["kind"]], f["bet"].lower()))
    return out


# ---------- writing notes ----------

def render_bet(template: str, bet: dict) -> str:
    def lines(kind: str) -> str:
        return "\n".join(LINE_FORMATS[kind](x) for x in bet.get(LIST_KEYS[kind]) or [])

    if template.startswith("---\n") and "\n---\n" in template[4:]:
        fm, body = template[4:].split("\n---\n", 1)
        fm_prefix = "---\n"
        fm_suffix = "\n---\n"
    else:
        fm, body = "", template
        fm_prefix = fm_suffix = ""
    yaml_map = {k: yaml_value(bet.get(k)) for k in USER_FIELDS}
    yaml_map["area"] = yaml_map["area"] or "work"
    raw_map = {k: "" if bet.get(k) is None else str(bet.get(k)).strip() for k in USER_FIELDS}
    raw_map["area"] = raw_map["area"] or "work"
    for k, v in yaml_map.items():
        fm = fm.replace("{{" + k + "}}", v)
    for k, v in raw_map.items():
        body = body.replace("{{" + k + "}}", v)
    body = body.replace("{{problem}}", (bet.get("problem") or bet.get("why") or "").strip())
    at_stake = [str(bet.get(k) or "").strip() for k in ("stake", "stake_note")]
    body = body.replace("{{at_stake}}", ": ".join(x for x in at_stake if x))
    for kind in LIST_KEYS:
        body = body.replace("{{" + LIST_KEYS[kind] + "}}", lines(kind))
    body = re.sub(r"^# .*$", lambda _: f"# {bet['bet']}", body, count=1, flags=re.M)
    text = fm_prefix + fm + fm_suffix + body
    text = re.sub(r"[ \t]+$", "", text, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", text)


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


def _canon(value, allowed: tuple[str, ...]) -> str:
    s = str(value or "").strip().lower()
    return s if s in allowed else ""


def parse_odds(value) -> int | None:
    """The odds the user gives a bet, as a whole percent from 0 to 100.
    Takes 60, 60%, or 0.6. None when blank or not one of those."""
    s = str(value or "").strip().rstrip("%").strip()
    if not s or not re.fullmatch(r"\d+(\.\d+)?", s):
        return None
    x = float(s)
    if "." in s and x <= 1 and not str(value).strip().endswith("%"):
        x *= 100
    return int(round(x)) if 0 <= x <= 100 else None


def check_odds(value) -> str:
    if str(value or "").strip() == "":
        return ""
    n = parse_odds(value)
    if n is None:
        raise SystemExit(f"bets: odds must be a percent from 0 to 100 (60, 60% or 0.6), got {value!r}")
    return str(n)


def validate_new(bet: dict) -> dict:
    if not isinstance(bet, dict) or not str(bet.get("bet") or "").strip():
        raise SystemExit("bets: each bet needs a \"bet\" name")
    bet = {**bet, "bet": str(bet["bet"]).strip()}
    if not str(bet.get("why") or "").strip() and str(bet.get("problem") or "").strip():
        bet["why"] = str(bet["problem"]).strip()
    for k in DATE_FIELDS:
        check_date(str(bet.get(k) or ""), k)
    if bet.get("area") and bet["area"] not in AREAS:
        raise SystemExit(f"bets: area must be one of {', '.join(AREAS)}")
    if bet.get("outcome") and bet["outcome"] not in OUTCOMES:
        raise SystemExit(f"bets: outcome must be one of {', '.join(OUTCOMES)}, or left out")
    if str(bet.get("status") or "").strip() and not _canon(bet.get("status"), STATUSES):
        raise SystemExit(f"bets: status must be one of {', '.join(STATUSES)}")
    if str(bet.get("rating") or "").strip() and not _canon(bet.get("rating"), RATINGS):
        raise SystemExit(f"bets: rating must be one of {', '.join(RATINGS)}, or left out")
    if str(bet.get("decision") or "").strip() and not _canon(bet.get("decision"), DECISIONS):
        raise SystemExit(f"bets: decision must be one of {', '.join(DECISIONS)}, or left out")
    bet["status"] = _canon(bet.get("status"), STATUSES) or "in progress"
    bet["rating"] = _canon(bet.get("rating"), RATINGS)
    if str(bet.get("stake") or "").strip() and not _canon(bet.get("stake"), STAKES):
        raise SystemExit(f"bets: stake must be one of {', '.join(STAKES)}, or left out")
    bet["decision"] = _canon(bet.get("decision"), DECISIONS)
    bet["stake"] = _canon(bet.get("stake"), STAKES)
    bet["odds"] = check_odds(bet.get("odds"))
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
        if k == "status":
            if v and not _canon(v, STATUSES):
                raise SystemExit(f"bets: status must be one of {', '.join(STATUSES)}")
            v = _canon(v, STATUSES)
        if k == "rating":
            if v and not _canon(v, RATINGS):
                raise SystemExit(f"bets: rating must be one of {', '.join(RATINGS)}, or empty")
            v = _canon(v, RATINGS)
        if k == "decision":
            if v and not _canon(v, DECISIONS):
                raise SystemExit(f"bets: decision must be one of {', '.join(DECISIONS)}, or empty")
            v = _canon(v, DECISIONS)
        if k == "stake":
            if v and not _canon(v, STAKES):
                raise SystemExit(f"bets: stake must be one of {', '.join(STAKES)}, or empty")
            v = _canon(v, STAKES)
        if k == "odds":
            v = check_odds(v)
        values[k] = v
    new_text = write_fields(text, values)
    new_text, left = sync_sections(read_frontmatter(text), read_frontmatter(new_text), new_text)
    _write(path, new_text)
    for heading in left:
        print(f"bets: left the {heading} section as it is, because it was edited by hand; "
              f"update it in the note if it should match", file=sys.stderr)
    return values


# A section in the note's body that repeats a frontmatter field, as the starter template writes it.
SECTION_FIELDS = {
    "Why": lambda fm: fm.get("why", ""),
    "Proved wrong if": lambda fm: fm.get("wrong_if", ""),
    "At stake": lambda fm: ": ".join(x for x in (fm.get("stake", ""), fm.get("stake_note", "")) if x),
    "Value": lambda fm: fm.get("value", ""),
}


def sync_sections(old_fm: dict, new_fm: dict, text: str) -> tuple[str, list[str]]:
    """Rewrite the body sections whose field changed.

    A section is rewritten only when it still holds the old field text, or nothing,
    so text the user wrote there by hand is kept. Returns the new text and the
    headings left alone for that reason."""
    left = []
    for heading, field_text in SECTION_FIELDS.items():
        old, new = field_text(old_fm).strip(), field_text(new_fm).strip()
        if old == new:
            continue
        m = re.search(r"^## " + re.escape(heading) + r"[ \t]*\n(.*?)(?=^#{1,2} |\Z)", text, re.M | re.S)
        if not m:
            continue
        current = m.group(1).strip()
        if current not in ("", old):
            left.append(heading)
            continue
        body = f"\n{new}\n\n" if new else "\n"
        text = text[:m.start(1)] + body + text[m.end(1):]
    return text, left


def kpi_names(path: str) -> list[str]:
    b = parse_bet(path)
    return [k["metric"] for k in b["kpis"]] if b else []


# ---------- the radar note ----------

STATUS_ORDER = ["in progress", "paused", "done"]
STATUS_LABEL = {"in progress": "In progress", "paused": "Paused", "done": "Done"}


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


def _odds_cell(b: dict) -> str:
    return f"{b['odds']}%" if b.get("odds") != "" and b.get("odds") is not None else "—"


ROW_HEAD = ["| Bet | Owner | Odds | Stake | Decision | Rating | Value |", "|---|---|---|---|---|---|---|"]


def _bet_row(b: dict) -> str:
    return (f"| {_link(b)} | {_cell(b['owner'] or '—')} | {_odds_cell(b)} | {b.get('stake') or '—'} "
            f"| {b.get('decision') or '—'} | {b['rating'] or '—'} | {_cell(b.get('value') or '—')} |")


GRID_RESULTS = ["won", "push", "lost"]
GRID_LABEL = {
    ("good", "won"): "Earned it", ("good", "push"): "Good call, even", ("good", "lost"): "Bad luck",
    ("bad", "won"): "Got lucky", ("bad", "push"): "Bad call, even", ("bad", "lost"): "Learn from it",
}


def grid_text(done: list[dict]) -> list[str]:
    """Decision against result for done bets: a good call can lose and a bad call can win."""
    rated = [b for b in done if b["decision"] and b["rating"]]
    out = ["## Decision against result", "",
           "Done bets the user rated twice: the decision as it was made, and the result.", ""]
    if not rated:
        return out + ["None rated both ways yet.", ""]
    out += ["| Decision | Won | Push | Lost |", "|---|---|---|---|"]
    for d in DECISIONS:
        cells = []
        for r in GRID_RESULTS:
            names = sorted((b for b in rated if b["decision"] == d and b["rating"] == r), key=lambda b: b["bet"].lower())
            links = ", ".join(_link(b) for b in names)
            cells.append(f"{GRID_LABEL[(d, r)]}: {len(names)}" + (f"<br>{links}" if links else ""))
        out.append(f"| {d.capitalize()} | " + " | ".join(cells) + " |")
    out.append("")
    missing = [b for b in done if not (b["decision"] and b["rating"])]
    if missing:
        out += [f"{len(missing)} done {'bet is' if len(missing) == 1 else 'bets are'} missing a decision or a result rating.", ""]
    return out


def calibration(done: list[dict]) -> dict | None:
    """Average odds against how often the bets won, for done bets with odds and a won or lost result.
    A push counts toward neither."""
    rows = [b for b in done if b["odds"] != "" and b["rating"] in ("won", "lost")]
    if not rows:
        return None
    avg = sum(b["odds"] for b in rows) / len(rows)
    won = sum(1 for b in rows if b["rating"] == "won")
    return {"bets": len(rows), "average_odds": round(avg), "won": won, "win_rate": round(100 * won / len(rows))}


def by_stake(done: list[dict]) -> dict:
    """For each stake, done bets with a won or lost result: how many, how many won, and
    the average odds where given. A push counts toward neither. Stakes with no such bet are left out."""
    out = {}
    for st in STAKES:
        rows = [b for b in done if b["stake"] == st and b["rating"] in ("won", "lost")]
        if not rows:
            continue
        won = sum(1 for b in rows if b["rating"] == "won")
        odds = [b["odds"] for b in rows if b["odds"] != ""]
        out[st] = {"bets": len(rows), "won": won, "win_rate": round(100 * won / len(rows)),
                   "average_odds": round(sum(odds) / len(odds)) if odds else None}
    return out


def stake_text(stakes: dict) -> list[str]:
    out = ["## Results by stake", ""]
    if not stakes:
        return out + ["No done bet has both a stake and a won or lost result yet.", ""]
    out += ["| Stake | Bets | Won | Win rate | Average odds |", "|---|---|---|---|---|"]
    for st in STAKES:
        if st in stakes:
            r = stakes[st]
            odds = f"{r['average_odds']}%" if r["average_odds"] is not None else "—"
            out.append(f"| {st.capitalize()} | {r['bets']} | {r['won']} | {r['win_rate']}% | {odds} |")
    return out + [""]


def calibration_text(cal: dict | None) -> list[str]:
    out = ["## Odds against results", ""]
    if not cal:
        return out + ["No done bet has both odds and a won or lost result yet.", ""]
    n = cal["bets"]
    gap = cal["average_odds"] - cal["win_rate"]
    if abs(gap) < 10:
        read = "The odds and the results are within 10 points."
    elif gap > 0:
        read = f"The odds ran {gap} points above the results."
    else:
        read = f"The results ran {-gap} points above the odds."
    out.append(f"{n} {'bet' if n == 1 else 'bets'} with odds and a won or lost result: average odds "
               f"{cal['average_odds']}%, {cal['won']} of {n} won ({cal['win_rate']}%). {read}")
    if n < 10:
        out.append("")
        out.append(f"With {n} {'bet' if n == 1 else 'bets'}, this gap says little yet.")
    return out + [""]


def radar_text(scored: list[dict], fus: list[dict], today: dt.date, area: str | None) -> str:
    groups = {s: [b for b in scored if b["status"] == s] for s in STATUS_ORDER}
    unset = [b for b in scored if not b["status"]]
    counts = {s: len(groups[s]) for s in STATUS_ORDER}
    summary = " · ".join(f"{n} {STATUS_LABEL[s].lower()}" for s, n in counts.items() if n)
    if unset:
        summary = (summary + " · " if summary else "") + f"{len(unset)} not set"
    scope = f" ({area})" if area else ""
    out = [
        "---", "type: bet-radar", f"updated: {today.isoformat()}", "---",
        f"# Bet Radar{scope}", "",
        f"Written by `bets.py score` on {short(today)}. Each run rewrites this note. Status, odds, stake, decision and rating are set on the bet notes.", "",
        f"**{len(scored)} bets** · {summary or 'none yet'}", "",
    ]
    for s in STATUS_ORDER:
        rows = sorted(groups[s], key=lambda b: b["bet"].lower())
        out += [f"## {STATUS_LABEL[s]}", ""]
        if rows:
            out += ROW_HEAD
            out += [_bet_row(b) for b in rows]
        else:
            out.append("None.")
        out.append("")
    out += ["## Not set", ""]
    if unset:
        out += ROW_HEAD
        out += [_bet_row(b) for b in sorted(unset, key=lambda b: b["bet"].lower())]
    else:
        out.append("None.")
    out += [""]
    out += grid_text(groups["done"])
    out += calibration_text(calibration(groups["done"]))
    out += stake_text(by_stake(groups["done"]))
    out += ["## Follow-ups", ""]
    if fus:
        owner = None
        for f in fus:
            if f["owner"] != owner:
                owner = f["owner"]
                out += ([""] if out[-1] else []) + [f"**{_cell(owner)}**"]
            out.append(f"- {_cell(f['ask'])} · [[{f['note']}]]")
    else:
        out.append("None.")
    where = f'"{BETS_DIR}"'
    area_filter = f' AND area = "{area}"' if area else ""
    out += ["", "## Live view", "",
            "Dataview reads the status, odds, stake, decision and rating on each bet note.", "",
            "```dataview",
            'TABLE WITHOUT ID file.link AS "Bet", owner AS "Owner", status AS "Status", odds AS "Odds", '
            'stake AS "Stake", decision AS "Decision", rating AS "Rating", value AS "Value"',
            f'FROM {where}',
            f'WHERE type = "bet"{area_filter}',
            "SORT status ASC, file.name ASC",
            "```", "",
            "Done bets by decision and result:", "",
            "```dataview",
            'TABLE WITHOUT ID key AS "Decision, result", length(rows) AS "Bets", rows.file.link AS "Which"',
            f'FROM {where}',
            f'WHERE type = "bet" AND status = "done" AND decision AND rating{area_filter}',
            'GROUP BY decision + ", " + rating',
            "SORT key ASC",
            "```", ""]
    return "\n".join(out)


def cmd_score(vault: str, today: dt.date, t: Thresholds, area: str | None, out_rel: str | None) -> dict:
    scored = [score_bet(b, today, t) for b in all_bets(vault)]
    shown = [b for b in scored if not area or (b["area"] or "work") == area]
    fus = follow_ups(shown, today, t)
    rel = out_rel or os.path.join(BETS_DIR, RADAR_NOTE)
    path = os.path.join(vault, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _write(path, radar_text(shown, fus, today, area))
    counts = {s: sum(1 for b in shown if b["status"] == s) for s in STATUS_ORDER}
    counts["not set"] = sum(1 for b in shown if not b["status"])
    done = [b for b in shown if b["status"] == "done"]
    grid = {f"{d}, {r}": sum(1 for b in done if b["decision"] == d and b["rating"] == r)
            for d in DECISIONS for r in GRID_RESULTS}
    return {"date": today.isoformat(), "radar": rel, "bets": len(shown), "notes_updated": 0,
            "status": counts, "decision_vs_result": grid, "calibration": calibration(done),
            "by_stake": by_stake(done),
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
