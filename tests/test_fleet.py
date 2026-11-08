"""Fleet coordination checks use disposable, real Git repositories."""
import copy
import json
import os
import shlex
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'fleet.py'
ADR = 'docs/adr/0006-development-fleet.md'


class FleetTests(unittest.TestCase):
    def setUp(self):
        # Disposable fixtures must not inherit executable filters or Git routing
        # from the developer/runner; local filter-refusal fixtures stay active.
        self.git_env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        self.git_env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
                            GIT_CONFIG_NOSYSTEM='1')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.email', 'fleet-test@example.invalid')
        self.git('config', 'user.name', 'Fleet Test')
        (self.root / 'docs/adr').mkdir(parents=True)
        (self.root / ADR).write_text('# ADR-0006\n- Status: Accepted\n')
        (self.root / '.gitignore').write_text('.worktrees/\n.fleet/\n')
        self.manifest = {'version': 1, 'owner': 'k2jac9', 'default_budget_usd': 0,
                         'tasks': [self.task('alpha'), self.task('beta', ['alpha'])]}
        self.save()
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], text=True,
                              capture_output=True, check=True, env=self.git_env).stdout.strip()

    def task(self, task_id, depends_on=None):
        return {'id': task_id, 'title': task_id.title(), 'role': 'implementer',
                'status': 'todo', 'depends_on': depends_on or [],
                'owned_paths': ['work/' + task_id], 'adrs': [ADR],
                'acceptance': [[sys.executable, '-c',
                                'from pathlib import Path; Path("acceptance-ran").touch(); raise SystemExit(99)']],
                'brief': 'Report the commit, changed paths, commands/results, and limitations.'}

    def save(self):
        (self.root / 'fleet').mkdir(exist_ok=True)
        (self.root / 'fleet/tasks.json').write_text(json.dumps(self.manifest))

    def run_cli(self, *args, root=None):
        return subprocess.run([sys.executable, str(SCRIPT), '--root', str(root or self.root), *args],
                              text=True, capture_output=True, env=self.git_env)

    def rejected(self, *args, root=None):
        result = self.run_cli(*args, root=root)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('Error:', result.stderr)
        return result

    def test_validate_and_ordered_plan_are_read_only(self):
        before = self.git('status', '--porcelain')
        self.assertEqual(self.run_cli('validate').returncode, 0)
        result = self.run_cli('plan')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(result.stdout.index('alpha'), result.stdout.index('beta'))
        self.assertIn('ready', result.stdout)
        self.assertIn('blocked', result.stdout)
        self.assertEqual(before, self.git('status', '--porcelain'))
        self.assertFalse((self.root / '.worktrees').exists())

    def test_duplicate_ids_unknown_dependencies_and_cycles(self):
        original = copy.deepcopy(self.manifest)
        for case in ('duplicate', 'unknown', 'cycle', 'self'):
            with self.subTest(case=case):
                self.manifest = copy.deepcopy(original)
                if case == 'duplicate':
                    self.manifest['tasks'][1]['id'] = 'alpha'
                elif case == 'unknown':
                    self.manifest['tasks'][1]['depends_on'] = ['missing']
                elif case == 'cycle':
                    self.manifest['tasks'][0]['depends_on'] = ['beta']
                else:
                    self.manifest['tasks'][0]['depends_on'] = ['alpha']
                self.save()
                self.rejected('validate')

    def test_unsafe_ownership_paths(self):
        for path in ('/tmp/escape', '../escape', 'work/../escape', './work', 'a//b',
                     'a\\b', '.git/config', '.worktrees/alpha', 'work/*', '', 'a\x00b'):
            with self.subTest(path=path):
                self.manifest['tasks'][0]['owned_paths'] = [path]
                self.save()
                self.rejected('validate')

    def test_symlink_ownership_and_root_are_refused(self):
        (self.root / 'linked').symlink_to(self.root / 'docs', target_is_directory=True)
        self.manifest['tasks'][0]['owned_paths'] = ['linked/report.md']
        self.save()
        self.rejected('validate')
        alias = self.root.parent / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        self.rejected('prepare', 'alpha', root=alias)

    def test_ready_task_path_overlap_is_refused(self):
        self.manifest['tasks'][1]['depends_on'] = []
        for path in ('work/alpha', 'work', 'work/alpha/nested.md'):
            with self.subTest(path=path):
                self.manifest['tasks'][1]['owned_paths'] = [path]
                self.save()
                self.rejected('validate')

    def test_blocked_overlap_is_allowed_until_ready(self):
        self.manifest['tasks'][1]['owned_paths'] = ['work/alpha']
        self.save()
        self.assertEqual(self.run_cli('validate').returncode, 0)

    def test_invalid_adr_references(self):
        for reference in ('docs/adr/missing.md', '../outside.md', 'README.md'):
            with self.subTest(reference=reference):
                self.manifest['tasks'][0]['adrs'] = [reference]
                self.save()
                self.rejected('validate')
        self.manifest['tasks'][0]['adrs'] = [ADR]
        (self.root / ADR).write_text('# ADR\n- Status: Proposed\n')
        self.save()
        self.rejected('validate')

    def test_malformed_manifest_fails_closed(self):
        original = copy.deepcopy(self.manifest)
        for field, value in (('status', 'running'), ('id', '../x'), ('depends_on', 'alpha'),
                             ('acceptance', ['echo unsafe']), ('acceptance', [[]]),
                             ('owned_paths', []), ('adrs', []), ('role', '')):
            with self.subTest(field=field, value=value):
                self.manifest = copy.deepcopy(original)
                self.manifest['tasks'][0][field] = value
                self.save()
                self.rejected('validate')
        for field, value in (('version', True), ('owner', 'other'), ('default_budget_usd', 1),
                             ('tasks', {})):
            with self.subTest(field=field):
                self.manifest = copy.deepcopy(original)
                self.manifest[field] = value
                self.save()
                self.rejected('validate')
        (self.root / 'fleet/tasks.json').write_text('{"version": 1, "version": 1}')
        self.rejected('validate')

    def test_blocked_done_and_unknown_task_preparation_is_refused(self):
        self.rejected('prepare', 'beta')
        self.rejected('prepare', 'missing')
        self.manifest['tasks'][0]['status'] = 'done'
        self.save()
        self.git('add', '.')
        self.git('commit', '-qm', 'mark done')
        self.rejected('prepare', 'alpha')
        result = self.run_cli('plan')
        self.assertIn('beta: ready', result.stdout)
        self.assertFalse((self.root / '.worktrees').exists())

    def test_preparation_creates_worktree_branch_and_ignored_brief_only(self):
        result = self.run_cli('prepare', 'alpha')
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.root / '.worktrees/alpha'
        self.assertEqual(self.git('-C', str(target), 'branch', '--show-current'), 'fleet/alpha')
        brief = target / '.fleet/brief.md'
        self.assertTrue(brief.is_file())
        self.assertIn('alpha', brief.read_text())
        self.assertIn(ADR, brief.read_text())
        self.assertIn('99', brief.read_text())
        self.assertEqual(self.git('-C', str(target), 'status', '--porcelain'), '')
        self.assertEqual(self.git('-C', str(target), 'check-ignore', '.fleet/brief.md'), '.fleet/brief.md')
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertFalse((self.root / 'acceptance-ran').exists())
        self.assertFalse((target / 'acceptance-ran').exists())
        self.rejected('prepare', 'alpha')

    def test_dirty_tracked_files_are_refused_but_untracked_notes_are_allowed(self):
        (self.root / ADR).write_text('# dirty\n')
        self.rejected('prepare', 'alpha')
        self.git('checkout', '--', ADR)
        (self.root / 'local-note.txt').write_text('untracked')
        self.assertEqual(self.run_cli('prepare', 'alpha').returncode, 0)

    def test_existing_branch_directory_and_symlink_are_refused(self):
        self.git('branch', 'fleet/alpha')
        self.rejected('prepare', 'alpha')
        self.git('branch', '-D', 'fleet/alpha')
        parent = self.root / '.worktrees'
        parent.mkdir()
        target = parent / 'alpha'
        target.mkdir()
        self.rejected('prepare', 'alpha')
        target.rmdir()
        target.symlink_to(self.root / 'docs', target_is_directory=True)
        self.rejected('prepare', 'alpha')
        target.unlink()
        parent.rmdir()
        parent.symlink_to(self.root / 'docs', target_is_directory=True)
        self.rejected('prepare', 'alpha')
        self.assertNotIn('fleet/alpha', self.git('branch', '--list'))

    def assert_filter_refused_without_effects(self, kind, included=False):
        # Install attributes before enabling a real marker-producing executable.
        (self.root / '.gitattributes').write_text('filtered.txt filter=marker\n')
        payload = self.root / 'filtered.txt'
        payload.write_text('tracked payload\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'filter fixture')
        marker = self.root.parent / 'filter-ran'
        executable = self.root.parent / 'filter.py'
        executable.write_text(
            'from pathlib import Path\nimport sys\n'
            f'Path({str(marker)!r}).touch()\n'
            + ('raise SystemExit(1)\n' if kind == 'process' else
               'sys.stdout.buffer.write(sys.stdin.buffer.read())\n'))
        command = shlex.join([sys.executable, str(executable)])
        if included:
            config = self.root.parent / 'included-config'
            self.git('config', '--file', str(config), f'filter.marker.{kind}', command)
            include_key = ('includeIf.onbranch:fleet/**.path' if included == 'conditional'
                           else 'include.path')
            self.git('config', include_key, str(config))
        else:
            self.git('config', f'filter.marker.{kind}', command)
        if kind == 'clean':
            # Force status to inspect content, rather than relying on cached stat data.
            payload.write_text('changed payload\n')
        configuration_before = (self.root / '.git/config').read_bytes()
        registrations_before = self.git('worktree', 'list', '--porcelain')
        result = self.run_cli('prepare', 'alpha')
        self.assertFalse(marker.exists(), f'{kind} filter executed: {result.stderr}')
        self.assertFalse((self.root / '.worktrees').exists())
        self.assertEqual(self.git('branch', '--list', 'fleet/alpha'), '')
        self.assertEqual(self.git('worktree', 'list', '--porcelain'), registrations_before)
        self.assertEqual((self.root / '.git/config').read_bytes(), configuration_before)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('configured Git executable filters or conditional includes are refused', result.stderr)

    def test_smudge_filter_is_refused_before_checkout_effects(self):
        self.assert_filter_refused_without_effects('smudge')

    def test_clean_filter_is_refused_before_status_effects(self):
        self.assert_filter_refused_without_effects('clean')

    def test_process_filter_is_refused_before_checkout_effects(self):
        self.assert_filter_refused_without_effects('process')

    def test_included_filter_configuration_is_refused(self):
        self.assert_filter_refused_without_effects('smudge', included=True)

    def test_branch_conditional_filter_configuration_is_refused(self):
        self.assert_filter_refused_without_effects('smudge', included='conditional')

    def test_symlink_manifest_is_refused(self):
        manifest = self.root / 'fleet/tasks.json'
        content = manifest.read_text()
        manifest.unlink()
        elsewhere = self.root / 'redirect.json'
        elsewhere.write_text(content)
        manifest.symlink_to(elsewhere)
        self.rejected('validate')


if __name__ == '__main__':
    unittest.main()
