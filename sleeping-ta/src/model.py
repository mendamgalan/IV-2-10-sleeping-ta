"""Single-controller interface to the POSIX thread simulation."""

import ctypes
import json
import os
import tempfile
from pathlib import Path


class Model:
    def __init__(self):
        library = Path(__file__).resolve().parents[1] / 'libta.so'
        self.lib = ctypes.CDLL(str(library))
        self.lib.sim_init.argtypes = [ctypes.c_int] * 6 + [ctypes.c_uint]
        self.lib.sim_init.restype = ctypes.c_int
        for name in ('sim_snapshot', 'sim_events', 'sim_recent_events'):
            function = getattr(self.lib, name)
            function.argtypes = []
            function.restype = ctypes.c_char_p
        for name in ('sim_close', 'sim_step'):
            function = getattr(self.lib, name)
            function.argtypes = []
            function.restype = None
        self.lib.sim_export.argtypes = [ctypes.c_char_p]
        self.lib.sim_export.restype = ctypes.c_int

    def reset(self, n=8, chairs=3, amin=10, amax=40,
              hmin=15, hmax=30, seed=42):
        # Validate BEFORE ctypes can wrap large Python integers to C integers.
        limits = {
            'n': (n, 1, 40),
            'chairs': (chairs, 0, 20),
            'amin': (amin, 1, 6000),
            'amax': (amax, 1, 6000),
            'hmin': (hmin, 1, 6000),
            'hmax': (hmax, 1, 6000),
            'seed': (seed, 0, 4294967295),
        }
        for name, (value, low, high) in limits.items():
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f'{name}: {low}–{high} хооронд бүхэл тоо оруулна.')
        if amin > amax or hmin > hmax:
            raise ValueError('Ирэх болон туслах хугацааны min ≤ max байна.')
        result = self.lib.sim_init(n, chairs, amin, amax, hmin, hmax, seed)
        if result == -2:
            raise OSError('Журналын түр файл үүсгэж чадсангүй. Дискний зай, эрхийг шалгана.')
        if result == -3:
            raise OSError('Thread эсвэл semaphore үүсгэж чадсангүй. Reset хийж дахин оролдоно.')
        if result:
            raise ValueError('Хөдөлгүүр тохиргоог хүлээн авсангүй.')

    def step(self):
        self.lib.sim_step()
        return self.snapshot()

    def snapshot(self):
        return json.loads(self.lib.sim_snapshot())

    def events(self):
        """Full CSV for tests/tools; the UI uses recent_events instead."""
        data = self.lib.sim_events()
        if data is None:
            raise OSError('Журналыг бүрэн уншиж чадсангүй.')
        return 'tick,event,student,waiting\n' + data.decode('utf-8')

    def recent_events(self):
        return self.lib.sim_recent_events().decode('utf-8')

    def export(self, filename):
        """Stream to a sibling temporary file and replace only on success."""
        destination = Path(filename).absolute()
        fd, temporary = tempfile.mkstemp(prefix='.ta-export-', dir=destination.parent)
        os.close(fd)
        try:
            if self.lib.sim_export(os.fsencode(temporary)):
                raise OSError('CSV бүрэн хадгалагдсангүй. Дискний зай, эрхийг шалгана.')
            os.replace(temporary, destination)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def close(self):
        self.lib.sim_close()
