"""UI checks run under a desktop display or xvfb-run in CI."""
import sys
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from app import App


class UiTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f'График дэлгэц байхгүй: {error}')
        self.root.withdraw()
        self.app = App(self.root)

    def tearDown(self):
        if hasattr(self, 'app'):
            self.app.close()

    def test_pause_step_and_reset(self):
        self.app.play()
        self.app.loop()
        self.app.pause()
        before = self.app.model.snapshot()
        self.app.loop()
        self.assertEqual(self.app.model.snapshot(), before)
        self.app.step()
        self.assertFalse(self.app.running)
        self.assertEqual(self.app.model.snapshot()['tick'], before['tick'] + 1)
        self.app.fields['n'].set('2')
        self.app.reset()
        self.assertEqual(len(self.app.model.snapshot()['students']), 2)
        self.assertEqual(self.app.model.snapshot()['tick'], 0)

    def test_invalid_inputs_preserve_current_run(self):
        before = self.app.model.snapshot()
        for field, value in [('n', '4294967297'), ('chairs', '-1'),
                             ('amin', 'nan'), ('hmin', 'inf'), ('seed', 'abc')]:
            with self.subTest(field=field, value=value):
                old = self.app.fields[field].get()
                self.app.fields[field].set(value)
                with patch('app.messagebox.showerror') as error:
                    self.app.reset()
                self.assertTrue(error.called)
                self.assertEqual(self.app.model.snapshot(), before)
                self.app.fields[field].set(old)

    def test_draw_uses_recent_log_not_entire_history(self):
        with patch.object(self.app.model, 'events', side_effect=AssertionError('full history')):
            self.app.draw()
        self.assertIn('sleep', self.app.log.get('1.0', 'end'))

    def test_journal_failure_visible(self):
        snapshot = self.app.model.snapshot()
        snapshot['journal_error'] = 1
        with patch.object(self.app.model, 'snapshot', return_value=snapshot):
            self.app.draw()
        self.assertIn('алдаа', self.app.warning.cget('text'))
