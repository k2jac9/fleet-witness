"""Local symmetric receipt integrity, separate from applicability and authority.

The key belongs to the trusted controller/issuer side of this in-process demo.
HMAC does not establish public verifiability or process isolation.
"""
import hashlib
import hmac
import json

FIELDS = frozenset({'issuer', 'claim', 'scope', 'artifact_digest', 'run_id'})


def _payload(fields):
    return json.dumps(fields, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')


def issue_receipt(key: bytes, *, issuer: str, claim: str, scope: str,
                  artifact_digest: str, run_id: str) -> dict:
    fields = dict(issuer=issuer, claim=claim, scope=scope,
                  artifact_digest=artifact_digest, run_id=run_id)
    if not all(isinstance(value, str) and value for value in fields.values()):
        raise ValueError('receipt fields must be nonempty strings')
    return dict(fields, signature=hmac.new(key, _payload(fields), hashlib.sha256).hexdigest())


def verify_receipt(receipt, key: bytes, run_id: str, artifact_digest: str) -> tuple[bool, str]:
    if not isinstance(receipt, dict) or set(receipt) != FIELDS | {'signature'}:
        return False, 'Malformed receipt'
    if not all(isinstance(value, str) and value for value in receipt.values()):
        return False, 'Malformed receipt fields'
    supplied_signature = receipt['signature']
    if len(supplied_signature) != 64 or any(char not in '0123456789abcdef' for char in supplied_signature):
        return False, 'Malformed receipt signature'
    fields = {name: receipt[name] for name in FIELDS}
    signature = hmac.new(key, _payload(fields), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, receipt['signature']):
        return False, 'Receipt integrity failed'
    expected = {'issuer': 'safety-issuer', 'claim': 'release_safe', 'scope': 'release',
                'run_id': run_id, 'artifact_digest': artifact_digest}
    for name, value in expected.items():
        if receipt[name] != value:
            return False, 'Receipt is not applicable: ' + name
    return True, 'Authentic, applicable release-safety receipt'
