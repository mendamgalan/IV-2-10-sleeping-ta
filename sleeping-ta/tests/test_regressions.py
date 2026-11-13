"""Regression checks for journal capacity, ctypes validation and lifecycle."""
import csv
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model import Model


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.model = Model()
        self.model.reset()

    def tearDown(self):
        self.model.close()

    def test_python_inputs_rejected_before_ctypes_conversion(self):
        before = self.model.snapshot()
        invalid = [
            {'n': 4294967297}, {'chairs': 4294967296},
            {'amin': 4294967297}, {'hmax': 4294967297},
            {'seed': -1}, {'seed': 4294967296},
            {'n': True}, {'n': 1.0}, {'n': '8'}, {'seed': None},
            {'amax': float('inf')}, {'hmin': float('nan')},
            {'amin': 3, 'amax': 2}, {'hmin': 3, 'hmax': 2},
            {'amax': 6001}, {'hmin': 0}, {'free': 1},
        ]
        for values in invalid:
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    self.model.reset(**values)
                self.assertEqual(self.model.snapshot(), before)

    def test_maximum_valid_seed(self):
        self.model.reset(seed=4294967295)
        self.assertTrue(self.model.step()['active'])

    def test_long_run_preserves_full_journal_and_live_tail(self):
        self.model.reset(n=40, chairs=0, amin=1, amax=1, hmin=10, hmax=10)
        for _ in range(1000):
            snapshot = self.model.step()
        data = self.model.events()
        self.assertGreater(len(data.encode()), 262144)
        rows = list(csv.DictReader(io.StringIO(data)))
        self.assertEqual(int(rows[-1]['tick']), 1000)
        self.assertEqual(sum(row['event'] == 'arrive' for row in rows), snapshot['arrivals'])
        self.assertEqual(sum(row['event'] == 'full_return' for row in rows), snapshot['rejected'])
        self.assertEqual(self.model.recent_events().splitlines(), data.splitlines()[-6:])
        self.assertFalse(snapshot['journal_error'])
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'журнал.csv'
            target.write_text('old export', encoding='utf-8')
            self.model.export(target)
            self.assertEqual(target.read_text(encoding='utf-8'), data)
            self.assertEqual(list(Path(folder).glob('.ta-export-*')), [])
        self.model.step()  # Reading/exporting must leave the append position intact.
        self.assertEqual(int(self.model.events().splitlines()[-1].split(',')[0]), 1001)

    def test_export_keeps_normal_file_mode(self):
        umask = os.umask(0o022)
        try:
            with tempfile.TemporaryDirectory() as folder:
                fresh = Path(folder) / 'new.csv'
                self.model.export(fresh)
                self.assertEqual(fresh.stat().st_mode & 0o777, 0o644)
                shared = Path(folder) / 'shared.csv'
                shared.write_text('old', encoding='utf-8')
                shared.chmod(0o664)
                self.model.export(shared)
                self.assertEqual(shared.stat().st_mode & 0o777, 0o664)
        finally:
            os.umask(umask)

    def test_failed_export_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'existing.csv'
            target.write_text('keep me', encoding='utf-8')
            self.model.close()  # No journal is available to export.
            with self.assertRaises(OSError):
                self.model.export(target)
            self.assertEqual(target.read_text(encoding='utf-8'), 'keep me')
            self.assertEqual(list(Path(folder).glob('.ta-export-*')), [])

    def test_reset_discards_old_history(self):
        self.model.reset(n=4, amin=1, amax=1)
        for _ in range(20):
            self.model.step()
        self.model.reset(n=1)
        self.assertEqual(self.model.events(), 'tick,event,student,waiting\n0,sleep,0,0\n')
        self.assertEqual(self.model.recent_events(), '0,sleep,0,0\n')
        self.assertEqual(self.model.snapshot()['tick'], 0)

    def test_help_is_spread_across_students(self):
        # Manual 7 long run: a fixed student order served only 4 of 40.
        self.model.reset(n=40, chairs=0, amin=1, amax=1, hmin=10, hmax=10)
        for _ in range(1010):
            snapshot = self.model.step()
        served = sum(1 for s in snapshot['students'] if s['visits'])
        self.assertGreaterEqual(served, 30)

    def test_free_mode_keeps_invariants(self):
        configs = [(40, 3, 1, 3, 1, 4), (40, 0, 1, 1, 2, 2), (10, 5, 1, 9, 1, 9)]
        for n, chairs, amin, amax, hmin, hmax in configs:
            self.model.reset(n=n, chairs=chairs, amin=amin, amax=amax,
                             hmin=hmin, hmax=hmax, free=True)
            for _ in range(500):
                s = self.model.step()
                q, cur = s['queue'], s['current']
                states = [x['state'] for x in s['students']]
                self.assertTrue(s['free'])
                self.assertLessEqual(len(q), chairs)
                self.assertEqual(len(q), len(set(q)))
                self.assertEqual(states.count(1), len(q))
                self.assertEqual(states.count(2), int(cur >= 0))
                self.assertEqual(s['arrivals'],
                                 s['rejected'] + s['completed'] + len(q) + int(cur >= 0))
            self.assertGreater(s['completed'], 0)

    def test_close_is_repeatable_idle_and_busy(self):
        for steps in (0, 1, 10):
            self.model.reset(n=4, amin=1, amax=1, hmin=10, hmax=10)
            for _ in range(steps):
                self.model.step()
            self.model.close()
            self.model.close()
            self.assertFalse(self.model.snapshot()['active'])
