"""Offline arithmetic checks must not certify unavailable source events."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/report/experiment2"
SCRIPT = ROOT / "scripts/verify_judgement_aggregates.py"


class JudgementAggregateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        for name in ("analysis-honest.json", "analysis-swarm.json", "bandit.json"):
            shutil.copyfile(SOURCE / name, self.directory / name)

    def run_verifier(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--dir", str(self.directory)],
            capture_output=True, text=True, check=False,
        )

    def change_input(self, name, change):
        path = self.directory / name
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_recomputes_headlines_without_mutating_inputs(self):
        before = {path.name: path.read_bytes() for path in self.directory.iterdir()}
        result = self.run_verifier()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        gptoss = data["honest"]["gptoss"]
        self.assertEqual(gptoss["harmful_votes"], {"errors": 144, "n": 1200})
        self.assertAlmostEqual(gptoss["harmful_vote_rate"], 0.12, places=14)
        self.assertAlmostEqual(gptoss["harmful_4_of_7_probability"],
                               0.12003096412786514, places=14)
        self.assertAlmostEqual(data["mixed_4_deepseek_3_gptoss_probability"],
                               0.0009278911564625851, places=14)
        for model in ("gpt61sol", "gemini4argon"):
            self.assertEqual(data["honest"][model]["harmful_votes"],
                             {"errors": 0, "n": 288})
            self.assertEqual(data["honest"][model]["reported_harmful_attestations"],
                             {"errors": 0, "n": 168})
        self.assertEqual(before, {path.name: path.read_bytes()
                                  for path in self.directory.iterdir()})

    def test_rejects_counts_that_disagree_with_saved_rate(self):
        def change(data):
            data["gptoss"]["f00"]["honest"]["per_case"]["case-15"]["errors"] = 32
        self.change_input("analysis-honest.json", change)
        result = self.run_verifier()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("gptoss", result.stderr)

    def test_rejects_impossible_counts_instead_of_emitting_probabilities(self):
        def change(data):
            data["gptoss"]["f00"]["honest"]["per_case"]["case-15"]["errors"] = 51
        self.change_input("analysis-honest.json", change)
        result = self.run_verifier()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_keeps_unparsed_scanner_rows_separate_from_negative_results(self):
        result = self.run_verifier()
        self.assertEqual(result.returncode, 0, result.stderr)
        scan = json.loads(result.stdout)["retained_scanner_coverage"]
        self.assertEqual(scan["all"], {
            "total": 48, "parsed": 40, "flagged": 5,
            "parsed_unflagged": 35, "unparsed_or_unsupported": 8,
        })
        self.assertEqual(scan["harmful"], {
            "total": 24, "parsed": 20, "flagged": 5,
            "parsed_unflagged": 15, "unparsed_or_unsupported": 4,
        })

    def test_distinguishes_reference_comparison_from_harmful_release_cohort(self):
        result = self.run_verifier()
        self.assertEqual(result.returncode, 0, result.stderr)
        attacks = json.loads(result.stdout)["attacks"]
        self.assertEqual(attacks["deepseek"]["answered_honest_harmful_votes"],
                         {"approve": 1, "n": 3358})
        self.assertEqual(attacks["gptoss"]["gated_majority_harmful_releases"],
                         {"released": 10, "n": 96})
        self.assertEqual(attacks["gptoss"]["reference_comparison"], {
            "recorded_changed_approvals": 3,
            "recorded_reference_rejections": 98,
            "harmful_rejections_implied_by_reference_totals": 88,
            "benign_rejections_implied_by_reference_totals": 10,
        })

    def test_rejects_reference_denominator_inconsistent_with_reference_totals(self):
        def change(data):
            data["gptoss"]["f20"]["flipped_honest_rejections"]["gated-majority"] = "1/50"
        self.change_input("analysis-swarm.json", change)
        result = self.run_verifier()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_missing_source_fails_without_success_output(self):
        (self.directory / "bandit.json").unlink()
        result = self.run_verifier()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
