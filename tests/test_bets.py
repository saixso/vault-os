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


def scored(b, today=TODAY, t=T):
    return bets.score_bet(b, today, t)


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
    def test_user_status_and_rating_pass_through(self):
        b = bet(status="done", rating="won", cycle_end="2026-11-20")
        s = scored(b)
        self.assertEqual((s["status"], s["rating"]), ("done", "won"))

    def test_cycle_end_does_not_decide_status(self):
        s = scored(bet(status="in progress", cycle_end="2026-11-20", shipped=""))
        self.assertEqual(s["status"], "in progress")

    def test_old_or_blank_status_is_not_one_of_the_three(self):
        self.assertEqual(scored(bet(status="off-track"))["status"], "")
        self.assertEqual(scored(bet(status=""))["status"], "")
        self.assertEqual(scored(bet(rating="great"))["rating"], "")


class FollowUps(unittest.TestCase):
    def fus(self, *bs):
        rows = [bets.score_bet(b, TODAY, T) for b in bs]
        return bets.follow_ups(rows, TODAY, T)

    def test_asks_for_status_and_for_a_rating_once_done(self):
        fus = self.fus(
            bet(bet="C", note="C", owner="", status=""),
            bet(bet="D", note="D", owner="Sam", status="done", rating=""),
            bet(bet="A", note="A", owner="Sam", status="in progress", rating=""),
            bet(bet="B", note="B", owner="Sam", status="paused", rating=""),
            bet(bet="E", note="E", owner="Sam", status="done", rating="won"),
        )
        self.assertEqual([(f["owner"], f["kind"], f["bet"]) for f in fus], [
            ("(no owner)", "owner", "C"),
            ("(no owner)", "status", "C"),
            ("Sam", "odds", "A"),
            ("Sam", "rating", "D"),
            ("Sam", "decision", "E"),
        ])

    def test_odds_asked_only_while_in_progress(self):
        fus = self.fus(
            bet(bet="A", note="A", status="in progress", odds="", wrong_if="Churn stays flat"),
            bet(bet="B", note="B", status="in progress", odds="60", wrong_if=""),
            bet(bet="C", note="C", status="in progress", odds="60", wrong_if="Churn stays flat"),
            bet(bet="D", note="D", status="paused", odds=""),
            bet(bet="E", note="E", status="done", rating="won", decision="good", odds=""),
            bet(bet="F", note="F", status="in progress", odds="60", wrong_if="Churn stays flat", stake="large"),
        )
        self.assertEqual([(f["kind"], f["bet"]) for f in fus], [("odds", "A"), ("odds", "B"), ("stake", "C")])

    def test_one_ask_for_both_ratings_when_neither_is_set(self):
        fus = self.fus(bet(bet="D", note="D", status="done", rating="", decision=""))
        self.assertEqual([f["kind"] for f in fus], ["rating"])
        self.assertIn("decision", fus[0]["ask"])
        fus = self.fus(bet(bet="D", note="D", status="done", rating="", decision="good"))
        self.assertNotIn("decision", fus[0]["ask"])


class Odds(unittest.TestCase):
    def test_forms(self):
        for given, want in (("60", 60), ("60%", 60), ("0.6", 60), ("0.65", 65), ("100", 100), ("0", 0),
                            ("1", 1), ("1.0", 100), ("12.5%", 12)):
            self.assertEqual(bets.parse_odds(given), want, given)
        for bad in ("", "high", "120", "-5", "60-70"):
            self.assertIsNone(bets.parse_odds(bad), bad)

    def test_decision_and_odds_pass_through_scoring(self):
        s = scored(bet(status="done", rating="lost", decision="Good", odds="70%"))
        self.assertEqual((s["decision"], s["odds"]), ("good", 70))
        self.assertEqual(scored(bet(stake="Large"))["stake"], "large")
        self.assertEqual(scored(bet(stake="huge"))["stake"], "")
        self.assertEqual(scored(bet(decision="fine"))["decision"], "")


