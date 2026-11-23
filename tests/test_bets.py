"""Hermetic tests for scripts/bets.py. Fake bets only.

Notes are created from the starter template in skills/bets/templates/bet.md.

Usage:
  python3 tests/test_bets.py
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
SCRIPT = os.path.join(REPO_ROOT, "scripts", "bets.py")
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
import bets  # noqa: E402

D = dt.date
TODAY = D(2026, 11, 23)
T = bets.Thresholds()


def bet(**kw):
    """A parsed bet with every field present, for rule tests."""
    base = {"file": "", "note": kw.get("bet", "A bet"), "bet": "A bet", "owner": "Alex", "area": "work",
            "cycle": "", "appetite": "", "cycle_start": "2026-11-02", "cycle_end": "2026-12-11",
            "started": "2026-11-03", "shipped": "", "dropped": "", "outcome": "", "source": "",
            "milestones": [], "kpis": [], "readings": [], "blockers": [],
            "signals": [{"date": "2026-11-20", "text": "Demo went fine", "call": None}]}
    base.update(kw)
    return base


def status(b, today=TODAY, t=T):
    s = bets.score_bet(b, today, t)
    return s["status"], s["status_reason"]


class Kpis(unittest.TestCase):
    def kpi(self, baseline, target, value, direction=None):
        k = {"metric": "Tickets", "baseline": baseline, "target": target, "read_by": "2026-12-01", "direction": direction}
        r = [{"date": "2026-12-02", "metric": "Tickets", "value": value}] if value is not None else []
        return bets.kpi_result(k, r)["result"]

    def test_lower_is_better_when_target_below_baseline(self):
        self.assertEqual(self.kpi("40", "25", "25"), "hit")
        self.assertEqual(self.kpi("40", "25", "20"), "hit")
        self.assertEqual(self.kpi("40", "25", "32"), "partial")
        self.assertEqual(self.kpi("40", "25", "41"), "missed")
        self.assertEqual(self.kpi("40", "25", "40"), "missed")

    def test_higher_is_better_when_target_above_baseline(self):
        self.assertEqual(self.kpi("60%", "75%", "80%"), "hit")
        self.assertEqual(self.kpi("60%", "75%", "70%"), "partial")
        self.assertEqual(self.kpi("60%", "75%", "55%"), "missed")

    def test_no_baseline_is_hit_or_missed(self):
        self.assertEqual(self.kpi("", "100", "120"), "hit")
        self.assertEqual(self.kpi("", "100", "90"), "missed")
        self.assertEqual(self.kpi("", "10", "5", direction="down"), "hit")

    def test_no_reading(self):
        self.assertEqual(self.kpi("40", "25", None), "not-read")

    def test_latest_reading_wins(self):
        k = {"metric": "Tickets", "baseline": "40", "target": "25", "read_by": "", "direction": None}
        r = [{"date": "2026-12-09", "metric": "tickets", "value": "24"},
             {"date": "2026-12-02", "metric": "Tickets", "value": "35"}]
        out = bets.kpi_result(k, r)
        self.assertEqual((out["result"], out["reading"], out["read_on"]), ("hit", 24.0, "2026-12-09"))

    def test_combine(self):
        self.assertEqual(bets.combine_results([]), "no-kpi")
        self.assertEqual(bets.combine_results(["not-read"]), "not-read")
        self.assertEqual(bets.combine_results(["hit", "hit"]), "hit")
        self.assertEqual(bets.combine_results(["missed", "not-read"]), "missed")
        self.assertEqual(bets.combine_results(["hit", "missed"]), "partial")


class Delivery(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(bets.delivery(bet(shipped="2026-12-10"), TODAY), "on-time")
        self.assertEqual(bets.delivery(bet(shipped="2026-12-15"), TODAY), "late")
        self.assertEqual(bets.delivery(bet(cycle_end="2026-11-20"), TODAY), "not-shipped")
        self.assertEqual(bets.delivery(bet(dropped="2026-11-10", shipped="2026-11-12"), TODAY), "dropped")
        self.assertEqual(bets.delivery(bet(cycle_start="2026-12-01"), TODAY), "upcoming")
        self.assertEqual(bets.delivery(bet(), TODAY), "in-progress")


class Status(unittest.TestCase):
    def test_on_track(self):
        self.assertEqual(status(bet()), ("on-track", ""))

    def test_owner_called_off_track(self):
        b = bet(signals=[{"date": "2026-11-21", "text": "Slipped", "call": "off-track"}])
        self.assertEqual(status(b)[0], "off-track")
        self.assertIn("owner called it off track", status(b)[1])

    def test_later_on_track_call_clears_it(self):
        b = bet(signals=[{"date": "2026-11-18", "text": "Slipped", "call": "off-track"},
                         {"date": "2026-11-21", "text": "Recovered", "call": "on-track"}])
        self.assertEqual(status(b)[0], "on-track")

    def test_milestone_date_passed(self):
        b = bet(milestones=[{"done": False, "text": "Pilot live", "due": "2026-11-20", "done_on": None}])
        self.assertEqual(status(b), ("off-track", 'milestone "Pilot live" was due Nov 20, 2026'))

    def test_ticked_milestone_does_not_count(self):
        b = bet(milestones=[{"done": True, "text": "Pilot live", "due": "2026-11-20", "done_on": "2026-11-19"}])
        self.assertEqual(status(b)[0], "on-track")

    def test_cycle_over_not_shipped(self):
        b = bet(cycle_end="2026-11-20")
        self.assertEqual(status(b), ("off-track", "cycle ended Nov 20, 2026 and it has not shipped"))

    def test_old_blocker_drifts(self):
        b = bet(blockers=[{"open": True, "text": "Vendor quote", "opened": "2026-11-15", "cleared": None}])
        self.assertEqual(status(b), ("drifting", "blocker open 8 days: Vendor quote"))

    def test_young_or_cleared_blocker_is_fine(self):
        young = bet(blockers=[{"open": True, "text": "Vendor quote", "opened": "2026-11-20", "cleared": None}])
        cleared = bet(blockers=[{"open": False, "text": "Vendor quote", "opened": "2026-11-01", "cleared": "2026-11-05"}])
        self.assertEqual(status(young)[0], "on-track")
        self.assertEqual(status(cleared)[0], "on-track")

    def test_blocker_threshold_is_configurable(self):
        b = bet(blockers=[{"open": True, "text": "Vendor quote", "opened": "2026-11-15", "cleared": None}])
        self.assertEqual(status(b, t=bets.Thresholds(blocker_days=10))[0], "on-track")

    def test_close_date_and_not_started_drifts(self):
        b = bet(started="", cycle_end="2026-12-04")
        self.assertEqual(status(b), ("drifting", "Dec 4, 2026 is 11 days away and work has not started"))
        b = bet(started="", milestones=[{"done": False, "text": "Spec", "due": "2026-11-30", "done_on": None}])
        self.assertEqual(status(b)[0], "drifting")

    def test_ticked_milestone_counts_as_started(self):
        b = bet(started="", cycle_end="2026-12-04",
                milestones=[{"done": True, "text": "Spec", "due": "2026-11-20", "done_on": "2026-11-19"}])
        self.assertEqual(status(b)[0], "on-track")

    def test_far_date_not_started_is_fine(self):
        self.assertEqual(status(bet(started="", cycle_end="2027-01-29"))[0], "on-track")

    def test_no_owner_stalls(self):
        self.assertEqual(status(bet(owner="")), ("stalled", "no owner"))

    def test_no_signal_for_a_week_stalls(self):
        b = bet(signals=[{"date": "2026-11-12", "text": "Kickoff", "call": None}])
        self.assertEqual(status(b), ("stalled", "no signal for 11 days"))
        self.assertEqual(status(b, t=bets.Thresholds(stale_days=14))[0], "on-track")

    def test_no_signals_counts_from_start(self):
        self.assertEqual(status(bet(signals=[], started="2026-11-03")),
                         ("stalled", "no signal since the cycle started Nov 3, 2026"))
        self.assertEqual(status(bet(signals=[], started="2026-11-20"))[0], "on-track")

    def test_order_off_track_before_drifting_before_stalled(self):
        b = bet(owner="", cycle_end="2026-11-20",
                blockers=[{"open": True, "text": "X", "opened": "2026-11-01", "cleared": None}])
        self.assertEqual(status(b)[0], "off-track")
        b = bet(owner="", blockers=[{"open": True, "text": "X", "opened": "2026-11-01", "cleared": None}])
        self.assertEqual(status(b)[0], "drifting")

    def test_finished_and_future_bets(self):
        self.assertEqual(status(bet(shipped="2026-11-20"))[0], "shipped")
        self.assertEqual(status(bet(shipped="2026-12-20"))[1], "shipped Dec 20, 2026 (late)")
        self.assertEqual(status(bet(dropped="2026-11-20"))[0], "dropped")
        self.assertEqual(status(bet(cycle_start="2026-12-07", started=""))[0], "upcoming")
        self.assertEqual(status(bet(cycle_start="2026-12-07", owner=""))[0], "stalled")

    def test_user_outcome_wins_over_kpi(self):
        b = bet(shipped="2026-11-20", outcome="hit",
                kpis=[{"metric": "Tickets", "baseline": "40", "target": "25", "read_by": "", "direction": None}],
                readings=[{"date": "2026-11-21", "metric": "Tickets", "value": "41"}])
        s = bets.score_bet(b, TODAY, T)
        self.assertEqual((s["kpi_result"], s["final_outcome"], s["outcome_by"]), ("missed", "hit", "user"))


class FollowUps(unittest.TestCase):
    def fus(self, *bs):
        scored = [bets.score_bet(b, TODAY, T) for b in bs]
        return bets.follow_ups(scored, TODAY, T)

    def test_kpi_reading_past_read_date_is_asked_of_owner(self):
        k = [{"metric": "Tickets", "baseline": "40", "target": "25", "read_by": "2026-11-16", "direction": None}]
        fus = self.fus(bet(shipped="2026-11-10", kpis=k))
        self.assertEqual([(f["owner"], f["kind"], f["days_overdue"]) for f in fus], [("Alex", "kpi-reading", 7)])
        early = [{"date": "2026-11-10", "metric": "Tickets", "value": "30"}]
        self.assertEqual(len(self.fus(bet(shipped="2026-11-10", kpis=k, readings=early))), 1)
        on_time = [{"date": "2026-11-16", "metric": "Tickets", "value": "30"}]
        self.assertEqual(self.fus(bet(shipped="2026-11-10", kpis=k, readings=on_time)), [])

    def test_future_read_date_is_not_asked(self):
        k = [{"metric": "Tickets", "baseline": "40", "target": "25", "read_by": "2026-12-16", "direction": None}]
        self.assertEqual(self.fus(bet(shipped="2026-11-10", kpis=k)), [])

    def test_kinds_and_order(self):
        fus = self.fus(
            bet(bet="B", note="B", owner="Sam", blockers=[{"open": True, "text": "Access", "opened": "2026-11-10", "cleared": None}]),
            bet(bet="A", note="A", owner="Sam", signals=[{"date": "2026-11-01", "text": "x", "call": None}]),
            bet(bet="C", note="C", owner=""),
            bet(bet="D", note="D", owner="Sam", cycle_end="2026-11-20"),
            bet(bet="E", note="E", owner="Sam", dropped="2026-11-01", cycle_end="2026-11-20"),
        )
        self.assertEqual([(f["owner"], f["kind"], f["bet"]) for f in fus], [
            ("(no owner)", "owner", "C"),
            ("Sam", "off-track", "D"),
            ("Sam", "blocker", "B"),
            ("Sam", "update", "A"),
        ])


class VaultCase(unittest.TestCase):
    def setUp(self):
        self.v = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.v, ".obsidian"))

    def tearDown(self):
        shutil.rmtree(self.v)

    def cli(self, *args, stdin=None, ok=True):
        e = dict(os.environ)
        e.pop("VAULT_OS_VAULT_ROOT", None)
        r = subprocess.run([sys.executable, SCRIPT, "--vault", self.v, *args], input=stdin,
                           capture_output=True, text=True, env=e)
        if ok:
            self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def read(self, rel):
        with open(os.path.join(self.v, rel), encoding="utf-8") as f:
            return f.read()

    def new(self, *items):
        return self.cli("new", stdin=json.dumps(list(items))).stdout


class NewNotes(VaultCase):
    def test_batch_backfill_from_template(self):
        out = self.new(
            {"bet": "Checkout redesign: phase 1", "owner": "Alex", "cycle": "Cycle 3",
             "cycle_start": "2026-09-01", "cycle_end": "2026-10-12", "shipped": "2026-10-10", "source": "backfill",
             "problem": "Too many abandoned carts.",
             "milestones": [{"text": "New cart page live", "due": "2026-10-05", "done": True, "done_on": "2026-10-04"}],
             "kpis": [{"metric": "Cart abandonment %", "baseline": "68", "target": "55", "read_by": "2026-11-15"}],
             "readings": [{"date": "2026-11-16", "kpi": "Cart abandonment %", "value": "60"}],
             "signals": [{"date": "2026-10-10", "text": "Shipped to everyone"}]},
            {"bet": "Run a half marathon", "area": "life", "owner": "me", "cycle_start": "2026-11-01", "cycle_end": "2027-03-01"},
        )
        self.assertIn("created: bets/Checkout redesign phase 1.md", out)
        self.assertIn("created: bets/Run a half marathon.md", out)
        text = self.read("bets/Checkout redesign phase 1.md")
        self.assertIn('bet: "Checkout redesign: phase 1"', text)
        self.assertIn("# Checkout redesign: phase 1", text)
        self.assertIn("- [x] #milestone New cart page live \U0001F4C5 2026-10-05 [done:: 2026-10-04]", text)
        self.assertIn("- #kpi Cart abandonment % [baseline:: 68] [target:: 55] [read_by:: 2026-11-15]", text)
        self.assertIn("- 2026-11-16 #reading Cart abandonment % [value:: 60]", text)
        self.assertNotIn("{{", text)
        self.assertNotIn(" \n", text)
        b = bets.parse_bet(os.path.join(self.v, "bets/Checkout redesign phase 1.md"))
        self.assertEqual(b["bet"], "Checkout redesign: phase 1")
        self.assertEqual(len(b["milestones"]) + len(b["kpis"]) + len(b["readings"]) + len(b["signals"]), 4)
        self.assertEqual(b["kpis"][0]["metric"], "Cart abandonment %")
        self.assertEqual(bets.parse_bet(os.path.join(self.v, "bets/Run a half marathon.md"))["area"], "life")

    def test_never_overwrites(self):
        self.new({"bet": "Alpha"})
        with open(os.path.join(self.v, "bets/Alpha.md"), "a") as f:
            f.write("I wrote this\n")
        self.assertIn("exists: bets/Alpha.md", self.new({"bet": "Alpha", "owner": "Sam"}))
        self.assertIn("I wrote this", self.read("bets/Alpha.md"))

    def test_rejects_bad_input(self):
        for item in ({"owner": "Sam"}, {"bet": "X", "area": "hobby"}, {"bet": "X", "cycle_end": "next week"},
                     {"bet": "X", "outcome": "great"}):
            r = self.cli("new", stdin=json.dumps(item), ok=False)
            self.assertNotEqual(r.returncode, 0, item)
        self.assertFalse(os.path.exists(os.path.join(self.v, "bets/X.md")))

    def test_vault_template_wins(self):
        os.makedirs(os.path.join(self.v, "templates"))
        with open(os.path.join(self.v, "templates", "bet.md"), "w") as f:
            f.write("---\ntype: bet\nbet: {{bet}}\nowner: {{owner}}\n---\n# {{bet}}\nOwn template\n")
        self.new({"bet": "Alpha", "owner": "Sam"})
        self.assertIn("Own template", self.read("bets/Alpha.md"))


class Appends(VaultCase):
    def setUp(self):
        super().setUp()
        self.new({"bet": "Alpha", "owner": "Sam", "cycle_start": "2026-11-02", "cycle_end": "2026-12-11",
                  "kpis": [{"metric": "Repeat tickets", "baseline": "40", "target": "25", "read_by": "2026-12-18"}]})

    def test_signal_blocker_milestone_tick_reading(self):
        self.assertEqual(self.cli("signal", "Alpha", "Kickoff done", "--date", "2026-11-03").stdout.strip(), "added")
        self.assertEqual(self.cli("signal", "Alpha", "Kickoff done", "--date", "2026-11-03").stdout.strip(), "already there")
        self.cli("signal", "bets/Alpha.md", "Pilot slipped", "--date", "2026-11-21", "--call", "off-track")
        self.cli("blocker", "Alpha", "Waiting on access", "--date", "2026-11-10")
        self.cli("milestone", "Alpha", "Pilot at 5 sites", "--due", "2026-11-27")
        self.cli("kpi", "Alpha", "Setup time minutes", "--baseline", "90", "--target", "30", "--read-by", "2026-12-18")
        self.cli("reading", "Alpha", "repeat tickets", "33", "--date", "2026-11-22")
        self.cli("tick", "Alpha", "access", "--date", "2026-11-22")
        text = self.read("bets/Alpha.md")
        self.assertIn("- 2026-11-21 Pilot slipped #off-track", text)
        self.assertIn("- [x] #blocker Waiting on access [opened:: 2026-11-10] [done:: 2026-11-22]", text)
        self.assertIn("- [ ] #milestone Pilot at 5 sites \U0001F4C5 2026-11-27", text)
        self.assertIn("- 2026-11-22 #reading Repeat tickets [value:: 33]", text)
        b = bets.parse_bet(os.path.join(self.v, "bets/Alpha.md"))
        self.assertEqual([s["call"] for s in b["signals"]], [None, "off-track"])
        self.assertEqual(b["signals"][1]["text"], "Pilot slipped")
        self.assertEqual(len(b["kpis"]), 2)
        self.assertFalse(b["blockers"][0]["open"])
        # Lines land inside their own section.
        sig = text.index("## Signals")
        self.assertTrue(sig < text.index("Pilot slipped") < text.index("## Notes"))

    def test_reading_needs_a_known_kpi_and_a_number(self):
        self.assertNotEqual(self.cli("reading", "Alpha", "Unknown", "3", ok=False).returncode, 0)
        self.assertNotEqual(self.cli("reading", "Alpha", "Repeat tickets", "lots", ok=False).returncode, 0)

    def test_tick_needs_one_match(self):
        self.cli("milestone", "Alpha", "Pilot A", "--due", "2026-11-27")
        self.cli("milestone", "Alpha", "Pilot B", "--due", "2026-11-28")
        self.assertNotEqual(self.cli("tick", "Alpha", "Pilot", ok=False).returncode, 0)
        self.cli("tick", "Alpha", "Pilot B")

    def test_set_only_user_fields(self):
        out = json.loads(self.cli("set", "Alpha", "shipped=2026-12-10", "outcome=partial").stdout)
        self.assertEqual(out, {"shipped": "2026-12-10", "outcome": "partial"})
        self.assertIn("shipped: 2026-12-10", self.read("bets/Alpha.md"))
        for bad in ("status=on-track", "shipped=soon", "outcome=great", "area=hobby"):
            self.assertNotEqual(self.cli("set", "Alpha", bad, ok=False).returncode, 0, bad)

    def test_refuses_a_note_that_is_not_a_bet(self):
        with open(os.path.join(self.v, "bets", "Readme.md"), "w") as f:
            f.write("# Not a bet\n")
        self.assertNotEqual(self.cli("signal", "Readme", "x", ok=False).returncode, 0)


class Score(VaultCase):
    def setUp(self):
        super().setUp()
        self.new(
            {"bet": "Alpha", "owner": "Sam", "cycle_start": "2026-11-02", "cycle_end": "2026-12-11", "started": "2026-11-03",
             "signals": [{"date": "2026-11-21", "text": "On plan"}]},
            {"bet": "Beta", "owner": "Alex", "cycle_start": "2026-11-02", "cycle_end": "2026-12-11", "started": "2026-11-03",
             "milestones": [{"text": "Pilot", "due": "2026-11-20"}], "signals": [{"date": "2026-11-21", "text": "Late"}]},
            {"bet": "Gamma", "owner": "Alex", "cycle_start": "2026-09-01", "cycle_end": "2026-10-12", "shipped": "2026-10-10",
             "kpis": [{"metric": "Tickets", "baseline": "40", "target": "25", "read_by": "2026-11-15"}]},
            {"bet": "Delta", "owner": "Sam", "cycle_start": "2026-09-01", "cycle_end": "2026-10-12", "shipped": "2026-10-20",
             "kpis": [{"metric": "Tickets", "baseline": "40", "target": "25", "read_by": "2026-11-01"}],
             "readings": [{"date": "2026-11-02", "kpi": "Tickets", "value": "22"}]},
            {"bet": "Long run", "area": "life", "owner": "me", "cycle_start": "2026-11-01", "cycle_end": "2027-03-01",
             "started": "2026-11-01", "signals": [{"date": "2026-11-22", "text": "10 km"}]},
        )

    def test_score_writes_fields_and_radar(self):
        out = json.loads(self.cli("score", "--today", "2026-11-23").stdout)
        self.assertEqual(out["bets"], 5)
        self.assertEqual(out["status"]["off-track"], 1)
        self.assertEqual(out["status"]["shipped"], 2)
        self.assertEqual(out["notes_updated"], 5)
        beta = self.read("bets/Beta.md")
        self.assertIn("status: off-track", beta)
        self.assertIn('status_reason: milestone "Pilot" was due Nov 20, 2026', beta)
        self.assertIn("kpi_result: hit", self.read("bets/Delta.md"))
        self.assertIn("delivery: late", self.read("bets/Delta.md"))
        radar = self.read("bets/Bet Radar.md")
        self.assertIn("| [[Beta]] | Alex | 🔴 off track |", radar)
        self.assertIn("Get the KPI reading: Tickets (due Nov 15, 2026) (8 days overdue) · [[Gamma]]", radar)
        self.assertIn("| Shipped on time | · | · | · | 1 | · | 1 |", radar)
        self.assertIn("| Shipped late | 1 | · | · | · | · | 1 |", radar)
        self.assertIn("Shipped on time: 1 of 2. Outcome hit: 1 of 1 with a result. 1 still have no result.", radar)
        self.assertIn("```dataview", radar)
        # The radar itself is not read as a bet.
        self.assertEqual(len(json.loads(self.cli("list", "--today", "2026-11-23").stdout)), 5)

    def test_second_run_changes_nothing(self):
        self.cli("score", "--today", "2026-11-23")
        before = {n: self.read(f"bets/{n}") for n in os.listdir(os.path.join(self.v, "bets"))}
        out = json.loads(self.cli("score", "--today", "2026-11-23").stdout)
        self.assertEqual(out["notes_updated"], 0)
        after = {n: self.read(f"bets/{n}") for n in os.listdir(os.path.join(self.v, "bets"))}
        self.assertEqual(before, after)

    def test_user_text_survives_scoring(self):
        with open(os.path.join(self.v, "bets/Alpha.md"), "a") as f:
            f.write("My own note\n")
        self.cli("score", "--today", "2026-11-23")
        self.assertIn("My own note", self.read("bets/Alpha.md"))

    def test_area_filter(self):
        self.cli("score", "--today", "2026-11-23", "--area", "life", "--out", "bets/Life radar.md")
        radar = self.read("bets/Life radar.md")
        self.assertIn("[[Long run]]", radar)
        self.assertNotIn("[[Alpha]]", radar)
        self.assertIn('WHERE type = "bet" AND area = "life"', radar)

    def test_thresholds_from_config_and_flags(self):
        self.new({"bet": "Quiet", "owner": "Sam", "cycle_start": "2026-11-02", "cycle_end": "2026-12-31",
                  "started": "2026-11-03", "signals": [{"date": "2026-11-13", "text": "x"}]})
        quiet = lambda *a: next(b for b in json.loads(self.cli("list", "--today", "2026-11-23", *a).stdout) if b["bet"] == "Quiet")["status"]
        self.assertEqual(quiet(), "stalled")
        with open(os.path.join(self.v, "bets", "bets-config.json"), "w") as f:
            json.dump({"stale_days": 14}, f)
        self.assertEqual(quiet(), "on-track")
        self.assertEqual(quiet("--stale-days", "5"), "stalled")

    def test_follow_ups_json(self):
        fus = json.loads(self.cli("follow-ups", "--today", "2026-11-23").stdout)
        self.assertEqual([(f["owner"], f["kind"], f["bet"]) for f in fus],
                         [("Alex", "off-track", "Beta"), ("Alex", "kpi-reading", "Gamma")])


class Frontmatter(unittest.TestCase):
    def test_yaml_values_round_trip(self):
        for s in ("Plain name", "Name: with colon", "#hash first", "yes", "- dash", 'Say "hi": now', "2026-11-23", "42"):
            text = bets.write_fields("---\nbet:\n---\n", {"bet": s})
            self.assertEqual(bets.read_frontmatter(text)["bet"], s, s)

    def test_safe_name(self):
        self.assertEqual(bets.safe_name("A/B: C?"), "A B C")
        self.assertEqual(bets.safe_name("  ..  "), "Untitled bet")


if __name__ == "__main__":
    unittest.main(verbosity=1)
