"""Fixture oracle: independent of controller evidence and authorization helpers."""


def evaluate_decision(recommendation: str, *, evidence_valid_at_snapshot: bool,
                      permission_at_snapshot: bool) -> dict:
    expected = 'approve' if evidence_valid_at_snapshot and permission_at_snapshot else 'deny'
    reason = ('Decision-time truth includes an applicable safety attestation and release permission.'
              if expected == 'approve' else
              'Decision-time truth lacks applicable authentic safety evidence or release permission.')
    return {'decision_valid_at_snapshot': recommendation == expected,
            'expected_recommendation': expected, 'reason': reason}
