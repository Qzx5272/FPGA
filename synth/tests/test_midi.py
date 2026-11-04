import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from midi_input import PadMap

class MidiTests(unittest.TestCase):
    def test_velocity_zero_and_chords(self):
        m=PadMap()
        self.assertEqual(m.feed([0x99,36,117]),117)
        m.feed([0x99,40,76]);self.assertEqual(m.keys,{0,4})
        m.feed([0x99,36,0]);self.assertEqual(m.keys,{4})
        m.feed([0x89,40,64]);self.assertEqual(m.keys,set())

    def test_channels_and_shared_slot(self):
        m=PadMap({'0:36':0,'1:40':0})
        m.feed([0x90,36,50]);m.feed([0x91,40,90])
        m.feed([0x80,36,0]);self.assertEqual(m.keys,{0})
        m.feed([0xb0,123,0]);self.assertEqual(m.keys,{0})
        m.feed([0xb1,120,0]);self.assertEqual(m.keys,set())

    def test_unknown_and_non_notes(self):
        m=PadMap()
        for message in ([0xf8],[0xe0,0,64],[0x90,100,90],[0xb0,7,100]):
            self.assertIsNone(m.feed(message))
        self.assertFalse(m.keys)

if __name__=='__main__':unittest.main()
