"""Finite-storage control contract. Reference model, not claimed as RTL."""
from dataclasses import dataclass
from pathlib import Path
import json,random,unittest
MAX=(1<<32)-1

@dataclass
class Slot:
    serial:int=0
    seen:bool=False
    active:bool=False
    pitch:int=0

class Control:
    def __init__(self,tracks=16,slots=16,capacity=64):
        self.owner=[0]*tracks;self.epoch=[0]*tracks
        self.slots=[[Slot() for _ in range(slots)] for _ in range(tracks)]
        self.capacity=capacity
    def count(self):return sum(s.active for row in self.slots for s in row)
    def transfer(self,t,owner):
        if self.epoch[t]==MAX:raise OverflowError('quiesce link, flush all scheduled events, then reinitialize epoch')
        retired=sum(s.active for s in self.slots[t]);self.epoch[t]+=1;self.owner[t]=owner
        self.slots[t]=[Slot() for _ in self.slots[t]]
        return retired
    def event(self,kind,source,track,slot,epoch,serial,pitch=60):
        if not (0<=serial<=MAX and 0<=epoch<=MAX):return 'range'
        if not (0<=track<len(self.slots) and 0<=slot<len(self.slots[track])):return 'range'
        if (source,epoch)!=(self.owner[track],self.epoch[track]):return 'lease'
        s=self.slots[track][slot]
        if s.seen and serial<s.serial:return 'old'
        if kind=='off':
            # Future release tombstones only this finite contact slot/version.
            s.serial=serial;s.seen=True;s.active=False;return 'release'
        if kind!='on' or not 0<=pitch<=127:return 'range'
        if s.seen and serial==s.serial:return 'duplicate_or_closed'
        if not s.active and self.count()>=self.capacity:return 'capacity'
        # Replacement of a live contact is an atomic retrigger; audio tail needs
        # its own fade/retirement voice, which this control model does not render.
        s.serial=serial;s.seen=True;s.active=True;s.pitch=pitch;return 'start'

class Tests(unittest.TestCase):
    def test_late_off_and_dispatch_lease(self):
        c=Control();c.event('on',0,0,0,0,3);c.transfer(0,1)
        self.assertEqual(c.event('on',1,0,0,1,0),'start')
        self.assertEqual(c.event('off',0,0,0,0,3),'lease')
        self.assertEqual(c.event('on',0,0,1,0,4),'lease')
        self.assertEqual(c.count(),1)
    def test_off_before_on_and_old_release(self):
        c=Control();c.event('off',0,0,0,0,5)
        self.assertEqual(c.event('on',0,0,0,0,5),'duplicate_or_closed')
        self.assertEqual(c.event('on',0,0,0,0,6),'start')
        self.assertEqual(c.event('off',0,0,0,0,5),'old');self.assertEqual(c.count(),1)
    def test_release_while_capacity_full(self):
        c=Control(capacity=1);c.event('on',0,0,0,0,1)
        self.assertEqual(c.event('on',0,1,0,0,1),'capacity')
        self.assertEqual(c.event('off',0,0,0,0,1),'release')
        self.assertEqual(c.event('on',0,1,0,0,1),'start')
    def test_same_pitch_separate_contacts(self):
        c=Control();c.event('on',0,0,0,0,1);c.event('on',0,0,1,0,1)
        c.event('off',0,0,0,0,1);self.assertTrue(c.slots[0][1].active)
    def test_finite_epoch_exhaustion(self):
        c=Control();c.epoch[0]=MAX
        with self.assertRaises(OverflowError):c.transfer(0,1)
        self.assertEqual(c.event('on',0,0,0,MAX,MAX+1),'range')
    def test_reordering_does_not_resurrect_released_versions(self):
        r=random.Random(2026138);c=Control(capacity=256)
        # All releases are delivered, with duplicates and arbitrary permutations.
        for batch in range(1000):
            events=[]
            for t in range(16):
                slot=r.randrange(16);v=batch*3+2
                events.extend([('on',0,t,slot,0,v),('off',0,t,slot,0,v),('on',0,t,slot,0,v-1)])
            r.shuffle(events)
            for e in events:c.event(*e)
            self.assertEqual(c.count(),0)
        self.assertEqual(sum(map(len,c.slots)),256)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    out={'scope':'finite reference contract, no transport parser or RTL validation','tests':result.testsRun,
         'failures':len(result.failures),'errors':len(result.errors),'fixed_contact_slots':256,
         'random_reordered_events':48000,'serial_bits':32,'epoch_bits':32,
         'requires':'dispatch-time lease check, separate release mailboxes, audible tail handling, link quiescence before epoch wrap'}
    (Path(__file__).resolve().parent/'deep'/'finite_control_results.json').write_text(json.dumps(out,indent=2))
    raise SystemExit(not result.wasSuccessful())
