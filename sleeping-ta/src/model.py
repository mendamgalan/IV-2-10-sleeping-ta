import ctypes
import json
from pathlib import Path

class Model:
    def __init__(self):
        self.lib = ctypes.CDLL(str(Path(__file__).resolve().parents[1] / 'libta.so'))
        self.lib.sim_init.argtypes = [ctypes.c_int]*6 + [ctypes.c_uint]
        self.lib.sim_init.restype = ctypes.c_int
        for name in ('sim_snapshot', 'sim_events'):
            getattr(self.lib, name).restype = ctypes.c_char_p
        for name in ('sim_close', 'sim_step'):
            getattr(self.lib, name).restype = None
    def reset(self, n=8, chairs=3, amin=10, amax=40, hmin=15, hmax=30, seed=42):
        if self.lib.sim_init(n, chairs, amin, amax, hmin, hmax, seed):
            raise ValueError('Оюутан 1–40, сандал 0–20, хугацаа 1–6000 tick; min ≤ max байна.')
    def step(self):
        self.lib.sim_step()
        return self.snapshot()
    def snapshot(self):
        return json.loads(self.lib.sim_snapshot())
    def events(self):
        return 'tick,event,student,waiting\n' + self.lib.sim_events().decode()
    def close(self):
        self.lib.sim_close()
