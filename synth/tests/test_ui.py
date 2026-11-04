import os,sys,unittest
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QEvent,QCoreApplication
from PySide6.QtTest import QTest
from app import MainWindow,STYLE
from protocol import TelemetryParser

class FakePort:
    def __init__(self):self.writes=[]
    def write(self,p):self.writes.append(p);return len(p)
    def close(self):pass

class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([]);cls.app.setStyleSheet(STYLE)
    def setUp(self):self.w=MainWindow();self.w.timer.stop();self.fake=FakePort();self.w.port=self.fake
    def tearDown(self):
        self.w.close();self.w.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        self.app.processEvents()
    def test_controls_and_polyphony(self):
        self.w.mouse_note(0,True);self.w.mouse_note(4,True)
        self.assertEqual(self.fake.writes[-1][3],17)
        self.w.mouse_note(0,False);self.assertEqual(self.fake.writes[-1][3],16)
        self.w.knobs['brightness'].setValue(211);self.w.volume.setValue(77)
        self.w.knobs['attack_ms'].setValue(100);self.w.knobs['release_ms'].setValue(500)
        self.w.send();p=self.fake.writes[-1]
        self.assertEqual(p[6],211);self.assertEqual(p[7],77)
        self.assertEqual(int.from_bytes(p[9:11],'little'),14)
        self.w.preset(2);self.assertEqual(self.fake.writes[-1][5],2)
        self.w.octave(1);self.assertEqual(self.fake.writes[-1][4],5)
        self.assertEqual(self.w.controls.keys,0)
        self.w.panic();self.assertEqual(self.fake.writes[-1][13]&3,1)

    def test_board_transport_and_mode_change(self):
        self.w.toggle_play(True)
        self.assertFalse(self.w.controls.auto_play)
        self.w.confirmed=True;self.w.toggle_play(True)
        self.assertEqual(self.fake.writes[-1][13]&3,2)
        self.w.tempo.setValue(60);self.w.send()
        self.assertEqual((self.fake.writes[-1][13]>>2)*2+40,120)
        self.w.select_voice(0)
        self.assertTrue(self.w.controls.auto_play)
        self.w.panic()
        self.assertFalse(self.w.controls.auto_play)
        self.assertEqual(self.fake.writes[-1][13]&3,1)

    def test_midi_keyboard_ownership_and_panic(self):
        self.w.confirmed=True
        self.w.mouse_note(0,True)
        self.w.midi.handle([0x99,36,111])
        self.w.midi.handle([0x99,40,87])
        self.assertEqual(self.fake.writes[-1][3],17)
        self.assertEqual(self.fake.writes[-1][8],127)
        self.w.midi.handle([0x89,36,0])
        self.assertEqual(self.fake.writes[-1][3],17)
        self.w.mouse_note(0,False)
        self.assertEqual(self.fake.writes[-1][3],16)
        self.w.panic();self.assertEqual(self.fake.writes[-1][3],0)
        self.assertFalse(self.w.midi.mapper.keys)

    def test_midi_learning_persistence(self):
        import tempfile,json
        panel=self.w.midi
        # Simulate an open input without consuming the user's physical device.
        panel.device=object()
        with tempfile.TemporaryDirectory() as temp:
            panel.mapping_file=Path(temp)/'mapping.json';panel.device_name='test-pad'
            panel.start_learning()
            panel.handle([0x99,48,90]);panel.handle([0x99,48,0]);panel.handle([0x99,48,100])
            self.assertEqual(len(panel.learning),1)
            for note in [50,52,53,55,57,59,60]:panel.handle([0x99,note,90])
            self.assertIsNone(panel.learning)
            mapping=json.loads(panel.mapping_file.read_text())['test-pad']
            self.assertEqual(mapping['9:48'],0);self.assertEqual(mapping['9:60'],7)
            self.assertFalse(panel.mapper.keys)
        panel.device=None

    def test_voice_sequence_stop_and_return(self):
        self.w.confirmed=True;self.w.sing_hello()
        self.assertEqual(self.fake.writes[-1][5],3)
        self.assertEqual(self.fake.writes[-1][6],8)
        self.w.next_voice_event()
        self.assertEqual(self.w.controls.keys,0)
        self.w.sing_hello(True)
        self.assertEqual(self.fake.writes[-1][6],9)
        self.assertFalse(self.w.knobs['brightness'].isEnabled())
        self.w.panic()
        self.assertFalse(self.w.voice_timer.isActive())
        self.assertEqual(self.w.voice_events,[])
        self.assertEqual(self.w.controls.keys,0)
        self.w.preset(0)
        self.assertTrue(self.w.knobs['brightness'].isEnabled())
        self.assertEqual(self.w.controls.tone,0)

if __name__=='__main__':unittest.main()
