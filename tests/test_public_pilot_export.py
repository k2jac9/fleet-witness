"""Public evidence exports must not recursively copy private provider records."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_controlled_pilot import PilotCase
from fleet_witness import controlled_pilot, pilot_store
from fleet_witness.swarm import providers


class PublicPilotExportTests(PilotCase):
    def report(self):
        with patch.object(providers, '_post', return_value=self.reply()):
            return controlled_pilot.collect(self.client(), self.root / 'export-source')

    def test_private_nested_material_is_never_copied_and_counts_survive(self):
        from scripts.export_public_pilot import public_export
        report = self.report()
        sentinel = 'PRIVATE-TRANSPORT-KEY-DO-NOT-PUBLISH'
        report['private_extra'] = {'key': sentinel}
        for call in report['calls']:
            call['private_extra'] = sentinel
            call['outcome']['private_extra'] = {'key': sentinel}
            call['ledger_attempt']['private_extra'] = sentinel
            call['ledger_attempt']['receipt']['private_extra'] = sentinel
            call['outcome']['attempts'][0]['private_extra'] = sentinel
            call['decision']['private_extra'] = sentinel
            for event in call['events']:
                event['private_extra'] = sentinel
        exported = public_export(report)
        encoded = json.dumps(exported)
        self.assertNotIn(sentinel, encoded)
        self.assertNotIn('synthetic-pilot-secret', encoded)
        for field in ('authorization', 'transport', 'provider_request_id', 'supervisor_input', 'text'):
            self.assertNotIn('"' + field + '"', encoded)
        self.assertEqual(len(exported['trials']), 160)
        self.assertEqual(len({c['pair_id'] for c in exported['trials']}), 80)
        self.assertEqual(sum(c['effects'] for c in exported['trials']), report['summary']['effects'])
        self.assertEqual(exported['summary'], pilot_store.summarize(report['calls'], None))

    def test_tampered_summary_and_incomplete_cohort_are_refused(self):
        from scripts.export_public_pilot import public_export
        report = self.report()
        tampered = copy.deepcopy(report)
        tampered['summary']['effects'] += 1
        with self.assertRaises(ValueError):
            public_export(tampered)
        incomplete = copy.deepcopy(report)
        incomplete['stop_reason'] = 'operator stop'
        incomplete['summary'] = pilot_store.summarize(incomplete['calls'], incomplete['stop_reason'])
        with self.assertRaises(ValueError):
            public_export(incomplete)


class PackageBoundaryTests(unittest.TestCase):
    def test_public_package_inputs_exclude_workstation_paths(self):
        from scripts.build_latest_submission import MEMBERS, ROOT, read_member
        for source in MEMBERS.values():
            if Path(source).suffix in {'.md', '.json', '.html', '.txt', '.svg'}:
                with self.subTest(source=source):
                    self.assertNotIn(b'/home/neo/', read_member(ROOT, source))

    def test_package_rejects_symlink_members_and_parent_traversal(self):
        from scripts.build_latest_submission import read_member
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'allowed').mkdir()
            (root / 'allowed' / 'paper.md').write_text('public')
            (root / 'secret').write_text('private')
            (root / 'link').symlink_to(root / 'secret')
            (root / 'directory-link').symlink_to(root / 'allowed', target_is_directory=True)
            self.assertEqual(read_member(root, 'allowed/paper.md'), b'public')
            for name in ('link', 'directory-link/paper.md', '../secret', str(root / 'secret')):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    read_member(root, name)


if __name__ == '__main__':
    unittest.main()
