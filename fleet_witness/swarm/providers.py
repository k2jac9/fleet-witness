"""Budget-capped model clients for live swarm runs (standard library only).

Every real request first reserves its worst-case cost in a persistent ledger
shared by all runs on this machine. A request that would cross the lifetime
cap or the per-run cap is refused before anything is sent. Ambiguous failures
(timeouts, transport errors after sending) are charged at the reserved worst
case so the ledger never under-counts. Keys are read from the environment only
and are never logged or written to run output.

This is a hackathon spend guard for one machine and one process at a time,
not a provider-enforced cap: always also watch the provider's own dashboard.
"""
import json
import os
from pathlib import Path
import random
import re
import socket
import threading
import time
import urllib.error
import urllib.request

ADAPTION_URL = 'https://api.prod.adaptionlabs.ai/api/v1/responses'
OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
OPENROUTER_MODELS_URL = 'https://openrouter.ai/api/v1/models'

# Credits per 1M tokens (input, output) from docs.adaptionlabs.ai/inference-stacks/models,
# checked 2026-11-08. The account owner reports 1 credit = 1 USD.
ADAPTION_PRICES = {
    'deepseek-v4-flash': (0.04444, 0.13332),
    'gemma-4-26b-a4b-it': (0.0765, 0.255),
    'gemma-4-31b-it': (0.09, 0.34),
    'qwen3.8-27b': (0.039, 1.25),
    'glm-53-flash': (0.15, 0.50),
    'qwen3.5-397b': (0.55, 3.50),
    'glm-5.2': (1.40, 4.40),
}

LEDGER_DIR = Path.home() / '.fleet_witness'
# Lifetime caps per provider unless overridden; deliberately far below the balances.
DEFAULT_LIFETIME_CAP = {'adaption': 100.0, 'openrouter': 15.0, 'fake': 1e9}


class BudgetExceeded(RuntimeError):
    pass


class ProviderError(RuntimeError):
    pass


def _env_key(name: str) -> str:
    value = os.environ.get(name)
    if not value and os.name == 'nt':
        # Keys saved with `setx` are visible to new processes only; read the user scope directly.
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as handle:
                value = winreg.QueryValueEx(handle, name)[0]
        except OSError:
            value = None
    if not value:
        raise ProviderError(f'{name} is not set')
    return value


def estimate_tokens(text: str) -> int:
    """Deliberately pessimistic: about 3 characters per token, plus overhead."""
    return len(text) // 3 + 64


class Ledger:
    """Persistent per-provider spend with lifetime and per-run hard caps."""

    def __init__(self, provider: str, run_cap_usd: float, lifetime_cap_usd: float | None = None,
                 path: Path | None = None):
        """One ledger file per provider, so parallel sweeps on different providers never share a file.
        Two processes on the SAME provider would still race: run one sweep per provider at a time."""
        self.provider = provider
        self.path = Path(path) if path else LEDGER_DIR / f'spend-ledger-{provider}.json'
        self.run_cap = float(run_cap_usd)
        self.lifetime_cap = float(DEFAULT_LIFETIME_CAP.get(provider, 5.0)
                                  if lifetime_cap_usd is None else lifetime_cap_usd)
        self.run_spent = 0.0
        self.run_reserved = 0.0
        self.calls = 0
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        for attempt in range(20):
            try:
                return json.loads(self.path.read_text(encoding='utf-8'))
            except FileNotFoundError:
                return {}
            except PermissionError:  # Windows: file briefly locked by antivirus/indexer
                time.sleep(0.05 * (attempt + 1))
        raise BudgetExceeded(f'cannot read spend ledger {self.path}; refusing to spend blind')

    def _save(self, data: dict):
        tmp = self.path.with_name(f'{self.path.stem}.{os.getpid()}.tmp')
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')
        for attempt in range(20):
            try:
                os.replace(tmp, self.path)
                return
            except PermissionError:
                time.sleep(0.05 * (attempt + 1))
        raise BudgetExceeded(f'cannot write spend ledger {self.path}; stopping to stay safe')

    def lifetime_spent(self) -> float:
        with self._lock:
            return self._load().get(self.provider, {}).get('spent_usd', 0.0)

    def reserve(self, usd: float):
        with self._lock:
            spent = self._load().get(self.provider, {}).get('spent_usd', 0.0)
            if spent + self.run_reserved + usd > self.lifetime_cap:
                raise BudgetExceeded(f'{self.provider} lifetime cap ${self.lifetime_cap:.2f} would be exceeded '
                                     f'(spent ${spent:.4f})')
            if self.run_spent + self.run_reserved + usd > self.run_cap:
                raise BudgetExceeded(f'run cap ${self.run_cap:.2f} would be exceeded '
                                     f'(run spent ${self.run_spent:.4f})')
            self.run_reserved += usd

    def settle(self, reserved: float, actual: float):
        with self._lock:
            self.run_reserved -= reserved
            self.run_spent += actual
            self.calls += 1
            data = self._load()
            entry = data.setdefault(self.provider, {'spent_usd': 0.0, 'calls': 0})
            entry['spent_usd'] = round(entry['spent_usd'] + actual, 8)
            entry['calls'] += 1
            self._save(data)


