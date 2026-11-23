"""Hermetic tests for scripts/planner.py. Fake data only.

Notes are rendered from the starter templates in skills/planner/templates.
Set PLANNER_TEMPLATES_DIR to a vault's templates/ folder to run the same tests
against that vault's own templates.

Usage:
  python3 tests/test_planner.py
"""
import datetime as dt
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "planner.py")
TEMPLATES_DIR = os.environ.get("PLANNER_TEMPLATES_DIR") or os.path.join(REPO_ROOT, "skills", "planner", "templates")
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import planner  # noqa: E402

D = dt.date


class Dates(unittest.TestCase):
    def test_week_numbers_match_moment_en(self):
        # moment("2026-11-22").format("ww") == "48" (Sunday start, week 1 holds Jan 1)
        self.assertEqual(planner.week_number(D(2026, 11, 22)), 48)
        self.assertEqual(planner.week_number(D(2026, 11, 23)), 48)
        self.assertEqual(planner.week_number(D(2026, 11, 28)), 48)
        self.assertEqual(planner.week_number(D(2026, 11, 29)), 49)
        self.assertEqual(planner.week_number(D(2026, 1, 1)), 1)
        self.assertEqual(planner.week_number(D(2027, 1, 2)), 1)

    def test_paths(self):
        p = planner.note_paths(D(2026, 11, 25))
        self.assertEqual(p["daily"], "reviews/daily/2026-11-25.md")
        self.assertEqual(p["weekly"], "reviews/weekly/Weekly Review 2026-W48.md")
        self.assertEqual(p["monthly"], "reviews/monthly/Monthly Review 2026-11.md")


class VaultCase(unittest.TestCase):
    def setUp(self):
        self.v = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.v, "templates"))
        for kind in ("daily", "weekly", "monthly"):
            shutil.copy(os.path.join(TEMPLATES_DIR, f"{kind}.md"), os.path.join(self.v, "templates"))

    def tearDown(self):
        shutil.rmtree(self.v)

    def path(self, rel):
        return os.path.join(self.v, rel)

    def read(self, rel):
        with open(self.path(rel)) as f:
            return f.read()


class Render(VaultCase):
    def test_daily_from_real_template(self):
        rel = os.path.relpath(planner.cmd_render(self.v, "daily", D(2026, 11, 24)), self.v)
        self.assertEqual(rel, "reviews/daily/2026-11-24.md")
        text = self.read(rel)
        self.assertIn("# Tuesday, November 24, 2026", text)
        self.assertIn("![[Weekly Review 2026-W48#2026-W48 Goals]]", text)
        self.assertIn("created: 2026-11-24", text)
        self.assertNotIn("<%", text)
        self.assertNotIn("tp.file.move", text)
        for block in ("prep", "promises", "decisions", "scorecard"):
            self.assertIn(f"<!-- planner:{block} -->", text)

    def test_weekly_and_monthly_from_real_templates(self):
        w = self.read(os.path.relpath(planner.cmd_render(self.v, "weekly", D(2026, 11, 24)), self.v))
        self.assertIn("# Weekly Review 2026-W48", w)
        self.assertIn("week_start: 2026-11-22", w)
        self.assertIn("week_end: 2026-11-28", w)
        self.assertIn("![[Weekly Review 2026-W47#2026-W47 Goals]]", w)
        self.assertIn('dv.date("2026-11-22")', w)
        m = self.read(os.path.relpath(planner.cmd_render(self.v, "monthly", D(2026, 11, 24)), self.v))
        self.assertIn("![[Monthly Review 2026-10#Next Month Priorities]]", m)
        self.assertIn("month_end: 2026-11-30", m)
        self.assertNotIn("<%", w + m)

    def test_render_never_overwrites(self):
        p = planner.cmd_render(self.v, "daily", D(2026, 11, 24))
        with open(p, "a") as f:
            f.write("\nI wrote this\n")
        planner.cmd_render(self.v, "daily", D(2026, 11, 24))
        self.assertIn("I wrote this", self.read("reviews/daily/2026-11-24.md"))


