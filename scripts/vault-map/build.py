#!/usr/bin/env python3
"""Build the vault map: a strategy-game view of an Obsidian vault.

Reads note paths, frontmatter and [[wikilinks]] only. It never prints or keeps
note text, and it writes nothing unless an output path is given.

What it computes (same notes in, same map out):
  territories  communities of linked concept notes (Louvain over links),
               named by their most-linked concept unless the config renames them
  terrain      each concept's maturity from `status:` (core, developing, seed)
  turns        months, from each note's `created:` date
  roads        idea -> bet -> built -> finished, from idea `solves:` and
               `became_bet:`, problem `ideas:`, bet `from_ideas:`, bet `shipped`,
               `delivery`, `kpi_result` and `outcome`, and plain links between them
  unlocks      pairs of territories with many concept links across their border
               and no idea or insight note that joins them
  fog          problem notes that no idea links to
  frontier     concepts in clusters too small to be a territory

Which notes count is set by path patterns and `type:` (see DEFAULTS). A note
whose `type:` is something else (a radar, a plan) is left out.

The vault is --vault, else $VAULT_OS_VAULT_ROOT, else the current directory.
Config is --config, else VAULT/dashboards/vault-map-config.json when present.
Standard library only.

Usage:
  build.py [--vault V] [--config F] [--today YYYY-MM-DD]
           [--json OUT] [--html OUT] [--summary]

With no --json, --html or --summary, the map data is printed as JSON.
--html writes one self-contained page (scripts/vault-map/map.html with the data in it).
--summary prints a short turn report in Markdown, for a weekly note.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import fnmatch
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "map.html")
DATA_MARK = "/*VAULT_MAP_DATA*/null"

DEFAULTS = {
    # Path patterns (fnmatch, case-sensitive, `*` crosses folders) per kind. First match wins.
    "kinds": {
        "concept": ["wiki/concepts/*", "concepts/*"],
        "idea": ["wiki/ideas/*", "ideas/*", "* Ideas/*"],
        "problem": ["wiki/problems/*", "problems/*", "* Problems/*"],
        "bet": ["bets/*", "wiki/pitches/*"],
        "decision": ["wiki/decisions/*", "decisions/*", "* Decisions/*"],
        "insight": ["wiki/insights/*", "insights/*", "* Insights/*"],
    },
    # `type:` values that place a note anywhere in the vault, and those that keep a note in its kind.
    "types": {"concept": "concept", "idea": "idea", "problem": "problem", "bet": "bet",
              "pitch": "bet", "decision": "decision", "insight": "insight"},
    "skip": ["inbox/*", "wiki/sources/*", "wiki/entities/*", "meetings/*", "people/*",
             "Archives/*", "archive/*", "templates/*", "reviews/*", "dashboards/*"],
    "skip_names": ["README", "index", "_index", "AGENTS", "CLAUDE", "Bet Radar"],
    "skip_tags": ["moc", "type/moc", "dashboard", "type/dashboard"],
    "need_frontmatter": True,  # a note with no frontmatter is a guide or scratch page, not mapped
    "maturity": {"evergreen": "core", "mature": "core", "done": "core",
                 "developing": "developing", "growing": "developing", "active": "developing",
                 "seed": "seed", "stub": "seed", "draft": "seed", "seedling": "seed"},
    "min_territory": 8,       # concepts a cluster needs to be a territory
    "max_territories": 10,
    "min_unlock_links": 3,    # concept links across a border before it can be an unlock
    "max_unlocks": 5,
    "resolution": 1.0,        # higher gives more, smaller territories
    "names": {},              # {"Hub concept note": "Territory name"}
    "merge": {},              # {"Hub concept note": "Hub concept note it joins"}
    "vault_name": "",         # for obsidian:// links; defaults to the vault folder name
}

LINK_FIELDS = ("related", "solves", "ideas", "from_ideas", "became_bet", "problems", "bets", "up", "parent")
LINK_RE = re.compile(r"\[\[([^\]|#^]+)")
KEY_RE = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*)$")
MONTH_RE = re.compile(r"^(\d{4})-(\d{2})")
FINISHED = {"hit", "partial", "missed"}
BUILT = {"on-time", "late"}
STAGES = ["idea", "tied", "bet", "built", "finished"]


# ---------- vault and config ----------

def resolve_vault(arg: str | None) -> str:
    v = os.path.abspath(arg or os.environ.get("VAULT_OS_VAULT_ROOT") or os.getcwd())
    if not any(os.path.isdir(os.path.join(v, d)) for d in (".obsidian", "wiki", "templates")):
        raise SystemExit(f"vault-map: {v} does not look like an Obsidian vault (no .obsidian/, wiki/ or templates/); pass --vault")
    return v


def load_config(vault: str, path: str | None) -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))
    path = path or os.path.join(vault, "dashboards", "vault-map-config.json")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            user = json.load(fh)
        for k, v in user.items():
            if k not in cfg:
                raise SystemExit(f"vault-map: unknown config key {k!r} in {path}")
            if isinstance(cfg[k], dict) and isinstance(v, dict) and k in ("kinds", "types", "maturity"):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


# ---------- reading notes ----------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Flat YAML frontmatter: scalars, inline [a, b] lists and `- item` lists."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    head, body = text[4:end], text[end + 4:]
    fm: dict = {}
    key = None
    for line in head.split("\n"):
        m = KEY_RE.match(line)
        if m:
            key, val = m.group(1).lower(), m.group(2).strip()
            if val.startswith("[") and val.endswith("]") and not val.startswith("[["):
                fm[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
            elif val:
                fm[key] = val.strip("'\"")
            else:
                fm[key] = []
        elif key and line.strip().startswith("- "):
            if not isinstance(fm.get(key), list):
                fm[key] = [fm[key]] if fm.get(key) else []
            fm[key].append(line.strip()[2:].strip().strip("'\""))
        elif line.strip() and not line.startswith((" ", "\t")):
            key = None
    return fm, body


def as_list(v) -> list[str]:
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    return [v] if isinstance(v, str) and v.strip() else []


def text_of(fm: dict, k: str) -> str:
    v = fm.get(k)
    return v.strip() if isinstance(v, str) else ""


def link_target(s: str) -> str:
    s = s.strip()
    m = LINK_RE.search(s)
    if m:
        s = m.group(1)
    s = s.split("|")[0].split("#")[0].strip()
    if s.endswith(".md"):
        s = s[:-3]
    return s.split("/")[-1].strip().lower()


def month(v) -> str:
    m = MONTH_RE.match(str(v or "").strip())
    return f"{m.group(1)}-{m.group(2)}" if m else ""


def matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, p) for p in patterns)


def note_kind(path: str, fm: dict, cfg: dict) -> str | None:
    name = os.path.basename(path)[:-3]
    if name in cfg["skip_names"] or name.startswith("_") or matches(path, cfg["skip"]):
        return None
    if cfg["need_frontmatter"] and not fm:
        return None
    tags = {x.lstrip("#").lower() for x in as_list(fm.get("tags"))}
    if tags & {x.lower() for x in cfg["skip_tags"]}:
        return None
    t = text_of(fm, "type").lower()
    by_path = next((k for k, pats in cfg["kinds"].items() if matches(path, pats)), None)
    if t:
        return cfg["types"].get(t) if (by_path or t in cfg["types"]) else None
    return by_path


def load_notes(vault: str, cfg: dict) -> dict[str, dict]:
    notes: dict[str, dict] = {}
    for root, dirs, files in os.walk(vault):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for f in sorted(files):
            if not f.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(root, f), vault).replace(os.sep, "/")
            try:
                with open(os.path.join(root, f), encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            fm, body = parse_frontmatter(text)
            kind = note_kind(rel, fm, cfg)
            if not kind:
                continue
            links = [link_target(x) for x in LINK_RE.findall(body)]
            for k in LINK_FIELDS:
                links += [link_target(x) for x in as_list(fm.get(k))]
            notes[rel] = {"path": rel, "name": f[:-3], "kind": kind, "fm": fm,
                          "aliases": as_list(fm.get("aliases")), "raw_links": [l for l in links if l]}
    return notes


def resolve_links(notes: dict[str, dict]) -> dict[str, set[str]]:
    """Undirected neighbours between mapped notes, by note name or alias."""
    by_name: dict[str, str] = {}
    for p in sorted(notes):
        for n in [notes[p]["name"]] + notes[p]["aliases"]:
            by_name.setdefault(n.strip().lower(), p)
    adj: dict[str, set[str]] = {p: set() for p in notes}
    for p, n in notes.items():
        for l in n["raw_links"]:
            q = by_name.get(l)
            if q and q != p:
                adj[p].add(q)
                adj[q].add(p)
    return adj


# ---------- territories ----------

def clusters(concepts: list[str], adj: dict[str, set[str]], resolution: float) -> list[list[str]]:
    """Louvain communities over concept-to-concept links. Nodes are visited in
    sorted order and ties keep the current community, so runs agree."""
    cset = set(concepts)
    g: dict = {p: collections.Counter({q: 1 for q in adj[p] if q in cset}) for p in concepts}
    part = {p: p for p in concepts}
    while True:
        nodes = sorted(g)
        k = {u: sum(g[u].values()) for u in nodes}
        m2 = sum(k.values()) or 1
        comm = {u: u for u in nodes}
        tot = dict(k)
        moved_any = False
        while True:
            moved = 0
            for u in nodes:
                if not k[u]:
                    continue
                cu = comm[u]
                kin = collections.Counter()
                for v, x in g[u].items():
                    if v != u:
                        kin[comm[v]] += x
                tot[cu] -= k[u]
                best, best_gain = cu, kin.get(cu, 0) - resolution * tot[cu] * k[u] / m2
                for c in sorted(kin):
                    gain = kin[c] - resolution * tot[c] * k[u] / m2
                    if gain > best_gain + 1e-9:
                        best, best_gain = c, gain
                tot[best] += k[u]
                if best != cu:
                    comm[u] = best
                    moved += 1
                    moved_any = True
            if not moved:
                break
        if not moved_any:
            break
        part = {p: comm[part[p]] for p in part}
        agg: dict = collections.defaultdict(collections.Counter)
        for u in nodes:
            agg[comm[u]]
            for v, x in g[u].items():
                agg[comm[u]][comm[v]] += x
        g = dict(agg)
    groups = collections.defaultdict(list)
    for p in sorted(part):
        groups[part[p]].append(p)
    return sorted(groups.values(), key=lambda grp: (-len(grp), grp[0]))


def hub(group: list[str], adj: dict[str, set[str]], notes: dict) -> str:
    return sorted(group, key=lambda p: (-len(adj[p]), notes[p]["name"]))[0]


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "t"


# ---------- the map ----------

def turns_between(first: str, last: str) -> list[str]:
    y, m = int(first[:4]), int(first[5:7])
    out = []
    while f"{y:04d}-{m:02d}" <= last:
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def build(vault: str, cfg: dict, today: dt.date) -> dict:
    notes = load_notes(vault, cfg)
    adj = resolve_links(notes)
    of = lambda k: sorted(p for p, n in notes.items() if n["kind"] == k)  # noqa: E731
    concepts, ideas, problems, bets = of("concept"), of("idea"), of("problem"), of("bet")
    bridges_kinds = {"idea", "insight"}

    # Clusters -> territories (after optional merges), the rest is frontier.
    groups = clusters(concepts, adj, float(cfg["resolution"]))
    by_hub = {notes[hub(g, adj, notes)]["name"]: g for g in groups if len(g) > 1}
    for src, dst in cfg["merge"].items():
        if src in by_hub and dst in by_hub and src != dst:
            by_hub[dst] = by_hub[dst] + by_hub.pop(src)
    big = sorted((g for g in by_hub.values() if len(g) >= cfg["min_territory"]), key=lambda g: (-len(g), g[0]))
    big = big[: cfg["max_territories"]]
    terr_of: dict[str, str] = {}
    territories = []
    for g in big:
        h = hub(g, adj, notes)
        hname = notes[h]["name"]
        tid = slug(hname)
        for p in g:
            terr_of[p] = tid
        territories.append({"id": tid, "hub": hname, "name": cfg["names"].get(hname, hname), "concepts": sorted(g)})
    frontier = [p for p in concepts if p not in terr_of]

    # Turns: months from the first dated note to today.
    created = {p: month(n["fm"].get("created")) for p, n in notes.items()}
    dated = [m for m in created.values() if m]
    last = f"{today.year:04d}-{today.month:02d}"
    first = min(dated + [last])
    turns = turns_between(first, last)
    tix = {m: i for i, m in enumerate(turns)}
    turn_of = lambda p: tix.get(created[p], 0) if created[p] <= last else len(turns) - 1  # noqa: E731

    def terrain(p):
        return cfg["maturity"].get(text_of(notes[p]["fm"], "status").lower(), "seed")

    def territories_touched(p):
        return {terr_of[q] for q in adj[p] if q in terr_of}

    # Ideas, problems, bets and the roads between them.
    def linked(p, kind):
        return sorted(q for q in adj[p] if notes[q]["kind"] == kind)

    bet_rows = {}
    for b in bets:
        fm = notes[b]["fm"]
        stage = "bet"
        if text_of(fm, "dropped"):
            stage = "dropped"
        if text_of(fm, "shipped") or text_of(fm, "delivery").lower() in BUILT:
            stage = "built"
        if text_of(fm, "kpi_result").lower() in FINISHED or text_of(fm, "outcome"):
            stage = "finished"
        start = month(fm.get("started")) or month(fm.get("cycle_start")) or created[b]
        bet_rows[b] = {"name": notes[b]["name"], "path": b, "stage": stage, "started": start,
                       "shipped": month(fm.get("shipped")), "ideas": linked(b, "idea"),
                       "territories": sorted(territories_touched(b))}
    idea_rows = {}
    for i in ideas:
        tb = [bet_rows[b]["stage"] for b in linked(i, "bet")]
        probs = linked(i, "problem")
        stage = "idea"
        if probs:
            stage = "tied"
        for s in ("bet", "dropped", "built", "finished"):
            if s in tb:
                stage = "bet" if s == "dropped" else s
        votes = collections.Counter(terr_of[q] for q in adj[i] if q in terr_of)
        home = sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if votes else ""
        idea_rows[i] = {"name": notes[i]["name"], "path": i, "stage": stage, "created": created[i],
                        "territory": home, "problems": probs, "bets": linked(i, "bet")}
    problem_rows = {}
    for p in problems:
        tt = set(territories_touched(p))
        for i in linked(p, "idea"):
            if idea_rows[i]["territory"]:
                tt.add(idea_rows[i]["territory"])
        problem_rows[p] = {"name": notes[p]["name"], "path": p, "ideas": linked(p, "idea"),
                           "fog": not linked(p, "idea"), "territories": sorted(tt)}

    # Territory detail.
    n_turns = len(turns)
    for t in territories:
        cs = t["concepts"]
        per_turn = collections.Counter(turn_of(p) for p in cs)
        run, cum = 0, []
        for k in range(n_turns):
            run += per_turn.get(k, 0)
            cum.append(run)
        rank = {"core": 0, "developing": 1, "seed": 2}
        ordered = sorted(cs, key=lambda p: (rank[terrain(p)], turn_of(p), notes[p]["name"]))
        t_ideas = sorted(i for i, r in idea_rows.items() if r["territory"] == t["id"])
        t_bets = sorted({b for b, r in bet_rows.items() if t["id"] in r["territories"]}
                        | {b for i in t_ideas for b in idea_rows[i]["bets"]})
        t_probs = sorted(p for p, r in problem_rows.items() if t["id"] in r["territories"])
        t.update({
            "size": len(cs), "growth": cum,
            "terrain": dict(collections.Counter(terrain(p) for p in cs)),
            "cities": [notes[p]["name"] for p in sorted(cs, key=lambda p: (-len(adj[p]), notes[p]["name"]))[:3]],
            "concepts": [{"name": notes[p]["name"], "path": p, "terrain": terrain(p), "turn": turn_of(p)} for p in ordered],
            "ideas": t_ideas, "bets": t_bets, "problems": t_probs,
            "stages": dict(collections.Counter(idea_rows[i]["stage"] for i in t_ideas)),
        })

    # Borders and unlocks.
    cross = collections.Counter()
    ground = collections.defaultdict(collections.Counter)
    for p in concepts:
        for q in adj[p]:
            if p < q and p in terr_of and q in terr_of and terr_of[p] != terr_of[q]:
                a, b = sorted((terr_of[p], terr_of[q]))
                cross[(a, b)] += 1
                ground[(a, b)][notes[p]["name"]] += 1
                ground[(a, b)][notes[q]["name"]] += 1
    bridged = set()
    for p, n in notes.items():
        if n["kind"] in bridges_kinds:
            tt = sorted(territories_touched(p))
            bridged |= {(a, b) for a in tt for b in tt if a < b}
    name_of = {t["id"]: t["name"] for t in territories}
    borders = [{"a": a, "b": b, "links": v, "bridged": (a, b) in bridged}
               for (a, b), v in sorted(cross.items(), key=lambda kv: (-kv[1], kv[0]))]
    unlocks = []
    for br in borders:
        if br["bridged"] or br["links"] < cfg["min_unlock_links"]:
            continue
        g = [k for k, _ in sorted(ground[(br["a"], br["b"])].items(), key=lambda kv: (-kv[1], kv[0]))[:4]]
        unlocks.append({**br, "ground": g,
                        "hint": f"What idea would join {name_of[br['a']]} and {name_of[br['b']]}? Start from {g[0]}."})
        if len(unlocks) >= cfg["max_unlocks"]:
            break

    # Turn reports.
    def per_turn(items, key):
        c = collections.Counter(tix[r[key]] for r in items if r[key] in tix)
        return [c.get(k, 0) for k in range(n_turns)]

    concept_new = [0] * n_turns
    for p in concepts:
        concept_new[turn_of(p)] += 1
    total = len(concepts) or 1
    spikes = [k for k, v in enumerate(concept_new) if v >= 50 and v >= 0.3 * total]

    ir, br_, pr = list(idea_rows.values()), list(bet_rows.values()), list(problem_rows.values())
    pipeline = {
        "ideas": len(ir),
        "tied": sum(1 for r in ir if r["problems"]),
        "reached_bet": sum(1 for r in ir if r["bets"]),
        "bets": len(br_),
        "bets_from_ideas": sum(1 for r in br_ if r["ideas"]),
        "built": sum(1 for r in br_ if r["stage"] in ("built", "finished")),
        "finished": sum(1 for r in br_ if r["stage"] == "finished"),
        "dropped": sum(1 for r in br_ if r["stage"] == "dropped"),
    }
    return {
        "version": 1,
        "generated": today.isoformat(),
        "vault_name": cfg["vault_name"] or os.path.basename(os.path.abspath(vault)),
        "turns": turns,
        "counts": {k: len(of(k)) for k in ("concept", "idea", "problem", "bet", "decision", "insight")},
        "undated": sum(1 for p in concepts if not created[p]),
        "territories": territories,
        "frontier": [{"name": notes[p]["name"], "path": p, "turn": turn_of(p)} for p in frontier],
        "borders": borders,
        "unlocks": unlocks,
        "ideas": ir,
        "bets": br_,
        "problems": pr,
        "fog": [r["name"] for r in pr if r["fog"]],
        "pipeline": pipeline,
        "per_turn": {"concepts": concept_new, "ideas": per_turn(ir, "created"),
                     "bets_started": per_turn(br_, "started"), "bets_shipped": per_turn(br_, "shipped")},
        "spikes": spikes,
    }


# ---------- outputs ----------

def label(m: str) -> str:
    return dt.date(int(m[:4]), int(m[5:7]), 1).strftime("%b %Y")


def summary(data: dict) -> str:
    k = len(data["turns"]) - 1
    pt = data["per_turn"]
    lines = [f"Vault map, turn {label(data['turns'][k])}"]
    on_map = sum(t["growth"][k] for t in data["territories"])
    grew = sorted(((t["growth"][k] - (t["growth"][k - 1] if k else 0), t["name"]) for t in data["territories"]), reverse=True)
    top = ", ".join(f"{n} (+{d})" for d, n in grew[:2] if d > 0) or "none"
    lines.append(f"- Territories: {len(data['territories'])}, {on_map} concepts, {pt['concepts'][k]} new this turn. Grew most: {top}.")
    lines.append(f"- Ideas formed: {pt['ideas'][k]}. Bets started: {pt['bets_started'][k]}. Bets shipped: {pt['bets_shipped'][k]}.")
    p = data["pipeline"]
    lines.append(f"- Road: {p['ideas']} ideas, {p['tied']} tied to a problem, {p['reached_bet']} reached a bet, "
                 f"{p['built']} built, {p['finished']} finished.")
    if data["unlocks"]:
        name = {t["id"]: t["name"] for t in data["territories"]}
        u = "; ".join(f"{name[x['a']]} and {name[x['b']]} ({x['links']} links)" for x in data["unlocks"][:3])
        lines.append(f"- Unexplored routes: {u}.")
    if data["fog"]:
        n = len(data["fog"])
        lines.append(f"- Fog: {n} problem{'' if n == 1 else 's'} with no idea yet.")
    if k in data["spikes"]:
        lines.append("- This turn's concept count is a spike, likely one import rather than steady growth.")
    return "\n".join(lines) + "\n"


def render_html(data: dict) -> str:
    with open(TEMPLATE, encoding="utf-8") as fh:
        page = fh.read()
    if DATA_MARK not in page:
        raise SystemExit("vault-map: map.html has no data marker")
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return page.replace(DATA_MARK, blob, 1)


def write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Build the vault map.")
    ap.add_argument("--vault")
    ap.add_argument("--config")
    ap.add_argument("--today")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--html", dest="html_out")
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args(argv)
    vault = resolve_vault(a.vault)
    try:
        today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    except ValueError:
        raise SystemExit(f"vault-map: --today must be YYYY-MM-DD, got {a.today!r}")
    data = build(vault, load_config(vault, a.config), today)
    if a.json_out:
        write(a.json_out, json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    if a.html_out:
        write(a.html_out, render_html(data))
    if a.summary:
        sys.stdout.write(summary(data))
    if not (a.json_out or a.html_out or a.summary):
        sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