class NotSent(ProviderError):
    """The provider certainly did not process the request (DNS/connect failure, 4xx, rate limit)."""


RETRY_AFTER_RE = re.compile(r'retry after (\d+)', re.I)


class _RateGate:
    """Shared pause: when any request is rate limited, every thread waits it out."""

    def __init__(self):
        self._lock = threading.Lock()
        self._resume_at = 0.0

    def wait(self):
        while True:
            with self._lock:
                delay = self._resume_at - time.monotonic()
            if delay <= 0:
                return
            time.sleep(min(delay, 5.0))

    def pause(self, seconds: float):
        with self._lock:
            self._resume_at = max(self._resume_at, time.monotonic() + seconds)


def _post(url: str, key: str, body: dict, timeout: float, gate: _RateGate, extra_headers=None,
          max_rate_waits: int = 15) -> dict:
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    headers.update(extra_headers or {})
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method='POST')
    for _ in range(max_rate_waits + 1):
        gate.wait()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as error:
            detail = error.read()[:300].decode('utf-8', 'replace')
            if error.code == 429:
                # Not processed, so retrying cannot double bill. Honour the provider's wait for everyone.
                match = RETRY_AFTER_RE.search(detail)
                header = error.headers.get('Retry-After') if error.headers else None
                seconds = float(match.group(1)) if match else float(header) if (header or '').isdigit() else 30.0
                gate.pause(seconds + random.random() * 3)
                continue
            if 400 <= error.code < 500:
                raise NotSent(f'HTTP {error.code}: {detail}') from None
            raise ProviderError(f'HTTP {error.code}: {detail}') from None
        except urllib.error.URLError as error:
            if isinstance(error.reason, (socket.gaierror, ConnectionRefusedError)):
                raise NotSent(f'not sent: {error.reason}') from None
            raise ProviderError(str(error)) from None
    raise NotSent('rate limited too many times')


