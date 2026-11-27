#!/usr/bin/env python3
"""Read-only link finder for the planner's idea pass.

Given ideas pulled from a day's meetings, find which existing vault notes each
one should link to. The agent decides what to write; this script only reads the
vault and prints JSON. It never writes a file.

How links are found, in order:
  1. Named: a note title or alias appears in the idea's text or terms.
     Prefixes like "Idea - " and "Problem - " are ignored when matching.
  2. Search: BM25 over note titles, aliases, tags and the first words of the
     body. Sure when the titles overlap strongly or every word of the note's
     title is in the idea; the rest are "maybe" (best few only, --maybe).
Short one-word titles match only as capital acronyms ("KDS"), and generic file
names (README, AGENTS, _index, dashboards) are never link targets.
  3. Same meeting: ideas raised in the same meeting link to each other.
Problem notes (title "Problem - ...", or tag/type problem) go to `solves`.

It also reports:
  - existing: an idea note that already covers this idea (update it, do not
    create a new one).
  - similar_ideas: other idea notes search found with some title overlap. The
    agent checks whether one is this idea in other words before creating.
  - alias_suggestions: a term that names an existing note differently (add it
    as an alias). Notes under a protected folder are flagged, and suggestions
    past the per-run cap are flagged.
  - new_terms: a term no note covers, with how often the vault mentioned it
    before. create_page is true from the second mention on, and only for a
    name (several words, or a word with a capital), never a common word.

Input (stdin, JSON):
  {"date": "2026-11-25",
   "ideas": [{"title": "...", "summary": "...", "meeting": "Team sync",
              "terms": ["Proper Noun", "..."], "commitment": true, "recurs": false}]}

  action per idea: "update" when an idea note already covers it, "create" when
  it comes with a commitment or recurs, else "daily-line-only".

Usage:
  idea-links.py --vault VAULT [--ideas-dir DIR] [--protect wiki] [--exclude a,b]
                [--top 8] [--maybe 5] [--alias-cap 5] < ideas.json

Standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

DEFAULT_EXCLUDE = ["reviews", "templates", "_templates", "raw", ".raw", "assets", "node_modules", "dashboards"]
DEFAULT_IDEAS_DIR = "ideas"
PREFIX_RE = re.compile(r"^(idea|problem|bet|moc|pitch|concept)\s*[-_:]\s*", re.I)
GENERIC = set("readme index home inbox projects areas resources archives untitled kanban log hot notes todo ideas idea problem problems "
              "dashboard dashboards agents claude changelog contributing license template templates".split())
STOP = set(
    "a an and are as at be but by for from has have how i if in into is it its of on or our so that the their them then there these "
    "they this to up was we what when where which who why will with you your not no can all any more most one two new use using via "
    "per vs get got make need needs should would could do does done just like also only than very over out about after before "
    "each every some other first take see give right part based during end build start put tell try ship move often runs".split()
)
FIELD_RE = re.compile(r"^(\w[\w-]*):\s*(.*)$")
LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
MAX_NGRAM = 8


def norm(s: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", s.lower()))


def stem(t: str) -> str:
    """Fold simple plurals so "operations" meets "operation"."""
    if len(t) > 4 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 4 and t.endswith("s") and not t.endswith("ss"):
        return t[:-1]
    return t


def tokens(s: str) -> list[str]:
    return [stem(t) for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in STOP and len(t) > 1 and not t.isdigit()]


def strip_prefix(name: str) -> str:
    return PREFIX_RE.sub("", name).strip()


# ---------- reading the vault ----------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    head, body = text[4:end], text[end + 4:]
    fm: dict = {}
    key = None
    for line in head.split("\n"):
        m = FIELD_RE.match(line)
        if m:
            key, val = m.group(1).lower(), m.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                fm[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
            elif val:
                fm[key] = val.strip("'\"")
            else:
                fm[key] = []
        elif key and line.strip().startswith("- "):
            if not isinstance(fm.get(key), list):
                fm[key] = [fm[key]] if fm.get(key) else []
            fm[key].append(line.strip()[2:].strip().strip("'\""))
    return fm, body


def as_list(v) -> list[str]:
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    return [v] if isinstance(v, str) and v.strip() else []


class Note:
    def __init__(self, path, name, aliases, tags, kind, words, links):
        self.path, self.name, self.aliases, self.tags, self.kind = path, name, aliases, tags, kind
        self.words = words  # first 300 words of the body, for search
        self.links = links
        self.inbound = 0

    @property
    def is_problem(self) -> bool:
        if re.match(r"(?i)idea\b", self.name) or is_noise(self.name):
            return False
        return bool(re.match(r"(?i)problem\s*[-:]", self.name)) or "problem" in self.tags or self.kind == "problem"


def under(path: str, folders: list[str]) -> bool:
    p = path.replace(os.sep, "/")
    return any(f and (p == f or p.startswith(f.rstrip("/") + "/")) for f in folders)


def load_vault(vault: str, exclude: list[str]) -> list[Note]:
    notes = []
    for root, dirs, files in os.walk(vault):
        rel_root = os.path.relpath(root, vault)
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not under(os.path.normpath(os.path.join(rel_root, d)), exclude))
        for f in sorted(files):
            if not f.endswith(".md"):
                continue
            rel = os.path.normpath(os.path.join(rel_root, f)).replace(os.sep, "/")
            try:
                with open(os.path.join(root, f), encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            fm, body = parse_frontmatter(text)
            name = f[:-3]
            tags = [t.lstrip("#").lower() for t in as_list(fm.get("tags"))]
            kind = str(fm.get("type", "")).lower() if isinstance(fm.get("type"), str) else ""
            links = LINK_RE.findall(body) + LINK_RE.findall(json.dumps(fm))
            notes.append(Note(rel, name, as_list(fm.get("aliases")), tags, kind, body.split()[:300], links))
    return notes


def count_inbound(notes: list[Note]) -> None:
    by_name = defaultdict(list)
    for n in notes:
        by_name[n.name.lower()].append(n)
    for n in notes:
        for target in set(n.links):
            t = target.strip().split("/")[-1].lower()
            for hit in by_name.get(t, []):
                if hit is not n:
                    hit.inbound += 1


def usable_name(s: str) -> bool:
    k = norm(s)
    if not k or s.strip().startswith("_") or k in GENERIC or k.startswith("untitled") or re.fullmatch(r"[\d ]+", k):
        return False
    parts = k.split()
    if len(parts) == 1 and (len(k) < 5 or k in STOP):
        # Short single words only when written as an acronym (e.g. "KDS").
        return s.strip().isupper() and len(s.strip()) >= 3
    return True


def is_noise(name: str) -> bool:
    """File names that are never link targets: README, AGENTS, _index, dashboard."""
    return name.strip().startswith("_") or norm(name) in GENERIC


def is_acronym(s: str) -> bool:
    k = norm(s)
    return len(k.split()) == 1 and (len(k) < 5 or k in STOP)


def name_index(notes: list[Note]) -> dict[str, list[Note]]:
    """Usable titles and aliases. Short one-word keys are acronyms and match only in capitals."""
    idx: dict[str, list[Note]] = defaultdict(list)
    for n in notes:
        names = {n.name, strip_prefix(n.name), *n.aliases}
        for s in list(names):  # "Model Context Protocol (MCP)" also answers to "MCP" and the words outside
            m = re.fullmatch(r"(.+?)\s*\(([^()]+)\)\s*", s)
            if m:
                names.add(m.group(1))
                if m.group(2).strip().isupper():  # (MCP) yes, (Network) or (End-to-End) no
                    names.add(m.group(2))
        for s in names:
            if usable_name(s):
                k = norm(s)
                if n not in idx[k]:
                    idx[k].append(n)
    return idx


# ---------- matching ----------

def named_matches(text: str, idx: dict[str, list[Note]]) -> dict[str, tuple[Note, str]]:
    """Notes whose title or alias appears in text. Key = note path."""
    toks = norm(text).split()
    found: dict[str, tuple[Note, str]] = {}
    for i in range(len(toks)):
        for j in range(min(len(toks), i + MAX_NGRAM), i, -1):
            k = " ".join(toks[i:j])
            if k in idx and is_acronym(k) and not re.search(r"(?<!\w)" + re.escape(k.upper()) + r"(?!\w)", text):
                continue  # "KDS" matches, "kds" does not
            for n in idx.get(k, []):
                found.setdefault(n.path, (n, k))
    return found


class BM25:
    def __init__(self, notes: list[Note], k1: float = 1.5, b: float = 0.75):
        self.notes, self.k1, self.b = notes, k1, b
        self.tf, self.dl = [], []
        df: Counter = Counter()
        for n in notes:
            title = tokens(strip_prefix(n.name)) + [t for a in n.aliases for t in tokens(a)]
            doc = title * 3 + [t for tag in n.tags for t in tokens(tag)] + tokens(" ".join(n.words))
            c = Counter(doc)
            self.tf.append(c)
            self.dl.append(len(doc))
            df.update(c.keys())
        self.N = max(len(notes), 1)
        self.avg = (sum(self.dl) / self.N) if self.dl else 1.0
        self.idf = {t: math.log(1 + (self.N - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def search(self, query: str, top: int) -> list[tuple[float, Note, list[str]]]:
        q = list(dict.fromkeys(tokens(query)))
        out = []
        for i, c in enumerate(self.tf):
            s, hit = 0.0, []
            for t in q:
                f = c.get(t)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.dl[i] / self.avg))
                    hit.append(t)
            hit.sort(key=lambda t: -self.idf[t])  # rarest shared words first
            if s > 0:
                out.append((s, self.notes[i], hit))
        out.sort(key=lambda x: (-x[0], -x[1].inbound, x[1].path))
        return out[:top]


def title_overlap(a: str, b: str) -> float:
    ta, tb = set(tokens(strip_prefix(a))), set(tokens(strip_prefix(b)))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def fuzzy_note(term: str, notes: list[Note]) -> Note | None:
    """An existing note the term names in other words (for an alias)."""
    tt = set(tokens(term))
    best, best_s = None, 0.0
    for n in notes:
        for s in [strip_prefix(n.name), *n.aliases]:
            ts = set(tokens(s))
            if not ts:
                continue
            shared = {t for t in tt & ts if len(t) >= 4}
            j = len(tt & ts) / len(tt | ts) if tt | ts else 0
            r = SequenceMatcher(None, norm(term), norm(s)).ratio()
            score = max(j if shared else 0.0, r if r >= 0.85 else 0.0)
            if score > best_s or (score == best_s and best and n.inbound > best.inbound):
                best, best_s = n, score
    return best if best_s >= 0.6 else None


def all_texts(vault: str) -> list[str]:
    """Every note's text, daily notes included, read once per run."""
    out = []
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.endswith(".md"):
                try:
                    with open(os.path.join(root, f), encoding="utf-8", errors="replace") as fh:
                        out.append(fh.read())
                except OSError:
                    pass
    return out


