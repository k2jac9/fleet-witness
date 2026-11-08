#!/usr/bin/env python3
"""Offline ADR-governed task planning and Git worktree preparation (ADR-0006)."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess


TASK_FIELDS = {'id', 'title', 'role', 'status', 'depends_on', 'owned_paths',
               'adrs', 'acceptance', 'brief'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def no_symlinks(path):
    """Check existing components without resolving away evidence of redirection."""
    for component in (path, *path.parents):
        require(not component.is_symlink(), f'symlink refused: {component}')


def safe_path(root, value):
    require(isinstance(value, str) and bool(value), 'path must be a nonempty string')
    parts = value.split('/')
    require(not any(c in value for c in '\\:*?[]\x00\r\n') and
            all(part not in ('', '.', '..') for part in parts) and
            parts[0] not in ('.git', '.fleet', '.worktrees'), f'unsafe path: {value!r}')
    require(not PurePosixPath(value).is_absolute(), f'absolute path: {value}')
    result = root.joinpath(*parts)
    no_symlinks(result)
    return result


def git(root, *args, check=True):
    # Local checkout hooks and fsmonitor helpers are not part of task preparation.
    result = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null',
                             '-c', 'core.fsmonitor=false', '-C', str(root), *args],
                            text=True, capture_output=True)
    if check and result.returncode:
        raise ValueError(f'git {args[0]} failed: {result.stderr.strip()}')
    return result



def reject_executable_filters(root):
    # Read effective configuration, including included/global/worktree settings,
    # before any status or checkout can execute clean/smudge/process commands.
    # Conditional includes can activate only after entering the new branch/path,
    # so refuse them too instead of evaluating only the current checkout context.
    # Names only: filter command values may contain private configuration.
    result = git(root, 'config', '--includes', '--null', '--name-only',
                 '--get-regexp',
                 r'^(filter\..*\.(clean|smudge|process)|includeif\..*\.path)$',
                 check=False)
    require(result.returncode in (0, 1), 'cannot inspect Git filter configuration')
    require(result.returncode == 1, 'configured Git executable filters or conditional includes are refused')

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'duplicate JSON key: {key}')
        result[key] = value
    return result


def text_value(value):
    return isinstance(value, str) and bool(value.strip()) and '\x00' not in value


def string_list(value, nonempty=False):
    return (isinstance(value, list) and (bool(value) or not nonempty) and
            all(text_value(item) for item in value) and len(set(value)) == len(value))


def load_plan(root):
    no_symlinks(root)
    require(root.is_dir(), f'root is not a directory: {root}')
    actual = Path(git(root, 'rev-parse', '--show-toplevel').stdout.strip())
    require(root == actual, 'root must be the Git worktree top level without aliases')
    reject_executable_filters(root)
    manifest_path = safe_path(root, 'fleet/tasks.json')
    manifest = json.loads(manifest_path.read_text(), object_pairs_hook=unique_object)
    require(isinstance(manifest, dict) and set(manifest) ==
            {'version', 'owner', 'default_budget_usd', 'tasks'}, 'invalid manifest fields')
    require(type(manifest['version']) is int and manifest['version'] == 1, 'version must be 1')
    require(manifest['owner'] == 'k2jac9', 'owner must be k2jac9')
    require(type(manifest['default_budget_usd']) is int and manifest['default_budget_usd'] == 0,
            'default_budget_usd must be 0; paid execution is not implemented')
    tasks = manifest['tasks']
    require(isinstance(tasks, list) and tasks, 'tasks must be a nonempty array')
    by_id = {}
    for task in tasks:
        require(isinstance(task, dict) and set(task) == TASK_FIELDS, 'invalid task fields')
        task_id = task['id']
        require(isinstance(task_id, str) and re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', task_id),
                'invalid task id')
        require(task_id not in by_id, f'duplicate task id: {task_id}')
        by_id[task_id] = task
        require(all(text_value(task[key]) for key in ('title', 'role', 'brief')),
                f'{task_id}: title, role, and brief must be nonempty strings')
        require(task['status'] in ('todo', 'done'), f'{task_id}: invalid status')
        for field in ('depends_on', 'owned_paths', 'adrs'):
            require(string_list(task[field], field != 'depends_on'), f'{task_id}: invalid {field}')
        for path in task['owned_paths']:
            safe_path(root, path)
        for reference in task['adrs']:
            adr = safe_path(root, reference)
            require(re.fullmatch(r'docs/adr/\d{4}-[a-z0-9-]+\.md', reference) and adr.is_file(),
                    f'{task_id}: invalid ADR reference: {reference}')
            require(re.search(r'^- Status: Accepted\b', adr.read_text(), re.MULTILINE),
                    f'{task_id}: ADR is not accepted: {reference}')
        commands = task['acceptance']
        require(isinstance(commands, list) and commands and
                all(isinstance(argv, list) and argv and all(text_value(arg) for arg in argv)
                    for argv in commands), f'{task_id}: acceptance must contain argv arrays')
    for task in tasks:
        require(all(dep in by_id for dep in task['depends_on']),
                f"{task['id']}: unknown dependency")
    # Iterative topological ordering also avoids recursion on malformed deep DAGs.
    remaining = set(by_id)
    ordered = []
    while remaining:
        available = sorted(task_id for task_id in remaining
                           if not (set(by_id[task_id]['depends_on']) & remaining))
        require(available, 'dependency cycle')
        ordered.extend(by_id[task_id] for task_id in available)
        remaining.difference_update(available)
    states = {task['id']: ('done' if task['status'] == 'done' else
                          'ready' if all(by_id[dep]['status'] == 'done'
                                         for dep in task['depends_on']) else 'blocked')
              for task in ordered}
    owners = []
    for task in ordered:
        if states[task['id']] != 'ready':
            continue
        for path in task['owned_paths']:
            for prior, owner in owners:
                require(not (path == prior or path.startswith(prior + '/') or
                             prior.startswith(path + '/')),
                        f"ready ownership overlap: {owner} / {task['id']}: {prior} / {path}")
            owners.append((path, task['id']))
    return manifest, ordered, states


def prepare(root, task, state):
    task_id = task['id']
    require(state == 'ready', f'{task_id} is {state}; only ready tasks can be prepared')
    require(not git(root, 'status', '--porcelain', '--untracked-files=no').stdout,
            'tracked worktree must be clean')
    branch = f'fleet/{task_id}'
    require(git(root, 'show-ref', '--verify', '--quiet', f'refs/heads/{branch}',
                check=False).returncode == 1, f'branch already exists: {branch}')
    parent = root / '.worktrees'
    target = parent / task_id
    no_symlinks(target)
    require(not os.path.lexists(target), f'worktree path already exists: {target}')
    require(not parent.exists() or parent.is_dir(), '.worktrees must be a directory')
    # Fail before Git effects if the committed tree would redirect the brief.
    require(not git(root, 'ls-tree', 'HEAD', '--', '.fleet').stdout,
            'HEAD must not track .fleet')
    for path in ('.worktrees/check', '.fleet/brief.md'):
        require(git(root, 'check-ignore', '--quiet', path, check=False).returncode == 0,
                f'{path} must be ignored before preparation')
    # Registered missing worktrees are still existing artifacts, not invitations to prune.
    registered = git(root, 'worktree', 'list', '--porcelain', '-z').stdout.split('\x00')
    require(f'worktree {target}' not in registered, f'worktree already registered: {target}')
    brief = (f"# {task_id}: {task['title']}\n\nRole: {task['role']}\nOwner: k2jac9\n"
             'External budget: $0\n\nRead AGENTS.md and docs/architecture.md first.\n\n'
             + task['brief'] + '\n\nOwned paths:\n'
             + ''.join(f'- {path}\n' for path in task['owned_paths'])
             + '\nAccepted ADRs:\n' + ''.join(f'- {adr}\n' for adr in task['adrs'])
             + '\nAcceptance argv (operator runs explicitly):\n'
             + ''.join(f'- `{json.dumps(argv)}`\n' for argv in task['acceptance'])
             + '\nReport task ID, exact commit, changed paths, actual commands/results, and limitations.\n'
               'Do not spend, merge, publish, grant access, or revise accepted ADRs.\n'
               'Worktrees isolate changes; they are not process sandboxes. ADR-0008 describes the optional worker environment.\n')
    parent.mkdir(exist_ok=True)
    git(root, 'worktree', 'add', '-b', branch, str(target), 'HEAD')
    directory = target / '.fleet'
    no_symlinks(directory)
    directory.mkdir()
    (directory / 'brief.md').write_text(brief)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).absolute().parents[1],
                        help='exact Git worktree root (default: this script\'s repository)')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('validate')
    sub.add_parser('plan')
    sub.add_parser('prepare').add_argument('task_id')
    args = parser.parse_args(argv)
    try:
        root = args.root.absolute()
        manifest, ordered, states = load_plan(root)
        if args.command == 'validate':
            print(f"Valid: {len(ordered)} tasks; owner {manifest['owner']}; external budget $0")
        elif args.command == 'plan':
            print('Planning only: status is not verification; external budget $0')
            for task in ordered:
                print(f"{task['id']}: {states[task['id']]} — {task['title']}")
        else:
            matches = [task for task in ordered if task['id'] == args.task_id]
            require(matches, f'unknown task: {args.task_id}')
            target = prepare(root, matches[0], states[args.task_id])
            print(f'Prepared {args.task_id}: {target}\nBrief: {target / ".fleet/brief.md"}')
    except (ValueError, OSError, UnicodeError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
