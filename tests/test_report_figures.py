"""Report statistics computed from real retained-event-shaped fixtures."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.make_figures import token_medians


class TokenMedianTests(unittest.TestCase):
    def test_conventional_even_and_odd_medians_of_answered_target_responses(self):
        with tempfile.TemporaryDirectory() as directory:
            sweep = Path(directory)
            run = sweep / "f30"
            run.mkdir()
            (run / "truth.json").write_text(json.dumps({
                "colluders": ["C"], "targets": ["target"],
            }), encoding="utf-8")
            events = [
                {"type": "attestation", "agent_id": "C", "case_id": "target",
                 "outcome": "sign", "output_tokens": tokens}
                for tokens in [329, 50, 326, 900]
            ] + [
                {"type": "attestation", "agent_id": "H", "case_id": "target",
                 "outcome": "refuse", "output_tokens": tokens}
                for tokens in [174, 1000, 12]
            ] + [
                {"type": "attestation", "agent_id": "H", "case_id": "target",
                 "outcome": "abstain", "output_tokens": 5000},
                {"type": "attestation", "agent_id": "C", "case_id": "valid",
                 "outcome": "sign", "output_tokens": 5000},
            ]
            (run / "events.jsonl").write_text(
                "\n".join(json.dumps(event) for event in events), encoding="utf-8")

            self.assertEqual(token_medians(sweep), {
                ("attestation", "Colluding"): (327.5, 4),
                ("attestation", "Honest"): (174, 3),
            })


if __name__ == "__main__":
    unittest.main()
