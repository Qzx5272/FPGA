"""Executable design checks, NOT synthesizable RTL or board performance evidence.

Run with Python 3. Only the control ownership contract and arithmetic estimates
are checked. Audio tails, transport parsing and hardware scheduling are excluded.
"""
from dataclasses import dataclass
from pathlib import Path
import json, math, unittest

@dataclass(frozen=True)
class Note:
    source: int
    track: int
    epoch: int
    note_id: int
    pitch: int

class Ensemble:
    def __init__(self, tracks=16, capacity=64):
        self.leases = {i:(0,0) for i in range(tracks)}
        self.capacity = capacity
        self.active = {}
        self.seen = set()

    def transfer(self, track, new_owner):
        """Atomic lease boundary. Returned voices require a hardware fade-out.

        Production epoch fields must not wrap while old packets can exist.
        This unbounded-integer specification deliberately excludes wraparound.
        """
        _, epoch = self.leases[track]
        retired = [n for n in self.active.values() if n.track == track]
        self.active = {k:n for k,n in self.active.items() if n.track != track}
        self.leases[track] = (new_owner,epoch+1)
        self.seen = {k for k in self.seen if k[1] != track}
        return retired

    @staticmethod
    def key(n):
        return (n.source,n.track,n.epoch,n.note_id)

    def on(self,n):
        if not 0 <= n.pitch <= 127:
            raise ValueError('pitch outside MIDI range')
        if self.leases[n.track] != (n.source,n.epoch): return 'stale_owner'
        key=self.key(n)
        if key in self.seen: return 'duplicate_or_retired'
        if len(self.active) >= self.capacity: return 'capacity'
        self.active[key]=n; self.seen.add(key)
        return 'accepted'

    def off(self,n):
        # A NoteOff arriving before its NoteOn tombstones that identity. This
        # avoids a stuck note if the transport fails to reorder the pair.
        if self.leases[n.track] != (n.source,n.epoch): return False
        key=self.key(n); self.seen.add(key)
        return self.active.pop(key,None) is not None

    def disconnect(self,source):
        # Each remote lease is revoked, invalidating queued old NoteOns too.
        retired=[]
        for track,(owner,_) in list(self.leases.items()):
            if owner==source: retired.extend(self.transfer(track,-1))
        return retired

    def panic(self):
        retired=list(self.active.values())
        for track,(owner,_) in list(self.leases.items()): self.transfer(track,owner)
        return retired

class OwnershipTests(unittest.TestCase):
    def test_same_pitch_two_players(self):
        e=Ensemble();e.transfer(0,1);e.transfer(1,2)
        a=Note(1,0,1,10,60);b=Note(2,1,1,10,60)
        e.on(a);e.on(b);e.off(a)
        self.assertEqual(list(e.active.values()),[b])

    def test_old_release_after_takeover(self):
        e=Ensemble();old=Note(0,0,0,10,60);e.on(old)
        self.assertEqual(e.transfer(0,1),[old])
        new=Note(1,0,1,10,60);e.on(new)
        self.assertFalse(e.off(old));self.assertIn(e.key(new),e.active)

    def test_late_automatic_note_is_rejected(self):
        e=Ensemble();e.transfer(0,1)
        self.assertEqual(e.on(Note(0,0,0,42,64)),'stale_owner')

    def test_replayed_on_does_not_retrigger(self):
        e=Ensemble();n=Note(0,0,0,1,60);e.on(n);e.off(n)
        self.assertEqual(e.on(n),'duplicate_or_retired');self.assertFalse(e.active)

    def test_off_before_on_does_not_stick(self):
        e=Ensemble();n=Note(0,0,0,1,60);e.off(n)
        self.assertEqual(e.on(n),'duplicate_or_retired')

    def test_disconnect_preserves_other_owner_and_offline_part(self):
        e=Ensemble();e.transfer(0,1);e.transfer(1,2)
        a=Note(1,0,1,1,60);b=Note(2,1,1,1,60);auto=Note(0,2,0,1,60)
        for n in (a,b,auto): e.on(n)
        e.disconnect(1)
        self.assertEqual(set(e.active.values()),{b,auto})
        self.assertEqual(e.on(Note(1,0,1,2,67)),'stale_owner')

    def test_full_pool_still_accepts_release(self):
        e=Ensemble(capacity=1);a=Note(0,0,0,1,60);b=Note(0,0,0,2,64)
        e.on(a);self.assertEqual(e.on(b),'capacity')
        self.assertTrue(e.off(a));self.assertEqual(e.on(b),'accepted')

    def test_panic_invalidates_future_events(self):
        e=Ensemble();n=Note(0,0,0,1,60);e.on(n);e.panic()
        self.assertFalse(e.active)
        self.assertEqual(e.on(Note(0,0,0,2,67)),'stale_owner')

def budget(clock,partials,lanes=8,fs=48000,overhead=192):
    # Overhead is a design reservation, NOT measured hardware cycle count.
    cycles=math.floor(clock/fs)
    required=math.ceil(partials/lanes)+overhead
    return dict(clock_hz=clock,sample_rate=fs,partials=partials,lanes=lanes,
                minimum_cycles_per_sample=cycles,assumed_overhead_cycles=overhead,
                estimated_required_cycles=required,margin_cycles=cycles-required,
                margin_fraction=(cycles-required)/cycles,
                state_bytes_assuming_32_per_partial=partials*32,
                fits_arithmetic_only=required<=cycles)

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(OwnershipTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    estimates=[budget(c,n) for c in (50000000,98304000) for n in (1024,4096,8192)]
    report={'status':'reference_model_only','tests_run':result.testsRun,
            'failures':len(result.failures),'errors':len(result.errors),
            'limitations':['No RTL, synthesis, board timing, audio or transport validation',
                           'Epoch and tombstone storage are unbounded in this reference',
                           'RAM port conflicts and pipeline hazards not modeled'],
            'budgets':estimates}
    Path(__file__).with_name('design_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
