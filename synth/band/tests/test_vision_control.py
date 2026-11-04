import os,sys,time,unittest
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from PySide6.QtGui import QImage,QColor
from app import QApplication,Desk
from vision_selection import SelectionGate,red_marker,apply_selection
from vision_control import VisionControl


def marker_image(part,second=None):
    image=QImage(96,64,QImage.Format.Format_RGBA8888);image.fill(QColor('black'))
    for role in ([part] if second is None else [part,second]):
        cx=12+(role%4)*24;cy=16+(role//4)*32
        for y in range(cy-3,cy+3):
            for x in range(cx-3,cx+3):image.setPixelColor(x,y,QColor(240,20,20))
    return image


def detect(image):
    return red_marker(bytes(image.constBits()),image.width(),image.height(),image.bytesPerLine())


class VisionModelTests(unittest.TestCase):
    def test_eight_regions_and_ambiguous_scene(self):
        for part in range(8):self.assertEqual(detect(marker_image(part))['part'],part)
        self.assertIsNone(detect(marker_image(0,7)))
        image=marker_image(0);image.fill(QColor('red'));self.assertIsNone(detect(image))
        image.fill(QColor(150,150,150));self.assertIsNone(detect(image))

    def test_grid_boundary_rejected_and_bad_buffer(self):
        image=marker_image(0);image.fill(QColor('black'))
        for y in range(12,20):
            for x in range(21,27):image.setPixelColor(x,y,QColor('red'))
        self.assertIsNone(detect(image))
        self.assertIsNone(red_marker(b'\x00',96,64,384))

    def test_dwell_loss_gap_and_clock_reversal(self):
        g=SelectionGate()
        for i in range(9):g.observe(3,i*.1)
        self.assertEqual(g.candidate(.8),3)
        self.assertIsNone(g.candidate(1.2))
        g.observe(3,1.3);self.assertIsNone(g.candidate(1.3))
        g.observe(3,.2);self.assertIsNone(g.candidate(.2))
        g.observe(None,.3);self.assertIsNone(g.candidate(.3))
        g.observe(3,float('nan'));self.assertIsNone(g.candidate(.4))

    def test_confirmation_requires_marker_rearm(self):
        g=SelectionGate()
        for i in range(10):g.observe(6,i*.1)
        self.assertEqual(g.candidate(.9),6);g.consume()
        for i in range(10,30):g.observe(6,i*.1)
        self.assertIsNone(g.candidate(2.9))
        g.observe(None,3)
        for i in range(31,41):g.observe(6,i*.1)
        self.assertEqual(g.candidate(4),6)


class VisionGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.desk=Desk();self.desk.pump_timer.stop();self.desk.beat_timer.stop()
        self.dialog=VisionControl(self.desk);self.dialog.timer.stop()
    def tearDown(self):self.dialog.close();self.desk.close()

    def test_dialog_never_autostarts_or_generates_events(self):
        self.dialog.show();self.app.processEvents()
        self.assertFalse(self.dialog.running);self.assertIsNone(self.dialog.camera)
        self.assertFalse(self.dialog.confirm.isEnabled());self.assertFalse(self.desk.queue)

    def test_frame_dwell_confirmation_and_freshness(self):
        self.dialog.running=True;now=time.monotonic()
        for i in range(10):self.dialog.process_image(marker_image(3),now-.9+i*.1)
        self.assertTrue(self.dialog.confirm.isEnabled());self.assertEqual(self.desk.seat_parts[1],6)
        self.dialog.accept_candidate();self.assertEqual(self.desk.seat_parts[1],3)
        self.assertFalse(self.desk.queue);self.assertFalse(self.dialog.confirm.isEnabled())
        self.dialog.gate.reset()
        for i in range(10):self.dialog.process_image(marker_image(4),now-2+i*.1)
        self.dialog.accept_candidate();self.assertEqual(self.desk.seat_parts[1],3)

    def test_held_pedal_conflict_and_other_seat(self):
        self.desk.held[(2,1)]={'part':0}
        self.assertFalse(apply_selection(self.desk,2,3)[0]);self.assertEqual(self.desk.seat_parts[2],0)
        self.desk.held.clear();self.desk.midi_sustain.add((2,0))
        self.assertFalse(apply_selection(self.desk,2,3)[0]);self.desk.midi_sustain.clear()
        self.desk.port=object();self.desk.states[3]={'owner':4}
        self.assertFalse(apply_selection(self.desk,2,3)[0]);self.desk.port=None
        self.assertTrue(apply_selection(self.desk,2,3)[0]);self.assertEqual(self.desk.seat_parts[2],3)
        self.assertEqual(self.desk.part.currentIndex(),6);self.assertFalse(self.desk.queue)

    def test_hiding_clears_pending_candidate(self):
        self.dialog.show();self.app.processEvents();self.dialog.running=True
        for i in range(10):self.dialog.gate.observe(3,i*.1)
        self.dialog.hide();self.assertFalse(self.dialog.running)
        self.assertIsNone(self.dialog.gate.candidate(.9));self.assertFalse(self.dialog.confirm.isEnabled())

    def test_parent_close_stops_vision(self):
        self.desk.vision_control=self.dialog;self.dialog.show();self.app.processEvents()
        self.dialog.running=True;self.desk.close();self.assertFalse(self.dialog.running)

    def test_camera_error_clears_candidate_and_releases(self):
        class Camera:
            def errorString(self):return 'Disconnected test camera'
            def stop(self):self.stopped=True
            def deleteLater(self):self.deleted=True
        camera=Camera();self.dialog.camera=camera;self.dialog.running=True
        for i in range(10):self.dialog.gate.observe(3,i*.1)
        self.dialog.camera_error()
        self.assertTrue(camera.stopped and camera.deleted);self.assertFalse(self.dialog.running)
        self.assertIsNone(self.dialog.gate.candidate(.9));self.assertIn('Disconnected',self.dialog.message.text())

    def test_space_panic_remains_available(self):
        from unittest.mock import patch
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.dialog.show();self.dialog.activateWindow();self.dialog.confirm.setEnabled(True)
        self.dialog.confirm.setFocus();self.app.processEvents()
        with patch.object(self.desk,'panic') as panic:
            QTest.keyClick(self.dialog.confirm,Qt.Key.Key_Space)
            panic.assert_called_once()


if __name__=='__main__':unittest.main()
