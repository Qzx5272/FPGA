import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from performance_recording import Recorder,Playback,validate,save,load
from protocol import Event,Decoder
from score_tools import articulate,section,History
from score import load as load_score


class Takes(unittest.TestCase):
    def test_held_snapshot_final_release_and_clock(self):
        r=Recorder();r.start(10,{'master':80},None,[Event(0,serial=5)])
        r.capture(Event(11,flags=0,parameter=80),10.2)
        take=r.stop(10.5)
        self.assertEqual([e['event']['kind'] for e in take['events']],[0,11,1])
        self.assertEqual(take['events'][-1]['at_us'],500000)
        p=Playback();p.start(take,20)
        self.assertEqual(p.due(20)[0]['serial'],5)
        self.assertEqual(p.due(20.2)[0]['kind'],11)
        self.assertEqual(p.due(20.5)[0]['kind'],1)
        self.assertFalse(p.active)
    def test_bad_timestamps_rejected_without_partial_playback(self):
        r=Recorder();r.start(0,{},None);r.capture(Event(0),0);t=r.stop(1)
        bad=copy.deepcopy(t);bad['events'][0]['at_us']=2000000
        with self.assertRaises(ValueError):validate(bad)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'take.json';save(p,t);self.assertEqual(load(p),t)
    def test_capture_excludes_polls_and_ends_on_panic(self):
        r=Recorder();r.start(0,{},None);r.capture(Event(6),0);r.capture(Event(0,serial=4),.1);r.capture(Event(127),.2)
        self.assertEqual(len(r.stop(.3)['events']),2)
    def test_slow_consumer_keeps_all_due_events(self):
        r=Recorder();r.start(0,{},None)
        for i in range(40):r.capture(Event(11,parameter=i),i*.01)
        t=r.stop(1);p=Playback();p.start(t,0);events=[]
        while p.active:events+=p.due(2,limit=3)
        self.assertEqual(len(events),40)
    def test_source_release_and_panic_end_recorded_held_notes(self):
        r=Recorder();r.start(0,{},None)
        r.capture(Event(0,source=3,serial=9),0)
        r.capture(Event(2,source=3),.1)
        r.capture(Event(0,source=2,serial=10),.2)
        r.capture(Event(127),.3)
        take=r.stop(.4)
        self.assertEqual([e['event']['kind'] for e in take['events']],[0,2,0,127])


class ScoreTools(unittest.TestCase):
    def setUp(self):self.score=load_score(Path(__file__).resolve().parents[1]/'assets/confluence.json')
    def test_smooth_preserves_notes_and_intentional_phrase_rests(self):
        result=articulate(self.score)
        self.assertEqual([e for e in self.score['events'] if e['kind']==0],[e for e in result['events'] if e['kind']==0])
        self.assertEqual(len(result['events']),len(self.score['events']))
        self.assertNotEqual(result,self.score)
    def test_loop_clips_crossing_notes_and_carries_vowel(self):
        s=copy.deepcopy(self.score);loop=section(s,1,5)
        self.assertEqual(loop['duration_samples'],96000)
        self.assertTrue(all(0<=e['sample']<96000 for e in loop['events']))
        self.assertEqual(s,self.score)
    def test_history_is_independent(self):
        h=History();h.remember(self.score);edited=articulate(self.score)
        self.assertEqual(h.undo(edited),self.score);self.assertEqual(h.redo(self.score),edited)
    def test_midi_export_import_note_count_and_tempo(self):
        from midi_file import write_midi,read_midi
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'music.mid';write_midi(p,self.score)
            score=read_midi(p)
            self.assertEqual(sum(e['kind']==0 for e in score['events']),sum(e['kind']==0 for e in self.score['events']))


class WorkstationUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import QApplication
        cls.application=QApplication.instance() or QApplication([])
    def setUp(self):
        from app import Desk
        self.d=Desk();self.d.pump_timer.stop();self.d.beat_timer.stop()
        class Port:
            in_waiting=0
            def __init__(self):self.data=bytearray()
            def write(self,data):self.data.extend(data);return len(data)
            def read(self,n):return b''
            def close(self):pass
        self.d.port=Port();self.d.board_identity={'features':0x7c,'capacity':256,'build_id':0x20261028}
        self.d.states={6:dict(owner=1,epoch=5)}
        self.d.open_workstation();self.w=self.d.workstation;self.w.timer.stop()
    def tearDown(self):self.w.take=None;self.d.close()
    def test_competition_page_lists_every_tracked_item(self):
        labels=[self.w.requirements.item(row,0).text() for row in range(self.w.requirements.rowCount())]
        self.assertEqual(len(labels),11)
        self.assertTrue(all(any(label.startswith(code+' ·') for label in labels) for code in (f'O{i:02d}' for i in range(1,11))))
        self.assertTrue(any(label.startswith('产品项 ·') for label in labels))
        self.assertTrue(self.w.requirements.wordWrap())
    def test_external_controls_update_saved_scene_without_echo(self):
        self.d.queue.clear();self.w.mutes[3].setChecked(True);self.d.queue.clear()
        for event in (Event(10,parameter=37),Event(15,parameter=132),Event(7,flags=2,parameter=53),Event(11,part=6,flags=0,parameter=81)):
            self.d.observe_captured_control(event)
        state=self.d.capture_performance()
        self.assertEqual((state['master'],state['tempo'],state['wet'],state['effect_mode']),(37,132,53,2))
        self.assertEqual(state['patches'][6][0],81)
        self.assertTrue(self.w.mutes[3].isChecked());self.assertEqual(self.w.mixers[6].value(),81)
        self.assertFalse(self.d.queue)
    def test_preheld_hardware_note_is_seeded_at_record_start(self):
        note=Event(0,source=65,part=6,contact=3,serial=12,note=64,velocity=79)
        self.d.observe_captured_control(note);self.w.start_recording();self.w.stop_recording()
        notes=[e for e in self.w.take['events'] if e['event']['kind'] in (0,1)]
        self.assertEqual([e['event']['kind'] for e in notes],[0,1])
        self.assertEqual(notes[0]['at_us'],0);self.assertEqual(notes[0]['event']['velocity'],79)
        self.d.observe_captured_control(Event(1,source=65,part=6,contact=3,serial=11))
        self.assertTrue(self.d.captured_held)
        self.d.observe_captured_control(Event(1,source=65,part=6,contact=3,serial=12))
        self.assertFalse(self.d.captured_held)
    def test_known_capture_loss_blocks_new_take_until_panic(self):
        self.d.capture_uncertain=True;self.w.start_recording();self.assertFalse(self.w.recorder.active)
        self.d.panic();self.w.start_recording();self.assertTrue(self.w.recorder.active);self.w.stop_recording()
    def test_patch_editor_reopens_actual_saved_envelope(self):
        self.d.patch_values[6]={4:1024,5:11,6:8192,7:15};self.d.open_patch()
        self.assertAlmostEqual(self.d.patch_editor.attack.value(),65535/(1024*48),places=2)
        self.assertAlmostEqual(self.d.patch_editor.sustain.value(),8192*100/16383,places=2)
        self.assertGreater(self.d.patch_editor.release.value(),4700)
    def test_recording_captures_successful_send_not_poll(self):
        self.w.start_recording();self.d.press(210,60,88);self.d.pump();self.d.release(210);self.d.pump();self.w.stop_recording()
        notes=[e['event'] for e in self.w.take['events'] if e['event']['kind'] in (0,1)]
        self.assertEqual([e['kind'] for e in notes],[0,1]);self.assertEqual(notes[0]['velocity'],88)
    def test_replay_uses_current_authorization_not_saved_epoch(self):
        self.w.replay(dict(kind=0,source=1,part=6,contact=1,note=62,velocity=90,epoch=999,serial=300))
        self.d.pump();frames=Decoder().feed(bytes(self.d.port.data))
        note=next(f for f in frames if f[1]==0)
        self.assertEqual(int.from_bytes(note[8:12],'little'),5)
        self.assertNotEqual(int.from_bytes(note[12:16],'little'),300)
        self.w.stop_playback();self.assertFalse(self.d.held)
    def test_replay_waits_for_fresh_grant_before_short_notes(self):
        from unittest.mock import patch
        r=Recorder();r.start(0,{},None);r.capture(Event(0,part=6),0);self.w.take=r.stop(.02)
        with patch('workstation.time.monotonic',return_value=100):self.w.start_playback()
        self.assertFalse(self.w.player.active);self.assertIsNotNone(self.w.replay_wait)
        self.d.states[6]=dict(owner=1,epoch=12,_received=100.3)
        with patch('workstation.time.monotonic',return_value=100.35):self.w.tick()
        self.assertTrue(self.w.player.active)
        self.assertTrue(self.d.held)
        self.assertEqual(next(iter(self.d.held.values()))['epoch'],12)
    def test_solo_and_saved_mix_state(self):
        self.w.solos[2].setChecked(True);self.w.solos[4].setChecked(True)
        self.assertFalse(self.w.solos[2].isChecked());self.assertEqual(self.w.solo,4)
        self.w.mutes[5].setChecked(True)
        state=self.d.capture_performance();self.w.solos[4].setChecked(False)
        self.d.restore_performance(state)
        self.assertEqual(self.w.solo,4);self.assertTrue(self.w.mutes[5].isChecked())
    def test_hardware_capture_decodes_timestamp_and_source(self):
        from protocol import captured_event
        import struct,zlib
        raw=bytearray(Event(0,source=65,part=6,serial=8).encode()[2:30]);raw[1]=0xc0
        raw[16:24]=struct.pack('<Q',96000);data=bytes(raw)+struct.pack('<I',zlib.crc32(raw))
        event,ticks=captured_event(data);self.assertEqual((event.source,ticks),(65,96000))
        self.w.start_recording();self.w.capture_from_board(event,ticks)
        self.w.capture_from_board(Event(1,source=65,part=6,serial=8),ticks+4800)
        self.w.stop_recording();notes=self.w.take['events']
        self.assertEqual(notes[1]['at_us']-notes[0]['at_us'],100000)
        self.assertEqual(self.w.replay_source(65),4)
    def test_metronome_is_undoable_event_score(self):
        from score_tools import with_metronome,section
        from score import validate
        source=section(load_score(Path(__file__).resolve().parents[1]/'assets/confluence.json'),0,4)
        result=with_metronome(source);validate(result)
        self.assertEqual(len(result['events'])-len(source['events']),8)
    def test_extended_preset_does_not_send_to_legacy(self):
        self.d.board_identity['features']=0x3c
        self.w.presets.setCurrentIndex(self.w.presets.findData('bell'));self.w.apply_preset()
        self.assertEqual(self.d.part.currentIndex(),6)
    def test_midi_16_pads_preserves_velocity(self):
        self.d.seat_parts[1]=6
        for i in range(16):self.d.on_midi((1,[144,36+i,30+i]))
        self.assertEqual(len(self.d.held),16)
        self.assertEqual(sorted(x['velocity'] for x in self.d.held.values()),list(range(30,46)))
    def test_editor_grid_history_drag(self):
        self.d.open_editor();e=self.d.editor;e.loop_timer.stop();before=copy.deepcopy(e.score)
        e.grid.setCurrentIndex(1);e.edit(.125,61,False)
        self.assertTrue(any(n['sample']==3000 and n['note']==61 for n in e.score['events']))
        e.undo();self.assertEqual(e.score,before);e.redo();self.assertNotEqual(e.score,before)
    def test_clean_scene_unmutes_previous_board_mix_and_restores_effect(self):
        self.w.mutes[3].setChecked(True);self.w.effect.setChecked(True)
        self.d.restore_performance(dict(mixer=dict(muted=[],solo=None,bypass=False)))
        self.d.queue.clear();self.w.apply_mixer()
        commands=[e for e in self.d.queue if e.kind==4]
        self.assertEqual(len(commands),15)
        self.assertTrue(all(e.flags==3 for e in commands))
        self.assertTrue(any(e.kind==7 and e.parameter==self.d.wet.value() for e in self.d.queue))
    def test_capture_overflow_reads_body_not_crc_and_blocks_replay(self):
        import struct,zlib
        body=bytearray(28);body[:2]=bytes([4,0xdf]);body[24:28]=struct.pack('<I',7)
        wire=b'\xb4\x4b'+body+struct.pack('<I',zlib.crc32(body))
        self.d.port.in_waiting=len(wire);self.d.port.read=lambda n:wire
        self.w.start_recording();self.d.pump()
        self.assertEqual(self.w.take.get('capture_incomplete'),True)
        self.assertIn('7 条',self.w.status.text());self.w.start_playback()
        self.assertFalse(self.w.player.active)
    def test_physical_panic_capture_and_source_release_replay(self):
        from protocol import captured_event
        import struct,zlib
        raw=bytearray(Event(127).encode()[2:30]);raw[1]=0xe0;raw[16:24]=struct.pack('<Q',48000)
        e,t=captured_event(bytes(raw)+struct.pack('<I',zlib.crc32(raw)))
        self.assertEqual((e.kind,t),(127,48000))
        self.w.replay(dict(kind=0,source=1,part=6,serial=8));self.d.pump()
        self.w.replay(dict(kind=2,source=1))
        self.assertFalse(self.d.held);self.assertFalse(self.w.replay_contacts)
    def test_poly_aftertouch_is_track_expression_and_native_rejects_pan(self):
        self.d.on_midi((1,[160,60,91]))
        self.assertTrue(any(e.kind==11 and e.flags==0 and e.parameter==91 for e in self.d.queue))
        self.d.queue.clear();self.w.pan(6,20);self.assertFalse(self.d.queue)
    def test_onboard_library_requires_capability_and_status_is_polled(self):
        self.w.select_onboard_song();self.assertFalse(any(e.kind==20 for e in self.d.queue))
        self.d.board_identity['features']|=2048;self.w.onboard_songs.setCurrentIndex(1)
        self.w.select_onboard_song();self.w.tick()
        self.assertTrue(any(e.kind==20 and e.parameter==1 for e in self.d.queue))
        self.assertTrue(any(e.kind==21 for e in self.d.queue))


if __name__=='__main__':unittest.main()
