"""Derive replay data from committed SQLite records and sealed fixture labels."""
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

from .evaluation import evaluate_decision


def export_replay(database: Path, trajectories: list[dict], seed: int) -> dict:
    episodes = []
    with closing(sqlite3.connect(database)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute('BEGIN')  # One read snapshot, even if a later adapter writes concurrently.
        for fixture in trajectories:
            trial_id = fixture['id']
            decision = conn.execute('SELECT * FROM decisions WHERE trial_id=?', (trial_id,)).fetchone()
            attempts = conn.execute('SELECT * FROM attempts WHERE decision_id=? ORDER BY rowid',
                                    (decision['id'],)).fetchall()
            events = conn.execute('SELECT * FROM events WHERE trial_id=? ORDER BY seq', (trial_id,)).fetchall()
            episodes.append({
                **{name: fixture[name] for name in ('id', 'pair_id', 'scenario', 'title',
                    'worker_policy', 'reviewer_policy', 'presentation')},
                'artifact_digest': decision['artifact_digest'],
                'supervisor_input': json.loads(decision['supervisor_input']),
                'decision': {name: decision[name] for name in ('id', 'recommendation', 'reason')},
                'evaluation': evaluate_decision(decision['recommendation'],
                    evidence_valid_at_snapshot=fixture['evidence_valid_at_snapshot'],
                    permission_at_snapshot=fixture['permission_at_snapshot']),
                'attempts': [{'id': row['id'],
                    'execution_authorized_at_attempt': bool(row['execution_authorized_at_attempt']),
                    'effect_occurred': bool(row['effect_occurred']),
                    'reason': row['reason'], 'policy_version': row['policy_version']} for row in attempts],
                'events': [{'seq': row['seq'], 'kind': row['kind'], 'actor': row['actor'],
                            'message': row['message'], 'details': json.loads(row['details'])} for row in events],
                'receipts': json.loads(decision['receipts']),
            })
    all_attempts = [attempt for episode in episodes for attempt in episode['attempts']]
    return {'schema_version': '1.0', 'project': 'Fleet Witness', 'mode': 'scripted-demo',
            'seed': seed, 'generated_at': datetime.now(timezone.utc).isoformat(),
            'summary': {'episodes': len(episodes),
                'approved_recommendations': sum(e['decision']['recommendation'] == 'approve' for e in episodes),
                'invalid_recommendations': sum(not e['evaluation']['decision_valid_at_snapshot'] for e in episodes),
                'execution_attempts': len(all_attempts),
                'effects': sum(a['effect_occurred'] for a in all_attempts),
                'denied_attempts': sum(not a['execution_authorized_at_attempt'] for a in all_attempts)},
            'episodes': episodes}