class Calibration(unittest.TestCase):
    def done(self, odds, rating, decision="good"):
        return scored(bet(status="done", rating=rating, decision=decision, odds=odds))

    def test_average_odds_against_win_rate(self):
        cal = bets.calibration([self.done("80", "won"), self.done("80", "lost"), self.done("70", "lost"),
                                self.done("90", "push"), self.done("", "won")])
        self.assertEqual(cal, {"bets": 3, "average_odds": 77, "won": 1, "win_rate": 33})
        text = "\n".join(bets.calibration_text(cal))
        self.assertIn("The odds ran 44 points above the results.", text)
        self.assertIn("says little yet", text)

    def test_win_rate_by_stake(self):
        rows = [scored(bet(status="done", rating="won", stake="large", odds="80")),
                scored(bet(status="done", rating="lost", stake="large", odds="60")),
                scored(bet(status="done", rating="lost", stake="large")),
                scored(bet(status="done", rating="won", stake="small")),
                scored(bet(status="done", rating="push", stake="medium")),
                scored(bet(status="done", rating="won", stake=""))]
        out = bets.by_stake(rows)
        self.assertEqual(out, {"small": {"bets": 1, "won": 1, "win_rate": 100, "average_odds": None},
                               "large": {"bets": 3, "won": 1, "win_rate": 33, "average_odds": 70}})
        text = "\n".join(bets.stake_text(out))
        self.assertIn("| Large | 3 | 1 | 33% | 70% |", text)
        self.assertIn("| Small | 1 | 1 | 100% | — |", text)
        self.assertNotIn("Medium", text)

    def test_none_without_odds_and_a_result(self):
        self.assertIsNone(bets.calibration([self.done("", "won"), self.done("60", "push")]))

    def test_grid_places_a_good_call_that_lost_as_bad_luck(self):
        rows = [scored(bet(bet="Win", note="Win", status="done", rating="won", decision="good")),
                scored(bet(bet="Unlucky", note="Unlucky", status="done", rating="lost", decision="good")),
                scored(bet(bet="Lucky", note="Lucky", status="done", rating="won", decision="bad")),
                scored(bet(bet="Half", note="Half", status="done", rating="won", decision=""))]
        text = "\n".join(bets.grid_text(rows))
        self.assertIn("| Good | Earned it: 1<br>[[Win]] | Good call, even: 0 | Bad luck: 1<br>[[Unlucky]] |", text)
        self.assertIn("| Bad | Got lucky: 1<br>[[Lucky]] | Bad call, even: 0 | Learn from it: 0 |", text)
        self.assertIn("1 done bet is missing a decision or a result rating.", text)


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
        self.assertIn("status: in progress", text)
        self.assertIn("why: Too many abandoned carts.", text)
        self.assertIn("## Why\n\nToo many abandoned carts.", text)
        self.assertNotIn("## Milestones", text)
        self.assertNotIn("## Blockers", text)
        self.assertNotIn("{{", text)
        self.assertNotIn(" \n", text)
        b = bets.parse_bet(os.path.join(self.v, "bets/Checkout redesign phase 1.md"))
        self.assertEqual(b["bet"], "Checkout redesign: phase 1")
        self.assertEqual(b["status"], "in progress")
        self.assertEqual(b["why"], "Too many abandoned carts.")
        self.assertEqual(bets.parse_bet(os.path.join(self.v, "bets/Run a half marathon.md"))["area"], "life")

    def test_new_bet_with_odds_and_wrong_if(self):
        self.new({"bet": "Self-serve setup", "owner": "Sam", "why": "Setup calls take days.",
                  "odds": "0.6", "wrong_if": "Setup time does not drop in 6 weeks",
                  "stake": "Medium", "stake_note": "Six weeks of one engineer"})
        text = self.read("bets/Self-serve setup.md")
        self.assertIn("odds: 60\n", text)
        self.assertIn("wrong_if: Setup time does not drop in 6 weeks\n", text)
        self.assertIn("## Proved wrong if\n\nSetup time does not drop in 6 weeks", text)
        self.assertIn("stake: medium\nstake_note: Six weeks of one engineer\n", text)
        self.assertIn("## At stake\n\nmedium: Six weeks of one engineer", text)
        self.assertRegex(text, r"\ndecision: ?\n")
        b = bets.parse_bet(os.path.join(self.v, "bets/Self-serve setup.md"))
        self.assertEqual((b["odds"], b["wrong_if"], b["decision"]), ("60", "Setup time does not drop in 6 weeks", ""))

    def test_never_overwrites(self):
        self.new({"bet": "Alpha"})
        with open(os.path.join(self.v, "bets/Alpha.md"), "a") as f:
            f.write("I wrote this\n")
        self.assertIn("exists: bets/Alpha.md", self.new({"bet": "Alpha", "owner": "Sam"}))
        self.assertIn("I wrote this", self.read("bets/Alpha.md"))

    def test_rejects_bad_input(self):
        for item in ({"owner": "Sam"}, {"bet": "X", "area": "hobby"}, {"bet": "X", "cycle_end": "next week"},
                     {"bet": "X", "outcome": "great"}, {"bet": "X", "status": "off-track"},
                     {"bet": "X", "rating": "great"}, {"bet": "X", "decision": "fine"},
                     {"bet": "X", "odds": "likely"}, {"bet": "X", "odds": "150"}, {"bet": "X", "stake": "huge"}):
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
        self.new({"bet": "Alpha", "owner": "Sam", "cycle_start": "2026-11-02", "cycle_end": "2026-12-11"})
        self.cli("kpi", "Alpha", "Repeat tickets", "--baseline", "40", "--target", "25", "--read-by", "2026-12-18")

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
        for bad in ("status=on-track", "shipped=soon", "outcome=great", "area=hobby", "decision=fine",
                    "odds=likely", "odds=101", "stake=huge"):
            self.assertNotEqual(self.cli("set", "Alpha", bad, ok=False).returncode, 0, bad)

    def test_set_odds_and_decision(self):
        out = json.loads(self.cli("set", "Alpha", "odds=70%", "wrong_if=Tickets stay above 35",
                                  "decision=Good", "stake=LARGE", "stake_note=A quarter of the team").stdout)
        self.assertEqual(out, {"odds": "70", "wrong_if": "Tickets stay above 35", "decision": "good",
                               "stake": "large", "stake_note": "A quarter of the team"})
        text = self.read("bets/Alpha.md")
        self.assertIn("odds: 70\n", text)
        self.assertIn("decision: good\n", text)

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

    def test_score_groups_by_status_and_does_not_rewrite_it(self):
        self.cli("set", "Alpha", "status=paused")
        self.cli("set", "Beta", "status=done", "rating=lost")
        before = self.read("bets/Alpha.md")
        out = json.loads(self.cli("score", "--today", "2026-11-23").stdout)
        self.assertEqual(out["bets"], 5)
        self.assertEqual(out["notes_updated"], 0)
        self.assertEqual(out["status"]["paused"], 1)
        self.assertEqual(out["status"]["done"], 1)
        self.assertEqual(self.read("bets/Alpha.md"), before)
        self.assertIn("status: paused", self.read("bets/Alpha.md"))
        radar = self.read("bets/Bet Radar.md")
        self.assertIn("## Paused", radar)
        self.assertIn("| [[Alpha]] | Sam | — | — | — | — | — |", radar)
        self.assertIn("| [[Beta]] | Alex | — | — | — | lost | — |", radar)
        self.assertIn("## Results by stake", radar)
        self.assertIn("Rate the decision as it was made", radar)
        self.assertIn("## Decision against result", radar)
        self.assertIn("## Odds against results", radar)
        self.assertIn("```dataview", radar)
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

    def test_score_leaves_an_old_status_word_unset(self):
        with open(os.path.join(self.v, "bets/Alpha.md"), encoding="utf-8") as f:
            text = f.read()
        text = text.replace("status: in progress", "status: off-track")
        with open(os.path.join(self.v, "bets/Alpha.md"), "w", encoding="utf-8") as f:
            f.write(text)
        self.cli("score", "--today", "2026-11-23")
        self.assertIn("status: off-track", self.read("bets/Alpha.md"))
        radar = self.read("bets/Bet Radar.md")
        self.assertIn("## Not set", radar)
        self.assertIn("[[Alpha]]", radar.split("## Not set", 1)[1])

    def test_follow_ups_json(self):
        for n in ("Alpha", "Beta", "Delta", "Long run"):
            self.cli("set", n, "odds=50", "wrong_if=It does not move", "stake=small")
        self.cli("set", "Gamma", "status=done")
        fus = json.loads(self.cli("follow-ups", "--today", "2026-11-23").stdout)
        self.assertEqual([(f["owner"], f["kind"], f["bet"]) for f in fus],
                         [("Alex", "rating", "Gamma")])

    def test_radar_shows_decision_against_result_and_odds(self):
        self.cli("set", "Alpha", "status=done", "rating=lost", "decision=good", "odds=80", "stake=large")
        self.cli("set", "Beta", "status=done", "rating=won", "decision=bad", "odds=40")
        self.cli("set", "Gamma", "status=done", "rating=won", "decision=good", "odds=70")
        out = json.loads(self.cli("score", "--today", "2026-11-23").stdout)
        self.assertEqual(out["decision_vs_result"]["good, lost"], 1)
        self.assertEqual(out["decision_vs_result"]["bad, won"], 1)
        self.assertEqual(out["calibration"], {"bets": 3, "average_odds": 63, "won": 2, "win_rate": 67})
        radar = self.read("bets/Bet Radar.md")
        self.assertIn("| [[Alpha]] | Sam | 80% | large | good | lost | — |", radar)
        self.assertEqual(out["by_stake"], {"large": {"bets": 1, "won": 0, "win_rate": 0, "average_odds": 80}})
        self.assertIn("| Large | 1 | 0 | 0% | 80% |", radar)
        self.assertIn("Bad luck: 1<br>[[Alpha]]", radar)
        self.assertIn("Got lucky: 1<br>[[Beta]]", radar)
        self.assertIn("The odds and the results are within 10 points.", radar)
        self.assertIn('GROUP BY decision + ", " + rating', radar)


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
