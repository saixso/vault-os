"""Hermetic tests for scripts/idea-links.py. Fake vault, fake data only.

Usage:
  python3 tests/test_idea_links.py
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "idea-links.py")
spec = importlib.util.spec_from_file_location("idea_links", SCRIPT)
il = importlib.util.module_from_spec(spec)
spec.loader.exec_module(il)

NOTES = {
    "ideas/Idea - Shared Device Health Score.md": (
        "---\ntags:\n  - idea\nstatus: seed\nsolves:\n  - \"[[Problem - Devices Fail Silently]]\"\n---\n"
        "# Idea - Shared Device Health Score\n\nOne score per site from device check-ins.\n"
    ),
    "areas/Problem - Devices Fail Silently.md": "---\ntags: [problem]\n---\nDevices go offline and nobody hears.\n",
    "areas/Field Install Playbook.md": (
        "---\naliases: [Install Playbook]\ntags: [process]\n---\nSteps for an on-site install. See [[Problem - Devices Fail Silently]].\n"
    ),
    "areas/Router Firmware Rollout.md": "Staged firmware rollout for site routers, with a pilot ring.\n",
    "wiki/concepts/Feedback Loop.md": "---\ntype: concept\n---\nA loop where output feeds back as input. [[Field Install Playbook]]\n",
    "reviews/daily/2026-11-20.md": "- Talked about the Ops Console and the site map.\n",
    "reviews/daily/2026-11-21.md": "- Ops Console came up again.\n",
    "README.md": "Readme for the fake vault.\n",
}

IDEAS = {
    "date": "2026-11-25",
    "ideas": [
        {"title": "Alert sites before devices fail", "summary": "Send a site an alert when device health drops, using the install playbook data.",
         "meeting": "Ops sync", "terms": ["Install Playbook", "Ops Console", "Pager Thing"], "commitment": True},
        {"title": "Shared device health score", "summary": "Score every site from check-ins.",
         "meeting": "Ops sync", "terms": ["Router Firmware Rollouts", "Feedback Loops"]},
        {"title": "Weekly firmware pilot ring", "summary": "Try new router firmware on a small pilot ring first.",
         "meeting": "Infra call", "terms": []},
    ],
}


def tree_hash(root):
    h = hashlib.sha256()
    for d, _, files in sorted(os.walk(root)):
        for f in sorted(files):
            p = os.path.join(d, f)
            h.update(os.path.relpath(p, root).encode())
            with open(p, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()


class IdeaLinks(unittest.TestCase):
    def setUp(self):
        self.v = tempfile.mkdtemp()
        for rel, body in NOTES.items():
            p = os.path.join(self.v, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                f.write(body)

    def tearDown(self):
        shutil.rmtree(self.v)

    def run_cli(self, data, *args):
        r = subprocess.run([sys.executable, SCRIPT, "--vault", self.v, *args], input=json.dumps(data),
                           capture_output=True, text=True, check=True)
        return json.loads(r.stdout)

    def by_title(self, out):
        return {i["title"]: i for i in out["ideas"]}

    def test_never_writes_to_the_vault(self):
        before = tree_hash(self.v)
        self.run_cli(IDEAS)
        self.assertEqual(before, tree_hash(self.v))

    def test_named_alias_links_sure_and_problems_go_to_solves(self):
        out = self.by_title(self.run_cli(IDEAS))
        a = out["Alert sites before devices fail"]
        sure = {l["note"] for l in a["links"]["sure"]}
        self.assertIn("Field Install Playbook", sure)  # matched by its alias
        self.assertEqual(a["action"], "create")  # comes with a commitment
        self.assertEqual(a["same_meeting"], ["Shared device health score"])
        self.assertNotIn("README", sure | {l["note"] for l in a["links"]["maybe"]})

    def test_existing_idea_is_updated_not_created(self):
        b = self.by_title(self.run_cli(IDEAS))["Shared device health score"]
        self.assertEqual(b["action"], "update")
        self.assertEqual(b["existing"]["note"], "Idea - Shared Device Health Score")
        linked = {l["note"] for k in ("sure", "maybe", "solves") for l in b["links"][k]}
        self.assertNotIn("Idea - Shared Device Health Score", linked)  # never links to itself

    def test_alias_suggestions_respect_protected_folders_and_cap(self):
        b = self.by_title(self.run_cli(IDEAS))["Shared device health score"]
        sug = {s["term"]: s for s in b["alias_suggestions"]}
        self.assertEqual(sug["Router Firmware Rollouts"]["note"], "Router Firmware Rollout")
        self.assertFalse(sug["Router Firmware Rollouts"]["protected"])
        self.assertTrue(sug["Feedback Loops"]["protected"])  # wiki/ is protected by default
        capped = self.by_title(self.run_cli(IDEAS, "--alias-cap", "0"))["Shared device health score"]
        self.assertTrue({s["term"]: s for s in capped["alias_suggestions"]}["Router Firmware Rollouts"]["over_cap"])

    def test_new_terms_need_a_second_mention_for_a_page(self):
        a = self.by_title(self.run_cli(IDEAS))["Alert sites before devices fail"]
        terms = {t["term"]: t for t in a["new_terms"]}
        self.assertEqual(terms["Ops Console"]["mentions_before"], 2)
        self.assertTrue(terms["Ops Console"]["create_page"])
        self.assertFalse(terms["Pager Thing"]["create_page"])

    def test_search_finds_unnamed_links_and_plain_ideas_stay_daily_lines(self):
        c = self.by_title(self.run_cli(IDEAS))["Weekly firmware pilot ring"]
        found = {l["note"] for k in ("sure", "maybe") for l in c["links"][k]}
        self.assertIn("Router Firmware Rollout", found)
        self.assertEqual(c["action"], "daily-line-only")
        for l in c["links"]["sure"] + c["links"]["maybe"]:
            self.assertLessEqual(len(l["reason"].split()), 6)

    def test_ideas_dir_flag_and_excluded_folders(self):
        out = self.run_cli(IDEAS, "--ideas-dir", "areas")
        self.assertEqual(out["ideas_dir"], "areas")
        paths = {l["path"] for i in out["ideas"] for k in ("sure", "maybe", "solves") for l in i["links"][k]}
        self.assertFalse(any(p.startswith("reviews/") for p in paths))

    def test_usable_names_skip_generic_and_short_words(self):
        self.assertFalse(il.usable_name("README"))
        self.assertFalse(il.usable_name("Home"))
        self.assertTrue(il.usable_name("KDS"))
        self.assertFalse(il.usable_name("kds"))
        self.assertTrue(il.usable_name("Router Firmware Rollout"))


if __name__ == "__main__":
    unittest.main()