class VaultResolution(unittest.TestCase):
    def setUp(self):
        self.v = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.v, ".obsidian"))

    def tearDown(self):
        shutil.rmtree(self.v)

    def run_cli(self, *args, env=None, cwd=None):
        e = dict(os.environ)
        e.pop("VAULT_OS_VAULT_ROOT", None)
        e.update(env or {})
        return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, env=e, cwd=cwd)

    def test_bundled_templates_when_vault_has_none(self):
        r = self.run_cli("--vault", self.v, "render", "daily", "2026-11-24")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "reviews/daily/2026-11-24.md")
        with open(os.path.join(self.v, "reviews/daily/2026-11-24.md")) as f:
            self.assertIn("<!-- planner:focus -->", f.read())

    def test_vault_templates_win_over_bundled(self):
        os.makedirs(os.path.join(self.v, "templates"))
        with open(os.path.join(self.v, "templates", "daily.md"), "w") as f:
            f.write("# own template\n")
        self.run_cli("--vault", self.v, "render", "daily", "2026-11-24")
        with open(os.path.join(self.v, "reviews/daily/2026-11-24.md")) as f:
            self.assertEqual(f.read(), "# own template\n")

    def test_env_var_names_the_vault(self):
        r = self.run_cli("render", "weekly", "2026-11-24", env={"VAULT_OS_VAULT_ROOT": self.v}, cwd=tempfile.gettempdir())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.v, "reviews/weekly/Weekly Review 2026-W48.md")))

    def test_refuses_a_folder_that_is_not_a_vault(self):
        bare = tempfile.mkdtemp()
        try:
            r = self.run_cli("render", "daily", "2026-11-24", cwd=bare)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("does not look like an Obsidian vault", r.stderr)
            self.assertFalse(os.path.exists(os.path.join(bare, "reviews")))
        finally:
            shutil.rmtree(bare)

    def test_paths_needs_no_vault(self):
        bare = tempfile.mkdtemp()
        try:
            r = self.run_cli("paths", "2026-11-25", cwd=bare)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Weekly Review 2026-W48", r.stdout)
        finally:
            shutil.rmtree(bare)


class Blocks(VaultCase):
    def test_block_add_keeps_ticks_and_skips_duplicates(self):
        p = planner.cmd_render(self.v, "daily", D(2026, 11, 24))
        planner.block_add(p, "promises", "- [ ] #promise Send Alex the draft plan [to:: Alex] [due:: 2026-11-25]")
        text = self.read("reviews/daily/2026-11-24.md").replace("- [ ] #promise Send Alex", "- [x] #promise Send Alex")
        with open(p, "w") as f:
            f.write(text)
        n = planner.block_add(p, "promises", "- [ ] #promise Send Alex the draft plan [to:: Alex] [due:: 2026-11-26]\n- [ ] #promise Book the room [to:: Team]")
        self.assertEqual(n, 1)
        text = self.read("reviews/daily/2026-11-24.md")
        self.assertIn("- [x] #promise Send Alex the draft plan", text)
        self.assertEqual(text.count("Send Alex the draft plan"), 1)
        self.assertIn("Book the room", text)

    def test_block_set_only_touches_block(self):
        p = planner.cmd_render(self.v, "daily", D(2026, 11, 24))
        before = self.read("reviews/daily/2026-11-24.md")
        planner.block_set(p, "prep", "**Meetings**\n- 9:00 Stand-up")
        planner.block_set(p, "prep", "**Meetings**\n- 10:00 Planning")
        after = self.read("reviews/daily/2026-11-24.md")
        self.assertIn("- 10:00 Planning", after)
        self.assertNotIn("9:00 Stand-up", after)
        self.assertEqual(before.replace("<!-- planner:prep -->\n", ""), after.replace("<!-- planner:prep -->\n**Meetings**\n- 10:00 Planning\n", ""))

    def test_old_note_without_blocks_gets_section(self):
        os.makedirs(self.path("reviews/daily"))
        with open(self.path("reviews/daily/2026-10-13.md"), "w") as f:
            f.write("---\ntags:\n  - daily\n---\n# Old\n\n## Focus\n\n- [ ] thing\n")
        planner.block_add(self.path("reviews/daily/2026-10-13.md"), "decisions", "- #decision Use plan A [review:: 2026-11-13]")
        text = self.read("reviews/daily/2026-10-13.md")
        self.assertIn("## Decisions\n\n<!-- planner:decisions -->\n- #decision Use plan A", text)


