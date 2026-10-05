import sys, unittest, csv, io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from model import Model
class EngineTests(unittest.TestCase):
    def setUp(self): self.m=Model()
    def tearDown(self): self.m.close()
    def run_case(self,n,c,a,b,h,j,steps=500):
        self.m.reset(n,c,a,b,h,j)
        for _ in range(steps):
            s=self.m.step();q=s['queue'];states=[x['state'] for x in s['students']]
            self.assertLessEqual(len(q),c);self.assertEqual(len(q),len(set(q)))
            self.assertNotIn(s['current'],q)
            self.assertEqual(states.count(2),int(s['current']>=0))
            self.assertEqual(states.count(1),len(q))
            self.assertEqual(s['arrivals'],s['rejected']+s['completed']+len(q)+int(s['current']>=0))
        return s
    def test_baseline_fifo(self):
        s=self.run_case(8,3,10,40,15,30);self.assertGreater(s['completed'],0)
        pending=[]
        for e in csv.DictReader(io.StringIO(self.m.events())):
            if e['event']=='queue':pending.append(e['student'])
            if e['event']=='help_start' and pending:self.assertEqual(e['student'],pending.pop(0))
    def test_zero_chairs(self):
        s=self.run_case(10,0,1,1,10,10);self.assertGreater(s['rejected'],0)
    def test_single_student_no_rejection(self):
        s=self.run_case(1,0,2,2,3,3);self.assertEqual(s['rejected'],0)
    def test_overload_and_maximum(self):
        s=self.run_case(40,20,1,2,30,40);self.assertGreater(s['rejected'],0)
    def test_sleep_until_arrival(self):
        self.m.reset(2,3,100,100,2,2)
        for _ in range(99):self.assertEqual(self.m.step()['current'],-1)
        self.assertGreaterEqual(self.m.step()['current'],0)
    def test_reproducible_and_reset(self):
        logs=[]
        for _ in range(3):self.run_case(8,3,1,5,2,8,100);logs.append(self.m.events())
        self.assertEqual(logs[0],logs[1]);self.assertEqual(logs[1],logs[2])
    def test_invalid(self):
        for args in [(0,3,1,2,1,2),(41,3,1,2,1,2),(3,-1,1,2,1,2),(3,21,1,2,1,2),(3,3,0,2,1,2),(3,3,3,2,1,2)]:
            with self.assertRaises(ValueError):self.m.reset(*args)
    def test_service_duration(self):
        self.run_case(1,0,1,1,5,5,100)
        start=None
        for e in csv.DictReader(io.StringIO(self.m.events())):
            if e['event']=='help_start':start=int(e['tick'])
            if e['event']=='help_end':self.assertEqual(int(e['tick'])-start,5)