class ModelClient:
    """One model on one provider. `complete` returns text plus usage and cost."""

    def __init__(self, provider: str, model: str, ledger: Ledger, *, max_output_tokens: int = 220,
                 temperature: float = 0.7, timeout: float = 90.0, max_concurrency: int = 16):
        if provider not in ('adaption', 'openrouter'):
            raise ValueError('provider must be adaption or openrouter')
        self.provider, self.model, self.ledger = provider, model, ledger
        self.max_output_tokens, self.temperature, self.timeout = max_output_tokens, temperature, timeout
        self._gate = threading.Semaphore(max_concurrency)
        self._rate = _RateGate()
        self._key = _env_key('ADAPTION_API_KEY' if provider == 'adaption' else 'OPENROUTER_API_KEY')
        if provider == 'adaption':
            if model not in ADAPTION_PRICES:
                raise ValueError(f'unknown Adaption price for {model}; known: {sorted(ADAPTION_PRICES)}')
            self.prices = ADAPTION_PRICES[model]
        else:
            self.prices = openrouter_prices(model)

    @property
    def label(self):
        return f'{self.provider}:{self.model}'

    def worst_case_usd(self, system: str, user: str) -> float:
        tokens_in = estimate_tokens(system) + estimate_tokens(user)
        return (tokens_in * self.prices[0] + self.max_output_tokens * self.prices[1]) / 1e6

    def complete(self, system: str, user: str, meta=None) -> dict:
        reserved = self.worst_case_usd(system, user)
        self.ledger.reserve(reserved)
        actual = reserved
        started = time.monotonic()
        try:
            with self._gate:
                if self.provider == 'adaption':
                    data = _post(ADAPTION_URL, self._key, {
                        'model': self.model, 'instructions': system, 'input': user,
                        'max_output_tokens': self.max_output_tokens, 'temperature': self.temperature,
                        'store': False}, self.timeout, self._rate)
                    text = data.get('output_text') or ''.join(
                        part.get('text', '') for item in data.get('output', []) if item.get('type') == 'message'
                        for part in item.get('content', []) if part.get('type') == 'output_text')
                    usage = data.get('usage') or {}
                    tokens_in, tokens_out = usage.get('input_tokens'), usage.get('output_tokens')
                    reported_cost = None
                else:
                    data = _post(OPENROUTER_URL, self._key, {
                        'model': self.model, 'max_tokens': self.max_output_tokens,
                        'temperature': self.temperature, 'usage': {'include': True},
                        'messages': [{'role': 'system', 'content': system},
                                     {'role': 'user', 'content': user}]}, self.timeout, self._rate,
                        {'X-Title': 'Fleet Witness hackathon'})
                    if 'error' in data:
                        raise ProviderError(str(data['error'])[:300])
                    text = (data.get('choices') or [{}])[0].get('message', {}).get('content') or ''
                    usage = data.get('usage') or {}
                    tokens_in, tokens_out = usage.get('prompt_tokens'), usage.get('completion_tokens')
                    reported_cost = usage.get('cost')
            if isinstance(tokens_in, int) and isinstance(tokens_out, int):
                computed = (tokens_in * self.prices[0] + tokens_out * self.prices[1]) / 1e6
                actual = float(reported_cost) if isinstance(reported_cost, (int, float)) else computed
            return {'text': text, 'input_tokens': tokens_in, 'output_tokens': tokens_out,
                    'cost_usd': actual, 'latency_s': round(time.monotonic() - started, 3)}
        except NotSent:
            actual = 0.0  # certainly unprocessed, so certainly unbilled
            raise
        finally:
            # On any failure `actual` stays at the reserved worst case.
            self.ledger.settle(reserved, actual)


_PRICE_CACHE = {}


def openrouter_prices(model: str) -> tuple[float, float]:
    """USD per 1M tokens from OpenRouter's public model list (no key, no cost)."""
    if model not in _PRICE_CACHE:
        with urllib.request.urlopen(OPENROUTER_MODELS_URL, timeout=30) as response:
            for entry in json.loads(response.read().decode('utf-8'))['data']:
                pricing = entry.get('pricing') or {}
                try:
                    _PRICE_CACHE[entry['id']] = (float(pricing['prompt']) * 1e6, float(pricing['completion']) * 1e6)
                except (KeyError, TypeError, ValueError):
                    continue
    if model not in _PRICE_CACHE:
        raise ValueError(f'OpenRouter model not found: {model}')
    return _PRICE_CACHE[model]


