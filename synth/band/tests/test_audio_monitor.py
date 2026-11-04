import unittest,sys,math,struct,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from audio_monitor import PCMWindow,AudioMonitor
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QCoreApplication,QEvent,QBuffer,QIODevice
from PySide6.QtTest import QTest
from PySide6.QtMultimedia import QAudio,QAudioFormat

class AudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_split_pcm_stereo_frequency_and_amplitude(self):
        pcm=b''.join(struct.pack('<hh',round(16384*math.sin(2*math.pi*32*n/1024)),round(8192*math.cos(2*math.pi*64*n/1024))) for n in range(2048))
        w=PCMWindow()
        for i in range(0,len(pcm),7):w.feed(pcm[i:i+7],1.0)
        d=w.snapshot(1.1)
        self.assertEqual(len(d['left']),2048);self.assertEqual(w.pending,b'')
        self.assertEqual(max(range(len(d['db'])),key=d['db'].__getitem__),32)
        self.assertAlmostEqual(d['db'][32],-6.0206,places=2)
        self.assertAlmostEqual(d['right'][0],0.25);self.assertEqual(d['clipped'],0)
        self.assertIsNone(w.snapshot(1.501));self.assertIsNone(w.snapshot(0.9))
    def test_format_bounds_rails_and_nonfinite(self):
        for encoding,values,expected in [('B',(0,128,255),(-1,0,127/128)),('h',(-32768,0,32767),(-1,0,32767/32768)),('i',(-2147483648,0,2147483647),(-1,0,2147483647/2147483648)),('f',(-1,0,1),(-1,0,1))]:
            w=PCMWindow(channels=1,encoding=encoding);w.feed(struct.pack('<'+encoding*3,*values),0)
            d=w.snapshot(0);self.assertEqual(d['left'],list(expected));self.assertEqual(d['right'],d['left']);self.assertEqual(d['clipped'],2)
        w=PCMWindow(channels=1,encoding='f');w.feed(struct.pack('<fff',float('nan'),float('inf'),float('-inf')),0)
        self.assertEqual(w.snapshot(0)['left'],[0,0,0])
        w.feed(struct.pack('<f',0.25)*10000,0);self.assertEqual(len(w.left),2048)
    def test_desk_close_also_closes_audio_monitor(self):
        from app import Desk
        desk=Desk();desk.pump_timer.stop();desk.beat_timer.stop();desk.open_stage()
        with patch('PySide6.QtMultimedia.QMediaDevices.audioInputs',return_value=[]):desk.stage_view.open_audio()
        monitor=desk.stage_view.audio_monitor
        self.assertTrue(monitor.isVisible());desk.close();self.app.processEvents()
        self.assertFalse(monitor.isVisible());self.assertFalse(monitor.timer.isActive())
        desk.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    def test_start_preferred_format_read_error_and_failed_reopen(self):
        fmt=QAudioFormat();fmt.setSampleRate(44100);fmt.setChannelCount(1);fmt.setSampleFormat(QAudioFormat.SampleFormat.Float)
        class Device:
            def description(self):return 'Mock input, no hardware'
            def isFormatSupported(self,f):return False
            def preferredFormat(self):return fmt
        with patch('PySide6.QtMultimedia.QMediaDevices.audioInputs',return_value=[Device()]):dlg=AudioMonitor()
        buffer=QBuffer(dlg);buffer.setData(struct.pack('<fff',0.25,-1,0.5));buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        class Source:
            failure=QAudio.Error.NoError;stopped=False;deleted=False
            def setBufferSize(self,n):self.size=n
            def start(self):return buffer
            def stop(self):self.stopped=True
            def deleteLater(self):self.deleted=True
            def error(self):return self.failure
        source=Source()
        with patch('PySide6.QtMultimedia.QAudioSource',return_value=source) as factory:dlg.start()
        self.assertEqual(factory.call_args.args[1].sampleRate(),44100)
        self.assertFalse(dlg.inputs.isEnabled());self.assertFalse(dlg.begin.isEnabled())
        buffer.readyRead.emit();dlg.refresh();self.assertEqual(dlg.canvas.data['left'],[0.25,-1,0.5])
        source.failure=QAudio.Error.IOError;dlg.refresh()
        self.assertTrue(source.stopped);self.assertTrue(source.deleted);self.assertIsNone(dlg.canvas.data)
        self.assertTrue(dlg.begin.isEnabled());self.assertIn('IOError',dlg.status.text())
        source=Source();source.start=lambda:None
        with patch('PySide6.QtMultimedia.QAudioSource',return_value=source):dlg.start()
        self.assertIsNone(dlg.source);self.assertIsNone(dlg.window);self.assertTrue(source.stopped)
        dlg.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    def test_dialog_no_autocapture_and_hide_releases(self):
        app=self.app
        panics=[]
        with patch('PySide6.QtMultimedia.QMediaDevices.audioInputs',return_value=[]):dlg=AudioMonitor(panic=lambda:panics.append(True))
        self.assertIsNone(dlg.source);self.assertFalse(dlg.begin.isEnabled())
        class Source:
            stopped=False;deleted=False
            def error(self):return QAudio.Error.NoError
            def stop(self):self.stopped=True
            def deleteLater(self):self.deleted=True
        source=Source();dlg.source=source;dlg.window=PCMWindow();dlg.window.feed(b'\0'*8192,time.monotonic())
        dlg.show();app.processEvents();dlg.refresh();self.assertIsNotNone(dlg.canvas.data)
        QTest.keyClick(dlg,Qt.Key.Key_Space,Qt.KeyboardModifier.ControlModifier);self.assertEqual(panics,[True])
        dlg.hide();app.processEvents();self.assertTrue(source.stopped);self.assertTrue(source.deleted)
        self.assertIsNone(dlg.source);self.assertIsNone(dlg.canvas.data)
        dlg.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()

if __name__=='__main__':unittest.main()
