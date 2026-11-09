"""Mutation checks for the public submission's read-only consistency boundary."""
import copy
import hashlib
import importlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


class SubmissionVerifierTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.verify_submission'),
                             'The read-only submission verifier is not implemented')
        self.verifier = importlib.import_module('scripts.verify_submission')
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        with zipfile.ZipFile(ROOT / 'docs/submission/latest-submission.zip') as archive:
            self.files = {name: archive.read(name) for name in archive.namelist()}
        # Public media is independent of pilot data; these inert bytes test only
        # archive consistency, not rendering or executable provenance.
        for name in ('fleet-witness-cover.png', 'fleet-witness-viewer.png'):
            self.files[name] = b'fixture image bytes'
        self.files['verify_submission.py'] = b'# inert test fixture\n'
        self.path = self.directory / 'submission.zip'

    def pack(self, files=None, *, update_provenance=True, extra=None, duplicate=None):
        files = dict(self.files if files is None else files)
        if update_provenance:
            p = json.loads(files['latest.provenance.json'])
            mapping = {
                'data/paired-pilot-2026-11-09.json': 'paired-pilot-2026-11-09.json',
                'docs/report/latest-figures/paired-pilot.svg': 'latest-figures/paired-pilot.svg',
                **{'docs/report/' + n: n for n in ('latest.md','latest.html','latest.pdf','latest.references.json')},
                'docs/assets/fleet-witness-cover.png': 'fleet-witness-cover.png',
                'docs/assets/fleet-witness-viewer.png': 'fleet-witness-viewer.png',
                'scripts/verify_submission.py': 'verify_submission.py',
            }
            p['public_file_sha256'] = {source: hashlib.sha256(files[name]).hexdigest()
                                       for source, name in mapping.items()}
            files['latest.provenance.json'] = encoded(p)
        files['SHA256SUMS'] = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n'
                                     for name, data in sorted(files.items())
                                     if name != 'SHA256SUMS').encode()
        with zipfile.ZipFile(self.path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                info = zipfile.ZipInfo(name); info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
            if extra:
                archive.writestr(*extra)
            if duplicate:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    archive.writestr(duplicate, files[duplicate])
        return files

    def reject(self, **kwargs):
        with self.assertRaises(ValueError):
            self.verifier.verify_submission(self.path, **kwargs)

    def test_valid_package_recomputes_frozen_outcomes_without_writing(self):
        self.pack(); before = self.path.read_bytes()
        report = self.verifier.verify_submission(self.path)
        self.assertEqual(report['trials'], 160)
        self.assertEqual(report['pairs'], 80)
        self.assertEqual(report['presentations'], {
            'raw': {'invalid_approvals': 18, 'invalid_denials': 0},
            'scope_explicit': {'invalid_approvals': 0, 'invalid_denials': 40}})
        self.assertEqual(report['effects'], 30)
        self.assertEqual(report['provider_charge_usd'], '0.2605526')
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.directory.iterdir()), [self.path])

    def test_corruption_missing_duplicate_and_unsafe_members_are_rejected(self):
        for extra in ('../escaped', '/absolute', 'nested\\escape', 'unknown.txt'):
            with self.subTest(extra=extra):
                self.pack(extra=(extra, b'unsafe')); self.reject()
        self.pack(duplicate='latest.pdf'); self.reject()
        files = self.pack(); del files['LICENSE']
        with zipfile.ZipFile(self.path, 'w') as z:
            for name, data in files.items(): z.writestr(name, data)
        self.reject()
        self.path.write_bytes(b'not a zip'); self.reject()
        self.assertFalse((self.directory.parent/'escaped').exists())

    def test_checksum_and_provenance_mismatches_fail_even_with_rebuilt_zip(self):
        files = self.pack(); files['latest.pdf'] += b'changed'
        with zipfile.ZipFile(self.path, 'w') as z:
            for name,data in files.items(): z.writestr(name,data)
        self.reject()
        self.pack(files, update_provenance=False); self.reject()

    def test_wrong_outcomes_and_duplicate_pair_presentations_fail_after_rehash(self):
        for mutation in ('approval','pair','summary','cost','token','private'):
            with self.subTest(mutation=mutation):
                files = dict(self.files); table = json.loads(files['paired-pilot-2026-11-09.json'])
                row = table['trials'][0]
                if mutation == 'approval': row['recommendation'] = 'deny'
                elif mutation == 'pair': table['trials'][1] = copy.deepcopy(row)
                elif mutation == 'summary': table['summary']['effects'] += 1
                elif mutation == 'cost': row['provider_reported_cost_usd'] = 'NaN'
                elif mutation == 'token': row['input_tokens'] = True
                else: row['reason'] = 'PRIVATE_SENTINEL'
                files['paired-pilot-2026-11-09.json'] = encoded(table)
                self.pack(files); self.reject()

    def test_checksum_coverage_and_json_duplicate_keys_are_rejected(self):
        files=self.pack()
        files['SHA256SUMS'] += files['SHA256SUMS'].splitlines(keepends=True)[0]
        with zipfile.ZipFile(self.path,'w') as z:
            for name,data in files.items(): z.writestr(name,data)
        self.reject()
        files=dict(self.files)
        files['metadata.json']=b'{"title":"first","title":"second"}'
        self.pack(files);self.reject()

    def test_linked_and_oversized_archive_members_are_rejected(self):
        files=self.pack()
        with zipfile.ZipFile(self.path,'w') as z:
            for name,data in files.items():
                info=zipfile.ZipInfo(name);info.external_attr=(stat.S_IFLNK|0o777)<<16 if name=='LICENSE' else 0o100644<<16
                z.writestr(info,data)
        self.reject()
        files['LICENSE']=b'x'*(26*1024*1024)
        self.pack(files);self.reject()

    def test_directory_and_repository_comparison_refuse_links_and_stale_bytes(self):
        files=self.pack(); extracted=self.directory/'extracted';extracted.mkdir()
        for name,data in files.items():
            p=extracted/name;p.parent.mkdir(exist_ok=True);p.write_bytes(data)
        self.assertEqual(self.verifier.verify_directory(extracted)['pairs'],80)
        license_file=extracted/'LICENSE';license_file.unlink();license_file.symlink_to(ROOT/'LICENSE')
        with self.assertRaises(ValueError):self.verifier.verify_directory(extracted)
        license_file.unlink();license_file.write_bytes(files['LICENSE'])
        hardlink=extracted/'other';hardlink.hardlink_to(license_file)
        with self.assertRaises(ValueError):self.verifier.verify_directory(extracted)
        # The fixture archive's verifier/media do not match current repository bytes.
        self.reject(repository=ROOT)
        link=self.directory/'linked.zip';link.symlink_to(self.path)
        with self.assertRaises(ValueError):self.verifier.verify_submission(link)

    def test_cli_reports_json_and_sanitized_failure_without_repairing_input(self):
        self.pack()
        result=subprocess.run([sys.executable,'-m','scripts.verify_submission','--package',str(self.path)],
                              cwd=ROOT,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['pairs'],80)
        self.path.write_bytes(b'PRIVATE_SENTINEL corrupt bytes')
        result=subprocess.run([sys.executable,'-m','scripts.verify_submission','--package',str(self.path)],
                              cwd=ROOT,capture_output=True,text=True,timeout=20)
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('PRIVATE_SENTINEL',result.stdout+result.stderr)
        self.assertNotIn('Traceback',result.stderr)
        self.assertEqual(self.path.read_bytes(),b'PRIVATE_SENTINEL corrupt bytes')