class Scorecard(VaultCase):
    def write_day(self, day, focus, promises="", decisions=""):
        p = planner.cmd_render(self.v, "daily", day)
        with open(p) as f:
            text = f.read().replace("- [ ]\n- [ ]\n- [ ]\n", focus, 1)
        with open(p, "w") as f:
            f.write(text)
        if promises:
            planner.block_add(p, "promises", promises)
        if decisions:
            planner.block_add(p, "decisions", decisions)
        return p

    def test_scorecard_open_items_and_stats(self):
        self.write_day(
            D(2026, 11, 23),
            "- [x] Write the plan\n- [ ] Review the budget\n- [ ]\n",
            "- [ ] #promise Send Alex the draft plan [to:: Alex] [due:: 2026-11-24]\n- [x] #promise Share notes [to:: Kim] [due:: 2026-11-23]",
            "- #decision Pilot option B first [expect:: fewer repeat tickets] [confidence:: 60] [review:: 2026-11-24]",
        )
        p = self.write_day(D(2026, 11, 24), "- [x] Review the budget\n- [x] Prep the demo\n- [ ] Call the vendor\n")

        s = planner.cmd_scorecard(self.v, p, 3.5)
        self.assertEqual(s["focus_done"], 2)
        self.assertEqual(s["focus_total"], 3)
        self.assertEqual(s["promises_due"], 1)
        self.assertEqual(s["promises_kept"], 0)
        self.assertEqual(s["carried"], 1)
        text = self.read("reviews/daily/2026-11-24.md")
        self.assertIn("focus_done: 2\n", text)
        self.assertIn("meeting_hours: 3.5\n", text)
        self.assertIn("Focus 2/3 · Promises kept 0/1 due, 0 new", text)

        o = planner.cmd_open_items(self.v, D(2026, 11, 25))
        self.assertEqual(o["carried"], ["Call the vendor"])
        self.assertEqual([x["text"][:19] for x in o["promises_due"]], ["#promise Send Alex "])
        self.assertEqual(len(o["decisions_to_review"]), 1)
        self.assertEqual(o["decisions_to_review"][0]["confidence"], "60")

        planner.cmd_scorecard(self.v, self.path("reviews/daily/2026-11-23.md"), 5)
        st = planner.cmd_stats(self.v, D(2026, 11, 22), D(2026, 11, 28))
        self.assertEqual(st["days_with_notes"], 2)
        self.assertEqual(st["totals"]["focus_done"], 3)
        self.assertEqual(st["focus_hit_rate_pct"], 60)
        self.assertEqual(st["promise_kept_rate_pct"], 50)
        self.assertEqual(len(st["promises_missed"]), 1)


class TodosAndTime(VaultCase):
    write_day = Scorecard.write_day

    def test_emoji_due_dates_and_todos(self):
        self.write_day(
            D(2026, 11, 23),
            "",
            "- [ ] #promise Send Sam the labels [to:: Sam] \U0001F4C5 2026-11-24\n"
            "- [ ] #todo Answer the Friday invite \U0001F4C5 2026-11-25 [est:: 5m]\n"
            "- [ ] #todo Book the room\n"
            "- [ ] #todo Plan next quarter \U0001F4C5 2026-12-20\n",
        )
        o = planner.cmd_open_items(self.v, D(2026, 11, 24))
        self.assertEqual([p["to"] for p in o["promises_due"]], ["Sam"])
        self.assertEqual(o["promises_due"][0]["due"], "2026-11-24")
        self.assertEqual([t["est"] for t in o["todos_due_soon"]], ["5m"])
        self.assertEqual(len(o["todos_undated"]), 1)

    def test_time_strip_merges_overlaps_and_finds_open_block(self):
        out = planner.cmd_time_strip({
            "Mon": [["09:00", "10:00"], ["09:30", "11:00"], ["15:00", "16:00"]],
            "Thu": {"events": [], "note": "Holiday"},
        })
        lines = out.split("\n")
        self.assertEqual(lines[0], "```")
        self.assertIn("3.0 h", lines[1])
        self.assertIn("open 11:00\u20133:00", lines[1])
        self.assertTrue(lines[1].startswith("Mon \u2588\u2588\u2588\u2591"))
        self.assertIn("0.0 h", lines[2])
        self.assertIn("open 8:00\u20135:00 \u00b7 Holiday", lines[2])

    def test_templates_have_due_queries_and_todo_block(self):
        planner.cmd_render(self.v, "daily", D(2026, 11, 24))
        planner.cmd_render(self.v, "weekly", D(2026, 11, 24))
        daily = self.read("reviews/daily/2026-11-24.md")
        weekly = self.read("reviews/weekly/Weekly Review 2026-W48.md")
        for text in (daily, weekly):
            self.assertIn("```tasks", text)
            self.assertIn("task.due.fromNow.groupText", text)
        self.assertIn("<!-- planner:todo -->", daily)
        self.assertIn("## This week", weekly)


