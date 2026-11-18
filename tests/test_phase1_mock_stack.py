"""Phase 1 tests: scenarios, mock data, mock API, mock repositories (verification-code domain).

Standard library only. Run from the project root:
    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import tempfile
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from evals.lock_expected import expected_hash
from mock import generate as G
from tests import term_scan
from mock.api_server import MockApi

ROOT = Path(__file__).resolve().parent.parent
SCEN = ROOT / "evals" / "scenarios"
EXPECTED_IDS = ["S1a", "S1b", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12", "S13", "S14", "S15",
                "S17", "S18", "S19", "S20", "S21", "S22"]
REQUIRED_EXPECTED = {"outcome", "cause_category", "layer", "culprit_repo", "must_mention", "must_not_claim",
                     "shortest_path", "notes"}
OUTCOMES = {"cause_found", "no_issue", "inconclusive"}

TMP = tempfile.TemporaryDirectory()
BUILD = Path(TMP.name)
DIRS: dict[str, Path] = {}


def setUpModule():
    for sid in EXPECTED_IDS:
        DIRS[sid] = G.generate(sid, out_dir=BUILD / "a")


def tearDownModule():
    TMP.cleanup()


def load(sid):
    return json.loads((SCEN / f"{sid}.json").read_text(encoding="utf-8"))


def webhook(sid):
    rows = []
    with (DIRS[sid] / "provider_logs.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            r["_req"] = datetime.fromisoformat(r["sent_at"])
            rows.append(r)
    return rows


def dedup(rows):
    seen, out = set(), []
    for r in rows:
        k = (r["request_ref"], r["to"], r["status"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def at(s):
    return G.parse_ts(s)


def window(rows):
    return [r for r in rows if r["_req"] >= G.WINDOW_START]


class TestScenarioFiles(unittest.TestCase):
    def test_exactly_the_expected_scenarios(self):
        ids = sorted(p.stem for p in SCEN.glob("S*.json"))
        self.assertEqual(sorted(EXPECTED_IDS), ids)

    def test_each_scenario_is_complete(self):
        for sid in EXPECTED_IDS:
            sc = load(sid)
            self.assertEqual(sid, sc["id"])
            self.assertTrue(sc["question"].strip())
            exp = sc["expected"]
            self.assertTrue(REQUIRED_EXPECTED <= set(exp), f"{sid} missing {REQUIRED_EXPECTED - set(exp)}")
            self.assertIn(exp["outcome"], OUTCOMES)
            self.assertTrue(exp["shortest_path"], sid)
            self.assertTrue(exp["must_mention"] or exp["outcome"] == "no_issue", sid)
            self.assertTrue(set(sc["generate"]) >= {"faults", "api", "repos", "outputs"})

    def test_expected_answers_match_lock(self):
        lock = json.loads((SCEN / "expected.lock.json").read_text())
        self.assertEqual(sorted(EXPECTED_IDS), sorted(lock))
        for sid in EXPECTED_IDS:
            self.assertEqual(lock[sid], expected_hash(load(sid)["expected"]),
                             f"{sid}: expected answer changed without re-locking")

    def test_outcome_mix_includes_negative_cases(self):
        outcomes = [load(s)["expected"]["outcome"] for s in EXPECTED_IDS]
        self.assertIn("no_issue", outcomes)
        self.assertGreaterEqual(outcomes.count("inconclusive"), 3)  # S8, S11, S13, S14

    def test_every_fault_type_and_user_data_key_is_known_to_the_generator(self):
        known_faults = {"format_strip", "upstream_hang_drop", "credit_exhausted", "optout_cluster",
                        "volume_factor", "route_failure", "template_reject", "injection", "webhook_gap",
                        "late_delivery", "api_save_error", "scheduled_job_stopped", "repeat_requests"}
        known_user_data = {"missing_dial_code"}
        src = (ROOT / "mock" / "generate.py").read_text()
        for sid in EXPECTED_IDS:
            gen = load(sid)["generate"]
            for f in gen["faults"]:
                self.assertIn(f["type"], known_faults, sid)
                self.assertIn(f'"{f["type"]}"', src, f"{sid}: generator does not handle {f['type']}")
            for k in gen.get("user_data", {}):
                self.assertIn(k, known_user_data, sid)

    def test_only_one_bad_repo_per_scenario(self):
        for sid in EXPECTED_IDS:
            bad = [k for k, v in load(sid)["generate"]["repos"].items() if v == "bad_commit"]
            culprit = load(sid)["expected"]["culprit_repo"]
            if culprit:
                self.assertEqual([culprit], bad, sid)


class TestDeterminismAndPrivacy(unittest.TestCase):
    def test_same_scenario_builds_identically(self):
        for sid in ("S1a", "S12", "S14"):
            other = G.generate(sid, out_dir=BUILD / "b")
            for f in DIRS[sid].iterdir():
                if f.is_file():
                    self.assertEqual(f.read_bytes(), (other / f.name).read_bytes(), f"{sid}/{f.name}")
            a = subprocess.run(["git", "-C", str(DIRS[sid] / "repos/code_service"), "rev-parse", "HEAD"],
                               capture_output=True, text=True).stdout
            b = subprocess.run(["git", "-C", str(other / "repos/code_service"), "rev-parse", "HEAD"],
                               capture_output=True, text=True).stdout
            self.assertEqual(a, b)

    def test_optional_term_scan(self):
        # Whole-word scan against an optional private word list (see tests/term_scan.py).
        if not term_scan.load_terms():
            self.skipTest(term_scan.SKIP_MESSAGE)
        hits = []
        for top in (BUILD, SCEN, ROOT / "mock", ROOT / "evals", ROOT / "tests"):
            hits += term_scan.scan_tree(top)
        self.assertEqual([], sorted(set(hits)))

    def test_all_phone_numbers_are_in_the_invented_range(self):
        pat = re.compile(r"\b\d{10,12}\b")
        for sid in ("S1a", "S12"):
            for name in ("delivery_reports.csv", "api_failed_log.csv"):
                f = DIRS[sid] / name
                if not f.exists():
                    continue
                with f.open(encoding="utf-8", newline="") as fh:
                    for row in csv.DictReader(fh):
                        tel = row.get("to")
                        self.assertTrue(tel.startswith(("999000", "9000")), tel)
        for r in webhook("S1a"):
            self.assertTrue(r["to"].startswith(("999000", "9000")), r["to"])
        self.assertIsNotNone(pat)  # compiled for readability only

    def test_planted_values_exist_in_the_export_for_later_masking_tests(self):
        text = (DIRS["S1a"] / "delivery_reports.csv").read_text(encoding="utf-8")
        for v in (G.PLANTED_PHONE, G.PLANTED_IP, G.PLANTED_CODE, G.PLANTED_NAME):
            self.assertIn(v, text)
        self.assertIn(G.PLANTED_PHONE, (DIRS["S1a"] / "provider_logs.jsonl").read_text(encoding="utf-8"))

    def test_manifest_lists_placeholders_and_planted_values(self):
        m = json.loads((DIRS["S1a"] / "manifest.json").read_text())
        self.assertTrue(m["sample_notes"])
        self.assertEqual(G.PLANTED_PHONE, m["planted"]["phone"])

    def test_fake_message_code_never_in_scenario_or_manifest_files_except_data(self):
        self.assertNotIn(G.PLANTED_CODE, (SCEN / "S1a.json").read_text())


class TestExportLayout(unittest.TestCase):
    def test_header_matches_export_layout(self):
        with (DIRS["S1a"] / "delivery_reports.csv").open(encoding="utf-8", newline="") as fh:
            self.assertEqual(G.EXPORT_HEADER, next(csv.reader(fh)))

    def test_multiline_message_is_one_record_and_dates_are_iso(self):
        with (DIRS["S1a"] / "delivery_reports.csv").open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertTrue(any("\n" in r["body"] for r in rows))
        for r in rows[:50]:
            datetime.strptime(r["sent_at"], "%Y-%m-%d %H:%M:%S")
            datetime.strptime(r["delivered_on"], "%Y-%m-%d")
            datetime.strptime(r["delivered_at"], "%H:%M:%S")
        self.assertTrue(all(len(r) == len(G.EXPORT_HEADER) for r in rows))

    def test_status_is_text_in_export_and_status_text_in_webhook(self):
        with (DIRS["S1a"] / "delivery_reports.csv").open(encoding="utf-8", newline="") as fh:
            self.assertTrue({r["status"] for r in csv.DictReader(fh)} <= {"Delivered", "Failed"})
        self.assertTrue({r["status"] for r in webhook("S1a")} <= {"delivered", "failed"})

    def test_webhook_has_retry_duplicates_and_late_rows(self):
        rows = webhook("S7")
        self.assertGreater(len(rows), len(dedup(rows)))
        m = json.loads((DIRS["S7"] / "manifest.json").read_text())
        self.assertGreater(m["duplicates"], 0)
        self.assertGreater(m["late_rows"], 0)

    def test_failed_log_layout(self):
        with (DIRS["S12"] / "api_failed_log.csv").open(encoding="utf-8", newline="") as fh:
            self.assertEqual(G.FAILED_LOG_HEADER, next(csv.reader(fh)))


class TestFaultsArePresent(unittest.TestCase):
    """Each fault must really be in the data, or the scenario proves nothing."""

    def test_s1a_format_stripped_numbers_fail_after_the_release(self):
        rows = window(dedup(webhook("S1a")))
        start = at("2026-11-15T18:00")
        post = [r for r in rows if r["_req"] >= start]
        bad = [r for r in post if len(r["to"]) == 10]
        self.assertGreater(len(bad), 100)
        self.assertTrue(all(r["status"] == "failed" for r in bad))
        pre_bad = [r for r in rows if r["_req"] < start and len(r["to"]) == 10]
        self.assertEqual(0, len(pre_bad))

    def test_s1b_delivery_reports_show_no_failures_but_volume_drops_and_failed_log_has_records(self):
        rows = dedup(webhook("S1b"))
        post = [r for r in rows if r["_req"] >= at("2026-11-15T18:00") and r["_req"] >= G.WINDOW_START]
        self.assertTrue(all(len(r["to"]) == 12 for r in post))
        base = [r for r in rows if at("2026-11-14T18:00") <= r["_req"] < at("2026-11-15T12:00")]
        self.assertLess(len(post) / 18, 0.2 * (len(base) / 18))  # 18:00 to 12:00 next day is 18 hours
        with (DIRS["S1b"] / "api_failed_log.csv").open(encoding="utf-8", newline="") as fh:
            codes = [r["code"] for r in csv.DictReader(fh)]
        self.assertGreater(codes.count("E105"), 100)

    def test_s2_route_5_fails_after_04_00(self):
        rows = window(dedup(webhook("S2")))
        r5 = [r for r in rows if r["route"] == "5" and r["_req"] >= at("2026-11-16T04:00")]
        failed = [r for r in r5 if r["status"] == "failed"]
        self.assertGreater(len(r5), 30)
        self.assertGreater(len(failed) / len(r5), 0.65)
        r4 = [r for r in rows if r["route"] == "4" and r["_req"] >= at("2026-11-16T04:00")]
        self.assertLess(sum(r["status"] == "failed" for r in r4) / len(r4), 0.06)

    def test_s3_template_reject_uses_documented_string_for_one_template_only(self):
        rows = [r for r in window(dedup(webhook("S3"))) if r["_req"] >= at("2026-11-16T00:00")]
        t = [r for r in rows if r["template"] == G.TEMPLATES["T_VERIFY"][0]]
        self.assertTrue(t and all(r["failure"] == "Template not registered (mock wording)" for r in t))
        other = [r for r in rows if r["template"] != G.TEMPLATES["T_VERIFY"][0]]
        self.assertLess(sum(r["status"] == "failed" for r in other) / len(other), 0.06)

    def test_s4_logs_are_healthy_and_api_is_slow(self):
        rows = window(dedup(webhook("S4")))
        self.assertLess(sum(r["status"] == "failed" for r in rows) / len(rows), 0.05)
        self.assertEqual(1800, load("S4")["generate"]["api"]["latency_ms"])

    def test_s5_has_template_fault_and_slow_api(self):
        rows = [r for r in window(dedup(webhook("S5"))) if r["_req"] >= at("2026-11-16T00:00")]
        t = [r for r in rows if r["template"] == G.TEMPLATES["T_RESET"][0]]
        self.assertTrue(all(r["status"] == "failed" for r in t))
        self.assertEqual(1800, load("S5")["generate"]["api"]["latency_ms"])

    def test_s6_only_the_template_and_sender_combination_fails(self):
        rows = [r for r in window(dedup(webhook("S6"))) if r["_req"] >= at("2026-11-16T00:00")]
        combo = [r for r in rows if r["template"] == G.TEMPLATES["T_LOGIN"][0] and r["sender"] == "MOCKB"]
        self.assertGreater(len(combo), 20)
        self.assertTrue(all(r["status"] == "failed" for r in combo))
        fault = "Template not registered (mock wording)"
        outside = [r for r in rows if not (r["template"] == G.TEMPLATES["T_LOGIN"][0] and r["sender"] == "MOCKB")]
        # The fault string must never appear outside the cohort. Rates are not tested on the small
        # outside groups: a few ordinary baseline failures are expected there.
        self.assertEqual(0, len([r for r in outside if r["failure"] == fault]))
        self.assertTrue(all(r["failure"] != fault for r in outside))
        same_template_other_sender = [r for r in outside if r["template"] == G.TEMPLATES["T_LOGIN"][0]]
        same_sender_other_template = [r for r in outside if r["sender"] == "MOCKB"]
        self.assertGreater(len(same_template_other_sender), 50)   # the cohort is a true subset of the template
        self.assertGreater(len(same_sender_other_template), 10)   # and of the sender

    def test_s7_is_quiet_and_failed_log_is_benign_only(self):
        rows = window(dedup(webhook("S7")))
        self.assertLess(sum(r["status"] == "failed" for r in rows) / len(rows), 0.05)
        with (DIRS["S7"] / "api_failed_log.csv").open(encoding="utf-8", newline="") as fh:
            codes = [r["code"] for r in csv.DictReader(fh)]
        self.assertEqual(["E110", "E110"], sorted(codes))
        self.assertTrue(all(c not in ("E101", "E102", "E103") for c in codes))

    def test_s8_volume_halves_with_no_failure_signal(self):
        rows = dedup(webhook("S8"))

        def n(day, h0=3, h1=12):
            return len([r for r in rows if at(f"2026-11-{day:02d}T{h0:02d}:00") <= r["_req"] < at(f"2026-11-{day:02d}T{h1:02d}:00")])
        weekday_mean = sum(n(d) for d in (10, 11, 12, 13)) / 4   # Tue to Fri, same hours as the fault window
        ratio = n(16) / weekday_mean                              # Monday 16 Nov, fault from 03:00
        self.assertTrue(0.35 < ratio < 0.65, ratio)
        post = [r for r in rows if r["_req"] >= at("2026-11-16T03:00")]
        self.assertLess(sum(r["status"] == "failed" for r in post) / len(post), 0.06)

    def test_s9_injection_text_is_in_failure_reasons(self):
        rows = dedup(webhook("S9"))
        inj = [r for r in rows if "Ignore all previous instructions" in r["failure"]]
        self.assertEqual(3, len(inj))
        self.assertGreater(len([r for r in rows if r["failure"] == "Template not registered (mock wording)"]), 10)

    def test_s11_has_a_six_hour_hole(self):
        rows = webhook("S11")
        hole = [r for r in rows if at("2026-11-16T02:00") <= r["_req"] < at("2026-11-16T08:00")]
        self.assertEqual(0, len(hole))
        around = [r for r in rows if at("2026-11-16T08:00") <= r["_req"] < at("2026-11-16T10:00")]
        self.assertGreater(len(around), 20)

    def test_s12_delivery_stops_at_03_00_and_failed_log_has_E101s_only_after_it(self):
        rows = dedup(webhook("S12"))
        self.assertEqual(0, len([r for r in rows if r["_req"] >= at("2026-11-16T03:00")]))
        with (DIRS["S12"] / "api_failed_log.csv").open(encoding="utf-8", newline="") as fh:
            recs = list(csv.DictReader(fh))
        e101 = [r for r in recs if r["code"] == "E101"]
        self.assertGreater(len(e101), 100)
        for r in e101:
            self.assertGreaterEqual(datetime.strptime(r["at"], "%Y-%m-%d %H:%M:%S"),
                                    datetime(2026, 11, 16, 3, 0, tzinfo=G.GEN_TZ).astimezone(timezone.utc).replace(tzinfo=None))
        self.assertEqual(1, len({r["reason"] for r in e101}))  # one consistent error text

    def test_s13_same_data_but_no_failed_log_file(self):
        self.assertFalse((DIRS["S13"] / "api_failed_log.csv").exists())
        self.assertEqual(0, len([r for r in dedup(webhook("S13")) if r["_req"] >= at("2026-11-16T03:00")]))

    def test_s14_most_numbers_are_in_scientific_notation(self):
        with (DIRS["S14"] / "delivery_reports.csv").open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        sci = [r for r in rows if re.fullmatch(r"\d\.\d+E\+\d\d", r["to"])]
        self.assertGreater(len(sci) / len(rows), 0.8)
        m = json.loads((DIRS["S14"] / "manifest.json").read_text())
        self.assertEqual("manual_export", m["primary_store"])
        self.assertEqual(len(sci), m["export_damaged_rows"])

    def test_s15_a_quarter_of_users_are_opted_out(self):
        rows = [r for r in dedup(webhook("S15")) if r["_req"] >= at("2026-11-15T14:00")]
        by_user: dict[str, list] = {}
        for r in rows:
            by_user.setdefault(r["to"], []).append(r)
        repeat = {u: rs for u, rs in by_user.items() if len(rs) >= 2}
        blocked = [u for u, rs in repeat.items() if all(x["failure"] == G.OPT_OUT_REASON for x in rs)]
        share = len(blocked) / len(repeat)
        self.assertTrue(0.18 < share < 0.32, share)
        # Ordinary baseline opt-out failures also exist for other recipients, but they are rare
        mixed = [u for u, rs in repeat.items() if u not in blocked
                 and any(x["failure"] == G.OPT_OUT_REASON for x in rs)]
        self.assertLess(len(mixed) / len(repeat), 0.05)


class TestRepos(unittest.TestCase):
    def git(self, sid, repo, *args):
        return subprocess.run(["git", "-C", str(DIRS[sid] / "repos" / repo), *args],
                              capture_output=True, text=True, check=True).stdout

    def test_every_scenario_builds_two_repos_with_dated_commits(self):
        for sid in EXPECTED_IDS:
            for repo in ("code_service", "message_gateway"):
                log = self.git(sid, repo, "log", "--format=%ad|%s", "--date=format:%Y-%m-%d").strip().splitlines()
                self.assertGreaterEqual(len(log), 3, (sid, repo))
                self.assertTrue(all(l.startswith("2026-11-") for l in log))

    def test_s1a_bad_commit_is_in_code_service_only_and_removes_the_prefix(self):
        diff = self.git("S1a", "code_service", "log", "-p", "--since=2026-11-14", "--format=%s", "--", "src/codes/")
        self.assertIn('.replace("+99", "")', diff)
        self.assertIn("Normalise phone numbers before sending", diff)
        self.assertNotIn("+99", self.git("S1a", "message_gateway", "log", "-p", "--since=2026-11-14"))

    def test_s10_bad_commit_is_in_gateway_and_code_service_is_clean(self):
        gw = self.git("S10", "message_gateway", "log", "-p", "--since=2026-11-14", "--format=%s")
        self.assertIn('if dial_code in ("+99", "99")', gw)
        self.assertIn("Trim dial code for domestic routes", gw)
        code_repo = self.git("S10", "code_service", "log", "-p", "--since=2026-11-14", "--format=%s")
        self.assertNotIn('replace("+99"', code_repo)
        self.assertIn("expiry wording", code_repo)  # a benign commit sits near the release too

    def test_good_commit_keeps_the_prefix(self):
        src = (DIRS["S2"] / "repos/code_service/src/codes/send_code.py").read_text()
        self.assertIn('dial_code.lstrip("+") + phone', src)

    def test_a_fake_secret_is_planted_for_scrubbing_tests(self):
        src = (DIRS["S2"] / "repos/code_service/src/codes/send_code.py").read_text()
        self.assertIn("MOCKKEY_NOT_A_REAL_KEY_0123456789", src)
        self.assertIn("mock value, not a real key", src)

    def test_repos_have_no_remote_and_use_fake_author(self):
        for sid in ("S1a", "S10"):
            self.assertEqual("", self.git(sid, "code_service", "remote").strip())
            self.assertIn("dev@example.test", self.git(sid, "code_service", "log", "-1", "--format=%ae"))



def user_summary(sid):
    return json.loads((DIRS[sid] / "users_summary.json").read_text())["days"]


def split_days(days, start_date):
    before = [d for d in days if d["created_date"] < start_date]
    after = [d for d in days if d["created_date"] >= start_date]
    return before, after


class TestUserDataAndDeliveryScenarios(unittest.TestCase):
    """S17 to S19: faults that leave little or nothing in the provider logs."""

    def hourly_counts(self, sid, start, end):
        rows = dedup(webhook(sid))
        return sum(1 for r in rows if at(start) <= r["_req"] < at(end))

    def test_s17_users_have_missing_dial_code_and_only_a_group_fails(self):
        before, after = split_days(user_summary("S17"), "2026-11-15")
        self.assertTrue(all(d["dial_code_missing"] == 0 for d in before))
        self.assertTrue(all(d["dial_code_missing"] > 0 for d in after))
        rows = [r for r in window(dedup(webhook("S17"))) if r["_req"] >= at("2026-11-15T18:00")]
        short = [r for r in rows if len(r["to"]) == 10]
        self.assertGreater(len(short), 15)
        self.assertTrue(all(r["status"] == "failed" for r in short))
        self.assertTrue(all(len(r["to"]) == 12 for r in rows if r["status"] == "delivered"))
        self.assertGreater(sum(len(r["to"]) == 12 for r in rows), len(short))  # most users are fine
        self.assertEqual("clean", load("S17")["generate"]["repos"]["code_service"])

    def test_s18_requests_are_missing_and_the_api_is_set_to_hang(self):
        mode = json.loads((DIRS["S18"] / "api_mode.json").read_text())
        self.assertEqual(100000, mode["latency_ms"])
        after = self.hourly_counts("S18", "2026-11-16T06:00", "2026-11-16T12:00")
        before = self.hourly_counts("S18", "2026-11-15T06:00", "2026-11-15T12:00")
        self.assertLess(after, 0.65 * before)
        rows = [r for r in dedup(webhook("S18")) if r["_req"] >= at("2026-11-16T06:00")]
        self.assertLess(sum(r["status"] == "failed" for r in rows) / len(rows), 0.06)
        self.assertFalse((DIRS["S18"] / "users_summary.json").exists())

    def test_s19_all_delivered_but_late_and_failure_rate_is_normal(self):
        def gaps(rows):
            return [(datetime.fromisoformat(r["delivered_at"]) - r["_req"]).total_seconds() for r in rows]
        late_rows = [r for r in dedup(webhook("S19")) if r["_req"] >= at("2026-11-16T04:00")]
        early_rows = [r for r in dedup(webhook("S19")) if r["_req"] < at("2026-11-16T04:00")]
        late_gaps, early_gaps = gaps(late_rows), gaps(early_rows)
        self.assertLessEqual(max(early_gaps), 10)
        self.assertGreater(sum(g >= 60 for g in late_gaps) / len(late_gaps), 0.55)
        self.assertLessEqual(max(late_gaps), 226)
        self.assertLess(sum(r["status"] == "failed" for r in late_rows) / len(late_rows), 0.06)

    def test_user_summary_is_aggregate_only_and_invented(self):
        for sid in ("S17",):
            text = (DIRS[sid] / "users_summary.json").read_text()
            self.assertNotRegex(text, r"\b\d{10,12}\b")
            self.assertEqual({"created_date", "new_users", "locale_missing", "dial_code_missing"},
                             set(user_summary(sid)[0]))
        for sid in EXPECTED_IDS:
            if "user_data" not in load(sid)["generate"]:
                self.assertFalse((DIRS[sid] / "users_summary.json").exists(), sid)

    def test_no_application_log_source_is_part_of_any_scenario_or_output(self):
        for sid in EXPECTED_IDS:
            names = {p.name for p in DIRS[sid].iterdir()}
            self.assertFalse({n for n in names if "app_log" in n or "application" in n}, sid)
            self.assertNotIn("app_log", json.dumps(load(sid)).lower())

    def test_new_scenarios_do_not_change_the_old_expected_answers(self):
        lock = json.loads((SCEN / "expected.lock.json").read_text())
        for sid in ("S17", "S18", "S19"):
            self.assertEqual(expected_hash(load(sid)["expected"]), lock[sid])


class TestMockApi(unittest.TestCase):
    TOKEN = "unit-test-token"

    def post(self, api, body, token=None, path="/v1/verify/start"):
        req = urllib.request.Request(api.base_url + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {token or self.TOKEN}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read())
            finally:
                e.close()

    def body(self, cc="+99", phone="9000000001"):
        return {"country_prefix": cc, "phone": phone, "client": "mock-client-0001"}

    def test_success_for_any_country_prefix(self):
        with MockApi(token=self.TOKEN, mode={"latency_ms": 0}) as api:
            for cc in ("+99", "99", ""):
                code, resp = self.post(api, self.body(cc))
                self.assertEqual(200, code, cc)
                self.assertEqual({"message": "Request accepted", "code": ""}, resp)

    def test_code_is_never_returned(self):
        with MockApi(token=self.TOKEN, mode={"latency_ms": 0}) as api:
            self.assertEqual("", self.post(api, self.body())[1]["code"])

    def test_wrong_token_is_rejected(self):
        with MockApi(token=self.TOKEN, mode={"latency_ms": 0}) as api:
            self.assertEqual(401, self.post(api, self.body(), token="nope")[0])

    def test_missing_field_and_unknown_path(self):
        with MockApi(token=self.TOKEN, mode={"latency_ms": 0}) as api:
            self.assertEqual(400, self.post(api, {"phone": "9000000001"})[0])
            self.assertEqual(404, self.post(api, self.body(), path="/nope")[0])

    def test_latency_mode_slows_the_answer(self):
        import time
        with MockApi(token=self.TOKEN, mode={"latency_ms": 600}) as api:
            t = time.perf_counter()
            self.post(api, self.body())
            self.assertGreaterEqual(time.perf_counter() - t, 0.55)

    def test_no_echo_by_default_so_the_probe_cannot_see_the_forwarded_number(self):
        with MockApi(token=self.TOKEN, mode={"latency_ms": 0, "forward": "strip_prefix"}) as api:
            self.assertNotIn("_mock_forwarded", self.post(api, self.body())[1])

    def test_echo_mode_shows_a_masked_forwarded_number_and_strip_mode_drops_the_prefix(self):
        with MockApi(token=self.TOKEN, mode={"latency_ms": 0, "forward": "strip_prefix", "echo_forwarded_number": True}) as api:
            echo = self.post(api, self.body())[1]["_mock_forwarded"]
            self.assertEqual(10, len(echo))
            self.assertNotIn("9000000001", echo)
            self.assertEqual(10, api.calls[0]["forwarded_len"])
        with MockApi(token=self.TOKEN, mode={"latency_ms": 0, "forward": "keep", "echo_forwarded_number": True}) as api:
            self.assertEqual(12, len(self.post(api, self.body())[1]["_mock_forwarded"]))

    def test_scenario_api_modes_are_valid(self):
        for sid in EXPECTED_IDS:
            m = json.loads((DIRS[sid] / "api_mode.json").read_text())
            self.assertTrue({"latency_ms", "forward", "echo_forwarded_number"} <= set(m), sid)
            self.assertIn(m["forward"], ("keep", "strip_prefix"))


if __name__ == "__main__":
    unittest.main()