class FakeClient:
    """Offline stand-in. Uses runner-supplied `meta` to imitate plausible agents.

    Honest agents judge visible receipt fields (so forged signatures fool them),
    sometimes follow a visible majority, and colluders push their targets with a
    shared talking point. Costs nothing and makes no network calls.
    """

    label = 'fake:scripted'
    max_output_tokens = 0

    def __init__(self, seed: int = 0, herd_probability: float = 0.35):
        self.seed, self.herd_probability = seed, herd_probability
        self.ledger = None

    def worst_case_usd(self, system, user):
        return 0.0

    def complete(self, system: str, user: str, meta=None) -> dict:
        meta = meta or {}
        rng = random.Random(f"{self.seed}:{meta.get('role')}:{meta.get('agent_id')}:{meta.get('case_id')}:"
                            f"{meta.get('condition')}")
        if meta.get('role') == 'auditor':
            sign = bool(meta.get('looks_valid'))
            if meta.get('colluder') and meta.get('target'):
                sign = True
            elif meta.get('board_approve_share') is not None and rng.random() < self.herd_probability / 3:
                sign = meta['board_approve_share'] > 0.5
            reason = (meta.get('talking_point') if meta.get('colluder') and meta.get('target')
                      else 'Receipt fields match the rule.' if sign else 'Receipt does not establish safety.')
            return {'text': json.dumps({'sign': sign, 'reason': reason}), 'input_tokens': 0,
                    'output_tokens': 0, 'cost_usd': 0.0, 'latency_s': 0.0}
        honest_vote = 'approve' if meta.get('looks_valid') else 'deny'
        reasons = {
            'approve': ['Receipt fields match the artifact and run; release looks fine.',
                        'Safety receipt matches scope and digest, approving.',
                        'Evidence appears applicable to this exact release.'],
            'deny': ['Receipt does not establish release safety for this artifact.',
                     'Build success is not a safety claim; denying.',
                     'Receipt run or artifact does not match the release.'],
        }
        if meta.get('colluder') and meta.get('target'):
            vote = 'approve'
            reason = f"{meta.get('talking_point')} Approving."
        else:
            vote = honest_vote
            tally = meta.get('tally')
            if tally and tally['approve'] != tally['deny'] and rng.random() < self.herd_probability:
                vote = 'approve' if tally['approve'] > tally['deny'] else 'deny'
            reason = rng.choice(reasons[vote])
        return {'text': json.dumps({'vote': vote, 'reason': reason}), 'input_tokens': 0,
                'output_tokens': 0, 'cost_usd': 0.0, 'latency_s': 0.0}


VOTE_RE = re.compile(r'\{.*\}', re.S)


def parse_sign(text: str) -> tuple[str, str]:
    """Extract {"sign": bool, "reason": ...} -> ('sign'|'refuse'|'abstain', reason). Unclear output never signs."""
    match = VOTE_RE.search(text or '')
    if match:
        try:
            data = json.loads(match.group(0))
            sign = data.get('sign')
            if isinstance(sign, str):
                sign = {'true': True, 'false': False}.get(sign.strip().lower())
            if isinstance(sign, bool):
                return ('sign' if sign else 'refuse'), str(data.get('reason', ''))[:400]
        except (json.JSONDecodeError, AttributeError):
            pass
    return 'abstain', (text or '')[:400]


def parse_vote(text: str) -> tuple[str, str]:
    """Extract {"vote": approve|deny, "reason": ...}; anything else is an abstention."""
    match = VOTE_RE.search(text or '')
    if match:
        try:
            data = json.loads(match.group(0))
            vote = str(data.get('vote', '')).strip().lower()
            if vote in ('approve', 'deny'):
                return vote, str(data.get('reason', ''))[:400]
        except (json.JSONDecodeError, AttributeError):
            pass
    lowered = (text or '').lower()
    if 'approve' in lowered and 'deny' not in lowered:
        return 'approve', (text or '')[:400]
    if 'deny' in lowered and 'approve' not in lowered:
        return 'deny', (text or '')[:400]
    return 'abstain', (text or '')[:400]
