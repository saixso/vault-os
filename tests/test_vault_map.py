"""Hermetic tests for scripts/vault-map/build.py. A made-up vault only.

Usage:
  python3 tests/test_vault_map.py
"""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "vault-map", "build.py")
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts", "vault-map"))
import build  # noqa: E402

TODAY = dt.date(2026, 3, 15)


def note(fm: dict | None, body: str = "") -> str:
    if fm is None:
        return body
    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            lines += [f'  - "{x}"' for x in v]
        else:
            lines.append(f"{k}: {v}")
    return "\n".join(lines + ["---", body])


class Vault:
    """Two groups of nine linked concepts (Garden, Kitchen), a loner, ideas, a problem, a bet."""

    def __init__(self, with_insight=False):
        self.root = tempfile.mkdtemp(prefix="vault-map-")
        os.makedirs(os.path.join(self.root, ".obsidian"))
        g = [f"Garden {i}" for i in range(9)]
        k = [f"Kitchen {i}" for i in range(9)]
        for group, month, status in ((g, "2026-01", "evergreen"), (k, "2026-02", "seed")):
            for i, name in enumerate(group):
                links = " ".join(f"[[{o}]]" for o in group if o != name)
                if i < 3:  # three links across the border
                    other = k if group is g else g
                    links += f" [[{other[i]}]]"
                self.put(f"wiki/concepts/{name}.md", note(
                    {"type": "concept", "status": status, "created": f"{month}-0{i % 9 + 1}"}, links))
        self.put("wiki/concepts/Lonely Thought.md", note({"type": "concept", "status": "seed", "created": "2026-03-01"}, "no links"))
        self.put("Areas/Home Problems/Problem - Weeds.md", note({"created": "2026-01-05", "severity": "high"}))
        self.put("Areas/Home Problems/Problem - Leaky Tap.md", note({"created": "2026-02-05"}))
        self.put("Areas/Home Problems/How to link.md", note(None, "guide with no frontmatter"))
        self.put("Areas/Home Problems/Tracker.md", note({"tags": ["type/moc"]}, "[[Problem - Weeds]]"))
        self.put("wiki/ideas/Mulch Robot.md", note(
            {"type": "idea", "created": "2026-03-02", "solves": ["[[Problem - Weeds]]"]}, "[[Garden 0]] [[Garden 1]]"))
        self.put("wiki/ideas/Spice Rack.md", note({"type": "idea", "created": "2026-03-03"}, "[[Kitchen 4]]"))
        self.put("bets/Build the Robot.md", note(
            {"type": "bet", "started": "2026-03-04", "shipped": "2026-03-10", "kpi_result": "hit",
             "from_ideas": ["[[Mulch Robot]]"]}))
        self.put("bets/Try Herbs.md", note({"type": "bet", "cycle_start": "2026-02-01", "dropped": "2026-02-20"}))
        self.put("bets/Bet Radar.md", note({"type": "bet-radar"}, "[[Build the Robot]]"))
        self.put("bets/README.md", note({"type": "bet"}))
        self.put("inbox/Scrap.md", note({"type": "idea"}, "[[Garden 2]]"))
        if with_insight:
            self.put("insights/Soil and Salt.md", note({"created": "2026-03-05"}, "[[Garden 5]] [[Kitchen 5]]"))

    def put(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def build(self, **cfg):
        c = build.load_config(self.root, None)
        c.update(cfg)
        return build.build(self.root, c, TODAY)

    def close(self):
        shutil.rmtree(self.root)


class Base(unittest.TestCase):
    with_insight = False

    def setUp(self):
        self.v = Vault(self.with_insight)
        self.d = self.v.build()

    def tearDown(self):
        self.v.close()

    def terr(self, prefix):
        return next(t for t in self.d["territories"] if t["hub"].startswith(prefix))


class Notes(Base):
    def test_kinds_and_skips(self):
        self.assertEqual(self.d["counts"]["concept"], 19)
        self.assertEqual(self.d["counts"]["idea"], 2)       # inbox idea skipped
        self.assertEqual(self.d["counts"]["problem"], 2)    # guide and tracker skipped
        self.assertEqual(self.d["counts"]["bet"], 2)        # radar and README skipped

    def test_frontmatter_lists(self):
        fm, _ = build.parse_frontmatter('---\ntags: [a, b]\nsolves:\n  - "[[X|alias]]"\nname: "Q"\n---\nbody')
        self.assertEqual(fm["tags"], ["a", "b"])
        self.assertEqual(build.link_target(fm["solves"][0]), "x")
        self.assertEqual(fm["name"], "Q")


class Territories(Base):
    def test_two_territories_and_frontier(self):
        self.assertEqual(sorted(t["size"] for t in self.d["territories"]), [9, 9])
        self.assertEqual([f["name"] for f in self.d["frontier"]], ["Lonely Thought"])

    def test_terrain_and_growth(self):
        g, k = self.terr("Garden"), self.terr("Kitchen")
        self.assertEqual(g["terrain"], {"core": 9})
        self.assertEqual(k["terrain"], {"seed": 9})
        self.assertEqual(self.d["turns"], ["2026-01", "2026-02", "2026-03"])
        self.assertEqual(g["growth"], [9, 9, 9])
        self.assertEqual(k["growth"], [0, 9, 9])
        self.assertEqual(self.d["per_turn"]["concepts"], [9, 9, 1])

    def test_rename_and_merge(self):
        g = self.terr("Garden")["hub"]
        k = self.terr("Kitchen")["hub"]
        d = self.v.build(names={g: "The Garden"})
        self.assertIn("The Garden", [t["name"] for t in d["territories"]])
        d = self.v.build(merge={k: g})
        self.assertEqual([t["size"] for t in d["territories"]], [18])

    def test_same_notes_same_map(self):
        self.assertEqual(json.dumps(self.d, sort_keys=True), json.dumps(self.v.build(), sort_keys=True))


class Roads(Base):
    def test_idea_stages(self):
        ideas = {i["name"]: i for i in self.d["ideas"]}
        self.assertEqual(ideas["Mulch Robot"]["stage"], "finished")
        self.assertEqual(ideas["Spice Rack"]["stage"], "idea")
        self.assertEqual(ideas["Mulch Robot"]["territory"], self.terr("Garden")["id"])

    def test_bet_stages_and_pipeline(self):
        bets = {b["name"]: b for b in self.d["bets"]}
        self.assertEqual(bets["Build the Robot"]["stage"], "finished")
        self.assertEqual(bets["Try Herbs"]["stage"], "dropped")
        self.assertEqual(bets["Try Herbs"]["started"], "2026-02")
        p = self.d["pipeline"]
        self.assertEqual((p["ideas"], p["tied"], p["reached_bet"], p["bets"], p["built"], p["finished"], p["dropped"]),
                         (2, 1, 1, 2, 1, 1, 1))
        self.assertEqual(self.d["per_turn"]["bets_shipped"], [0, 0, 1])

    def test_fog(self):
        self.assertEqual(self.d["fog"], ["Problem - Leaky Tap"])


class Unlocks(Base):
    def test_unbridged_border_is_an_unlock(self):
        self.assertEqual(len(self.d["unlocks"]), 1)
        u = self.d["unlocks"][0]
        self.assertEqual(u["links"], 3)
        self.assertFalse(u["bridged"])
        self.assertTrue(u["ground"])

    def test_threshold(self):
        self.assertEqual(self.v.build(min_unlock_links=4)["unlocks"], [])


class Bridged(Base):
    with_insight = True

    def test_insight_joining_both_closes_the_unlock(self):
        self.assertEqual(self.d["unlocks"], [])
        self.assertTrue(self.d["borders"][0]["bridged"])


class Outputs(Base):
    def test_summary(self):
        s = build.summary(self.d)
        self.assertTrue(s.startswith("Vault map, turn Mar 2026"))
        self.assertIn("Bets shipped: 1", s)
        self.assertIn("Fog: 1 problem with no idea", s)
        self.assertIn("Unexplored routes: ", s)

    def test_html_embeds_data_safely(self):
        self.d["frontier"][0]["name"] = "</script><b>x"
        page = build.render_html(self.d)
        self.assertNotIn(build.DATA_MARK, page)
        self.assertNotIn("</script><b>", page)
        self.assertIn('"vault_name"', page)

    def test_template_has_marker(self):
        with open(build.TEMPLATE, encoding="utf-8") as fh:
            self.assertIn(build.DATA_MARK, fh.read())

    def test_cli_writes_only_what_is_asked(self):
        out = os.path.join(self.v.root, "dashboards", "vault-map.json")
        before = sorted(os.listdir(self.v.root))
        r = subprocess.run([sys.executable, SCRIPT, "--vault", self.v.root, "--today", "2026-03-15", "--summary"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(os.listdir(self.v.root)), before)
        r = subprocess.run([sys.executable, SCRIPT, "--vault", self.v.root, "--today", "2026-03-15", "--json", out],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["generated"], "2026-03-15")

    def test_config_file_and_unknown_key(self):
        os.makedirs(os.path.join(self.v.root, "dashboards"))
        path = os.path.join(self.v.root, "dashboards", "vault-map-config.json")
        with open(path, "w") as fh:
            json.dump({"min_territory": 20}, fh)
        c = build.load_config(self.v.root, None)
        self.assertEqual(build.build(self.v.root, c, TODAY)["territories"], [])
        with open(path, "w") as fh:
            json.dump({"nope": 1}, fh)
        with self.assertRaises(SystemExit):
            build.load_config(self.v.root, None)

    def test_refuses_a_folder_that_is_not_a_vault(self):
        d = tempfile.mkdtemp()
        try:
            r = subprocess.run([sys.executable, SCRIPT, "--vault", d], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main(verbosity=1)
