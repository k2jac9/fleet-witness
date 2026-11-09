"""Real SQLite regressions: budget aliases, lost reservations and cap changes."""
from contextlib import closing
import multiprocessing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from fleet_witness.swarm import providers as p


def reserve_child(path, start, results):
    try:
        ledger = p.Ledger('openrouter', 1, 1, Path(path))
        start.wait(5)
        ledger.reserve(.75)
        results.put('reserved')
    except p.BudgetExceeded:
        results.put('denied')


class SharedLedgerTest(unittest.TestCase):
    def test_tags_share_provider_liability(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(p, 'LEDGER_DIR', Path(tmp)):
            with patch.dict(os.environ, {'FLEET_WITNESS_LEDGER_TAG': 'first'}):
                first = p.Ledger('openrouter', 1, 1)
                reservation = first.reserve(.75)
                first.settle(.75 if reservation is None else reservation, .75)
            with patch.dict(os.environ, {'FLEET_WITNESS_LEDGER_TAG': '../second'}):
                second = p.Ledger('openrouter', 1, 1)
                self.assertEqual(first.path, second.path)
                with self.assertRaises(p.BudgetExceeded):
                    second.reserve(.75)

    def test_concurrent_processes_cannot_reserve_same_money(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'ledger.sqlite3'
            p.Ledger('openrouter', 1, 1, path)
            ctx = multiprocessing.get_context('spawn')
            start, results = ctx.Event(), ctx.Queue()
            children = [ctx.Process(target=reserve_child, args=(str(path), start, results)) for _ in range(2)]
            for child in children:
                child.start()
            start.set()
            observed = [results.get(timeout=15) for _ in children]
            for child in children:
                child.join(15)
                self.assertEqual(child.exitcode, 0)
            self.assertEqual(sorted(observed), ['denied', 'reserved'])

    def test_restart_preserves_reservation_and_stops_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'ledger.sqlite3'
            p.Ledger('openrouter', 1, 1, path).reserve(.25)
            restarted = p.Ledger('openrouter', 1, 1, path)
            with self.assertRaises(p.BudgetExceeded):
                restarted.reserve(.1)
            self.assertEqual(restarted.snapshot()['provider']['held_usd'], .25)

    def test_provider_cap_cannot_be_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'ledger.sqlite3'
            p.Ledger('openrouter', 1, 1, path)
            for changed in (2, .5):
                with self.subTest(changed=changed), self.assertRaises(p.BudgetExceeded):
                    p.Ledger('openrouter', 1, changed, path)

    def test_existing_json_blocks_even_custom_database_and_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            legacy = Path(tmp) / 'spend-ledger-openrouter-historical.json'
            legacy.write_bytes(b'{"unreconciled":true}')
            with self.assertRaises(p.BudgetExceeded):
                p.Ledger('openrouter', 1, 1, Path(tmp) / 'fresh.sqlite3')
            self.assertEqual(legacy.read_bytes(), b'{"unreconciled":true}')
            self.assertFalse((Path(tmp) / 'fresh.sqlite3').exists())

    def test_negative_nonfinite_bool_and_subunit_caps_are_refused(self):
        for bad in (-1, float('nan'), float('inf'), True, '0.0000000001'):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises((ValueError, p.BudgetExceeded)):
                    p.Ledger('openrouter', bad, 1, Path(tmp) / 'ledger.sqlite3')

    def test_overrun_keeps_larger_hold_and_blocks_new_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = p.Ledger('openrouter', 1, 1, Path(tmp) / 'ledger.sqlite3')
            request = ledger.reserve(.2)
            ledger.settle(.2 if request is None else request, 1.5)
            self.assertTrue(hasattr(ledger, 'snapshot'), 'ledger must expose durable liabilities')
            snapshot = ledger.snapshot()
            self.assertTrue(hasattr(ledger, 'snapshot'), 'ledger must expose durable liabilities')
            self.assertEqual(snapshot['provider']['held_usd'], 1.5)
            self.assertEqual(snapshot['provider']['settled_usd'], 0)
            self.assertTrue(snapshot['halted'])
            with self.assertRaises(p.BudgetExceeded):
                ledger.reserve(.01)

    def test_settlement_and_audit_roll_back_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'ledger.sqlite3'
            ledger = p.Ledger('openrouter', 1, 1, path)
            request = ledger.reserve(.2)
            self.assertTrue(path.exists(), 'reservation must be durable before dispatch')
            self.assertEqual(path.read_bytes()[:16], b'SQLite format 3\x00')
            with closing(sqlite3.connect(path)) as con:
                con.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END")
            with self.assertRaises(sqlite3.DatabaseError):
                ledger.settle(.2 if request is None else request, .1)
            self.assertEqual(ledger.snapshot()['run']['held_usd'], .2)
            self.assertEqual(ledger.snapshot()['run']['settled_usd'], 0)

    def test_double_settlement_cannot_reduce_liability(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = p.Ledger('openrouter', 1, 1, Path(tmp) / 'ledger.sqlite3')
            request = ledger.reserve(.2)
            ledger.settle(.2 if request is None else request, .1)
            with self.assertRaises((ValueError, p.BudgetExceeded)):
                ledger.settle(.2 if request is None else request, 0)
            self.assertEqual(ledger.lifetime_spent(), .1)


def dispatch_and_crash(path):
    ledger = p.Ledger('openrouter', 1, 1, Path(path), run_id='crashed-run')
    request = ledger.reserve(.2)
    ledger.dispatch(request)
    os._exit(17)


class LedgerRecoveryTest(unittest.TestCase):
    def test_crash_after_dispatch_keeps_accounting_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'ledger.sqlite3'
            child = multiprocessing.get_context('spawn').Process(target=dispatch_and_crash, args=(str(path),))
            child.start()
            child.join(10)
            self.assertEqual(child.exitcode, 17)
            restarted = p.Ledger('openrouter', 1, 1, path, run_id='crashed-run')
            self.assertEqual(restarted.calls, 1)
            self.assertEqual(restarted.run_reserved, .2)
            with self.assertRaises(p.BudgetExceeded): restarted.reserve(.1)
            with closing(sqlite3.connect(path)) as con:
                self.assertEqual(con.execute('SELECT status FROM requests').fetchone()[0], 'dispatched')
                self.assertEqual(con.execute("SELECT COUNT(*) FROM audit WHERE kind='dispatched'").fetchone()[0], 1)

    def test_nanodollar_rounding_never_discards_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = p.Ledger('openrouter', '0.000000001', 1, Path(tmp) / 'ledger.sqlite3')
            ledger.reserve('0.0000000001')
            self.assertEqual(ledger.run_reserved, .000000001)

    def test_large_known_charge_is_preserved_even_above_cap_and_integer_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = p.Ledger('openrouter', 1, 1, Path(tmp) / 'ledger.sqlite3')
            reservation = ledger.reserve(.1)
            try:
                ledger.settle(reservation, '10000000000')
            except ValueError:
                self.fail('a known large charge must remain a durable liability')
            self.assertEqual(ledger.run_reserved, 10000000000)
            with self.assertRaises(p.BudgetExceeded): ledger.reserve(.1)