class MeetingOutcomes(VaultCase):
    def test_outcomes_count_in_scorecard_and_stats(self):
        p = planner.cmd_render(self.v, "daily", D(2026, 11, 24))
        self.assertIn("<!-- planner:meetings -->", self.read("reviews/daily/2026-11-24.md"))
        planner.block_set(
            p,
            "meetings",
            "**10:00 Sam 1:1** \u00b7 decide\n"
            "- **Ask:** which vendor?\n"
            "- [x] #outcome Vendor picked [mtg:: Sam 1:1]\n"
            "**2:00 Planning** \u00b7 discuss\n"
            "- [ ] #outcome Dates agreed [mtg:: Planning]\n",
        )
        s = planner.cmd_scorecard(self.v, p, 1.5)
        self.assertEqual((s["outcomes_hit"], s["outcomes_total"]), (1, 2))
        text = self.read("reviews/daily/2026-11-24.md")
        self.assertIn("outcomes_hit: 1\n", text)
        self.assertIn("outcomes 1/2", text)
        st = planner.cmd_stats(self.v, D(2026, 11, 22), D(2026, 11, 28))
        self.assertEqual(st["meeting_outcome_rate_pct"], 50)


class FocusFill(VaultCase):
    write_day = Scorecard.write_day

    def test_candidates_rank_overdue_goal_promise_first(self):
        planner.cmd_render(self.v, "weekly", D(2026, 11, 24))
        wk = os.path.join(self.v, "reviews/weekly/Weekly Review 2026-W48.md")
        planner.block_set(wk, "suggested-goals", "- Suggestion: Vendor contract signed with Sam.")
        self.write_day(
            D(2026, 11, 23),
            "",
            "- [ ] #promise Send Kim the notes [to:: Kim]\n"
            "- [ ] #promise Get the vendor contract signed [to:: Sam] \U0001F4C5 2026-11-20\n",
        )
        c = planner.cmd_focus_candidates(self.v, D(2026, 11, 24))
        self.assertFalse(c["goals_are_his"])
        top = c["candidates"][0]
        self.assertIn("vendor contract", top["text"])
        self.assertEqual((top["quadrant"], top["overdue_days"]), ("do first", 4))
        self.assertEqual(c["candidates"][1]["quadrant"], "schedule")

    def test_fill_only_while_empty_and_upgrades_old_notes(self):
        p = planner.cmd_render(self.v, "daily", D(2026, 11, 24))
        items = "- [ ] Ship the plan \U0001F4C5 2026-11-24 [why:: owed]\n- [ ] Call Sam\n- [ ] Book room\n- [ ] Fourth"
        self.assertTrue(planner.focus_fill(p, items))
        text = self.read("reviews/daily/2026-11-24.md")
        self.assertEqual(len(planner.focus_items(text)), 3)
        self.assertFalse(planner.focus_fill(p, "- [ ] Something else"))
        self.assertIn("Ship the plan", self.read("reviews/daily/2026-11-24.md"))
        # A note made before the focus block existed.
        old = text.replace("<!-- planner:focus -->\n", "").replace("<!-- /planner:focus -->\n", "")
        old = old.split("## Focus")[0] + "## Focus\n\n- [ ]\n- [ ]\n- [ ]\n\n---\n" + old.split("## Focus", 1)[1].split("---\n", 1)[1]
        with open(p, "w") as f:
            f.write(old)
        self.assertTrue(planner.focus_fill(p, "- [ ] Call Sam"))
        self.assertIn("<!-- planner:focus -->\n- [ ] Call Sam\n<!-- /planner:focus -->\n\n---", self.read("reviews/daily/2026-11-24.md"))


if __name__ == "__main__":
    unittest.main()