def mentions(term: str, texts: list[str]) -> int:
    """How many notes mention the term (any punctuation between its words)."""
    words = norm(term).split()
    if words and len(words[-1]) > 4 and words[-1].endswith("s"):
        words[-1] = words[-1][:-1].rstrip("e").rstrip("i")  # families -> famil, routers -> router
    pat = re.compile(r"(?<![\w])" + r"[\W_]+".join(map(re.escape, words)) + r"\w{0,3}(?![\w])", re.I)
    return sum(1 for t in texts if pat.search(t))


def short_reason(basis: str, hit: list[str] | None = None, term: str = "") -> str:
    if basis == "named":
        return "named in the meeting"
    if basis == "same-meeting":
        return "raised in the same meeting"
    if basis == "solves":
        return "problem this idea addresses"
    words = (hit or [])[:3]
    return ("shares " + ", ".join(words)) if words else "related by search"


def name_like(term: str) -> bool:
    """A page only for names: several words, or a word with a capital (Supportal, KDS), not "alerts"."""
    t = term.strip()
    return len(t.split()) > 1 or any(c.isupper() for c in t)


def run(vault: str, data: dict, ideas_dir: str, protect: list[str], exclude: list[str], top: int, alias_cap: int,
        max_maybe: int = 5) -> dict:
    notes = load_vault(vault, exclude)
    count_inbound(notes)
    idx = name_index(notes)
    bm = BM25(notes)
    idea_notes = [n for n in notes if under(n.path, [ideas_dir]) or "idea" in n.tags or n.kind == "idea"]
    idea_set = set(idea_notes)
    ideas = data.get("ideas", [])
    batch_terms: Counter = Counter()
    for it in ideas:
        for t in {norm(x) for x in it.get("terms", [])}:
            batch_terms[t] += 1

    by_meeting = defaultdict(list)
    for it in ideas:
        by_meeting[it.get("meeting", "")].append(it.get("title", ""))

    out_ideas, alias_used, texts = [], 0, None
    for it in ideas:
        title, summary = it.get("title", ""), it.get("summary", "")
        terms = it.get("terms", [])
        text = " . ".join([title, summary, *terms])
        idea_toks = set(tokens(text))

        existing = None
        for n in idea_notes:
            s = title_overlap(title, n.name)
            if s >= 0.5 and (existing is None or s > existing["overlap"]):
                existing = {"note": n.name, "path": n.path, "overlap": round(s, 2)}

        sure, maybe, solves = {}, {}, {}
        similar = {}  # other idea notes that may be this idea in other words

        def put(bucket, n, basis, hit=None):
            if (existing and n.path == existing["path"]) or is_noise(n.name):
                return
            for b in (sure, maybe, solves, similar):
                if n.path in b or any(v["note"] == n.name for v in b.values()):
                    return
            target = solves if n.is_problem else bucket
            target[n.path] = {"note": n.name, "path": n.path, "reason": short_reason("solves" if n.is_problem else basis, hit),
                              "basis": basis, "inbound": n.inbound}

        for path, (n, _k) in named_matches(text, idx).items():
            put(sure, n, "named")
        for score, n, hit in bm.search(title + " " + summary, top):
            if n in idea_set and not (existing and n.path == existing["path"]) and title_overlap(title, n.name) >= 0.2:
                similar[n.path] = {"note": n.name, "path": n.path, "overlap": round(title_overlap(title, n.name), 2)}
                continue
            name_toks = set(tokens(strip_prefix(n.name)))
            strong = (title_overlap(title, n.name) >= 0.5 or len(set(hit) & name_toks) >= 3
                      or (len(name_toks) >= 2 and name_toks <= idea_toks))
            put(sure if strong else maybe, n, "search", hit)

        same = [t for t in by_meeting.get(it.get("meeting", ""), []) if t and t != title]

        named_keys = {norm(k) for _, k in named_matches(" . ".join(terms), idx).values()}
        aliases, new_terms = [], []
        for term in terms:
            k = norm(term)
            if not k or k in idx or k in named_keys:
                continue
            n = fuzzy_note(term, notes)
            if n and k in {norm(x) for x in [n.name, strip_prefix(n.name), *n.aliases]}:
                put(sure, n, "named")  # same name in other capitals: a link, not a new alias
            elif n:
                over = alias_used >= alias_cap
                prot = under(n.path, protect)
                if not over and not prot:
                    alias_used += 1
                aliases.append({"term": term, "note": n.name, "path": n.path, "current_aliases": n.aliases,
                                "protected": prot, "over_cap": over and not prot})
                put(sure, n, "named")
            else:
                if texts is None:
                    texts = all_texts(vault)
                before = mentions(term, texts)
                new_terms.append({"term": term, "mentions_before": before, "mentions_today": batch_terms[k],
                                  "create_page": name_like(term) and before + batch_terms[k] >= 2})

        if existing:
            action = "update"
        elif it.get("commitment") or it.get("recurs"):
            action = "create"
        else:
            action = "daily-line-only"

        maybe_list = list(maybe.values())  # best search rank first
        out_ideas.append({
            "title": title,
            "meeting": it.get("meeting", ""),
            "action": action,
            "existing": existing,
            "similar_ideas": list(similar.values()),
            "links": {"sure": list(sure.values()), "maybe": maybe_list[:max_maybe], "solves": list(solves.values())},
            "same_meeting": same,
            "alias_suggestions": aliases,
            "new_terms": new_terms,
        })

    return {
        "date": data.get("date"),
        "notes_indexed": len(notes),
        "ideas_dir": ideas_dir,
        "alias_cap": alias_cap,
        "alias_suggested": alias_used,
        "ideas": out_ideas,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", help="vault root (default: $VAULT_OS_VAULT_ROOT, then the current directory)")
    ap.add_argument("--ideas-dir", default=os.environ.get("VAULT_OS_IDEAS_DIR", DEFAULT_IDEAS_DIR),
                    help="folder that holds idea notes (default: $VAULT_OS_IDEAS_DIR, then ideas)")
    ap.add_argument("--protect", default="wiki", help="comma list of folders whose notes never get alias edits (default: wiki)")
    ap.add_argument("--exclude", default=",".join(DEFAULT_EXCLUDE), help="comma list of folders left out of link targets")
    ap.add_argument("--top", type=int, default=8, help="search results per idea (default 8)")
    ap.add_argument("--maybe", type=int, default=5, help="maybe links kept per idea, best first (default 5)")
    ap.add_argument("--alias-cap", type=int, default=5, help="alias edits allowed per run (default 5)")
    a = ap.parse_args(argv)
    vault = os.path.abspath(a.vault or os.environ.get("VAULT_OS_VAULT_ROOT") or os.getcwd())
    if not os.path.isdir(vault):
        print(f"idea-links: {vault} is not a folder", file=sys.stderr)
        return 2
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"idea-links: input is not JSON ({e})", file=sys.stderr)
        return 2
    split = lambda s: [x.strip().strip("/") for x in s.split(",") if x.strip()]
    res = run(vault, data, a.ideas_dir.strip("/"), split(a.protect), split(a.exclude), a.top, a.alias_cap, a.maybe)
    json.dump(res, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
