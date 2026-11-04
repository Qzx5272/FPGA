import sys,os,json,copy,unittest,tempfile
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
band=Path(__file__).resolve().parents[1];sys.path.insert(0,str(band/'host'))
from app import QApplication,Desk
from protocol import Decoder,Event,UART_GUARD_BYTES
import score
class Port:
    def __init__(self):self.data=bytearray();self.in_waiting=0
    def write(self,b):self.data.extend(b);return len(b)
    def read(self,n):return b''
    def close(self):pass
class HostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.d=Desk();self.d.pump_timer.stop();self.d.beat_timer.stop();self.p=Port();self.d.port=self.p
        self.d.states={6:dict(owner=1,epoch=2),0:dict(owner=2,epoch=3)}
    def tearDown(self):self.d.close()
    def packets(self):return Decoder().feed(bytes(self.p.data))
    def test_editor_final_partial_measure_survives_save_and_upload(self):
        from unittest.mock import patch
        from editor import ScoreEditor
        editor=ScoreEditor(self.d)
        try:
            project=dict(format='starcluster-score-1',sample_rate=48000,bpm=120,
                duration_samples=108000,events=[
                    dict(sample=0,kind=0,part=6,note=60,velocity=90,serial=1),
                    dict(sample=24000,kind=1,part=6,note=60,velocity=0,serial=1)])
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'partial.json';score.save(path,project)
                with patch('editor.QFileDialog.getOpenFileName',return_value=(str(path),'')),patch('editor.QMessageBox.warning') as warning:
                    editor.open();warning.assert_not_called()
                self.assertEqual(editor.bar.maximum(),2)
                editor.bar.setValue(2);editor.part.setCurrentIndex(6)
                editor.edit(0,67,False)
                tail=[e for e in editor.score['events'] if e['note']==67]
                self.assertEqual([e['sample'] for e in tail],[96000,107999])
                before=copy.deepcopy(editor.score)
                editor.edit(1,69,False)  # Beyond the final partial measure.
                self.assertEqual(editor.score,before)
                score.save(path,editor.score);restored=score.load(path)
                self.assertEqual(restored,editor.score)
                self.assertEqual(list(score.upload_events(restored)),list(score.upload_events(editor.score)))
                for duration,count in ((96000,1),(96001,2),(192000,2)):
                    editor.score['duration_samples']=duration
                    self.assertEqual(editor.measure_count(),count)
        finally:editor.close()
    def test_editor_shared_export_preserves_captured_presets(self):
        from unittest.mock import patch
        from editor import ScoreEditor
        editor=ScoreEditor(self.d)
        try:
            with patch('editor.QMessageBox.warning') as warning,patch('editor.QFileDialog.getExistingDirectory') as choose:
                editor.export_offline(shared=True)
                warning.assert_called_once();choose.assert_not_called()
            editor.profile.setCurrentIndex(1)
            with tempfile.TemporaryDirectory() as directory:
                with patch.object(self.d,'capture_performance',return_value={'patches':{'7':{'0':44},'15':{'0':63}},'collaboration':False}),patch('editor.QFileDialog.getExistingDirectory',return_value=directory),patch('editor.QMessageBox.warning') as warning:
                    editor.export_offline(shared=True);warning.assert_not_called()
                target=Path(directory)
                manifest=json.loads((target/'export_manifest.json').read_text(encoding='utf-8'))
                self.assertEqual(manifest['voice_allocation'],'shared256-central-parameters')
                self.assertIn('singer_expression<=63;', (target/'rtl/band_singer_core.sv').read_text())
                self.assertIn("4'd7:offline_parameter_0=16'd44;",(target/'rtl/offline_patch_defaults.vh').read_text())
                self.assertIn('offline_parameter_0(i)',(target/'rtl/shared_role_controls.v').read_text())
        finally:editor.close()
    def test_singer_project_profile_roundtrip_and_wrong_target_rejection(self):
        from offline import export_project
        project=dict(format='starcluster-score-2',sample_rate=48000,bpm=120,duration_samples=48000,
            engine_profile='singer-v1',events=[dict(sample=0,kind=0,part=15,note=60,velocity=90,serial=1),dict(sample=24000,kind=1,part=15,note=60,velocity=0,serial=1)],performance={'patches':{'15':{'0':64}}})
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'song.json';score.save(path,project);self.assertEqual(score.load(path),project)
            target=Path(directory)/'offline'
            export_project(project,target,autoplay=True)
            self.assertEqual(json.loads((target/'project.json').read_text(encoding='utf-8')),project)
            self.assertTrue((target/'rtl/offline_singer_top.sv').exists())
            self.assertTrue((target/'coeffs.mem').exists())
            self.assertFalse((target/'constraints/microphone.cst').exists())
            self.assertEqual(json.loads((target/'export_manifest.json').read_text())['engine_profile'],'singer-v1')
            self.assertIn('singer_expression<=64;', (target/'rtl/band_singer_core.sv').read_text())
        self.d.board_identity={'features':0};self.d.upload_score(project)
        self.assertIsNone(self.d.upload_generator);self.assertFalse(self.d.await_upload)
        self.d.board_identity={'features':32};self.d.upload_score(project);self.assertTrue(self.d.await_upload)
        self.assertEqual(next(self.d.upload_generator).kind,13)
        legacy=copy.deepcopy(project);legacy.pop('engine_profile');legacy['format']='starcluster-score-1'
        with self.assertRaises(ValueError):score.validate_target(legacy,None)
        with self.assertRaises(ValueError):score.validate_target(legacy,32)
        score.validate_target(legacy,0)
        unsupported=copy.deepcopy(project);unsupported['performance']['patches']['15']['1']=8192
        with self.assertRaises(ValueError):score.validate(unsupported)
    def test_editor_singer_profile_is_explicit_and_rejects_incompatible_vowels(self):
        from editor import ScoreEditor
        editor=ScoreEditor(self.d);editor.profile.setCurrentIndex(1)
        self.assertEqual(editor.score['engine_profile'],'singer-v1');self.assertIn('电子歌手',editor.part.itemText(15))
        editor.profile.setCurrentIndex(0);editor.score['events'].insert(0,dict(sample=0,kind=2,part=15,note=0,velocity=0,serial=999999))
        editor.profile.setCurrentIndex(1)
        self.assertEqual(editor.profile.currentIndex(),0);self.assertEqual(editor.score['engine_profile'],'band-v1');editor.close()
    def test_singer_controls_only_advertise_supported_expression(self):
        self.d.board_identity={'features':32};self.d.part.setCurrentIndex(15)
        self.assertFalse(self.d.bend.isEnabled());self.assertFalse(self.d.vowel.isEnabled());self.assertFalse(self.d.patch_button.isEnabled())
        self.assertTrue(self.d.expression.isEnabled())
        self.d.queue.clear();self.d.parameter(1,9000);self.d.parameter(2,3);self.assertEqual(len(self.d.queue),0)
        self.d.parameter(0,64);self.assertEqual(len(self.d.queue),1);self.assertEqual(self.d.queue[0].part,15)
        self.d.part.setCurrentIndex(6);self.assertTrue(self.d.bend.isEnabled());self.assertTrue(self.d.patch_button.isEnabled())
        self.d.part.setCurrentIndex(15);self.d.board_identity={'features':0};self.d.refresh_role_controls();self.assertTrue(self.d.bend.isEnabled())
    def test_singer_capability_crc_poll_and_expiration(self):
        import struct,zlib,time
        body=struct.pack('<4B6I',4,162,1,60,1,2,3,4,0,0)
        raw=b'\xb4\x4b'+body+struct.pack('<I',zlib.crc32(body))
        def deliver(data):
            self.p.in_waiting=len(data);self.p.read=lambda n:data
            self.d.pump();self.p.in_waiting=0;self.p.read=lambda n:b''
        self.d.board_identity={'features':0};deliver(raw)
        self.assertIsNone(self.d.singer_snapshot)
        self.d.board_identity={'features':32};deliver(raw)
        self.assertEqual(self.d.singer_snapshot,dict(gate=True,note=60,dropped=1,stale_off=2,dac_dropped=3,dac_underruns=4))
        self.assertIn('保持音符 60',self.d.singer_label.text())
        self.assertEqual(self.d.role_name(15),'电子歌手')
        stamp=self.d.singer_received;deliver(raw[:-1]+bytes([raw[-1]^1]));self.assertEqual(self.d.singer_received,stamp)
        self.d.queue.clear();self.d.heartbeat();self.assertTrue(any(e.kind==19 for e in self.d.queue))
        self.d.queue.clear();self.d.board_identity={'features':0};self.d.heartbeat();self.assertFalse(any(e.kind==19 for e in self.d.queue))
        self.assertIn('已过期',self.d.singer_label.text())
        self.d.singer_received=time.monotonic()-3;self.d.refresh_singer();self.assertIn('已过期',self.d.singer_label.text())
        self.d.singer_received=time.monotonic();self.d.port=None;self.d.refresh_singer();self.assertIn('已过期',self.d.singer_label.text())
    def test_vowel_phrase_orders_articulation_and_restores_prior_vowel(self):
        original=score.load(band/'assets/confluence.json')
        original['events']=[e for e in original['events'] if e['part']!=7]
        original['events'].insert(0,dict(sample=0,kind=2,part=7,note=3,velocity=0,serial=90000))
        before=copy.deepcopy(original)
        result=score.insert_vowel_phrase(original,24000,[(0,60,24000),(2,64,24000)],80)
        self.assertEqual(original,before)
        choir=[e for e in result['events'] if e['part']==7]
        self.assertEqual([(e['sample'],e['kind'],e['note']) for e in choir],[(0,2,3),(24000,2,0),(24000,0,60),(45600,1,60),(48000,2,2),(48000,0,64),(69600,1,64),(72000,2,3)])
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'phrase.json';score.save(p,result);self.assertEqual(score.load(p),result)
        self.assertEqual(len(list(score.upload_events(result))),len(result['events'])*3+3)
        with self.assertRaises(ValueError):score.insert_vowel_phrase(result,30000,[(0,60,24000)])
        with self.assertRaises(ValueError):score.insert_vowel_phrase(original,original['duration_samples']-24000,[(0,60,24000)])
        self.assertEqual(original,before)
    def test_phrase_restores_saved_patch_vowel_without_prior_marker(self):
        original=score.load(band/'assets/confluence.json')
        original['events']=[e for e in original['events'] if e['part']!=7]
        original.setdefault('performance',{}).setdefault('patches',{})['7']={'2':4}
        result=score.insert_vowel_phrase(original,24000,[(0,60,24000)])
        restored=[e for e in result['events'] if e['part']==7 and e['sample']==48000]
        self.assertEqual([(e['kind'],e['note']) for e in restored],[(2,4)])
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'phrase.json';score.save(p,result)
            self.assertEqual(list(score.upload_events(score.load(p))),list(score.upload_events(result)))
        original['events'].insert(0,dict(sample=0,kind=2,part=7,note=1,velocity=0,serial=90000))
        changed=score.insert_vowel_phrase(original,24000,[(0,60,24000)])
        self.assertEqual([e['note'] for e in changed['events'] if e['part']==7 and e['sample']==48000],[1])
    def test_phrase_editor_inserts_four_notes_in_empty_choir_bar(self):
        from editor import ScoreEditor
        editor=ScoreEditor(self.d)
        editor.score['events']=[e for e in editor.score['events'] if e['part']!=7]
        editor.insert_phrase()
        self.assertEqual([e['note'] for e in editor.score['events'] if e['kind']==0 and e['part']==7],[60,64,67,72])
        self.assertEqual(editor.part.currentIndex(),7);score.validate(editor.score);editor.close()
    def test_stage_expiration_is_per_track_and_disconnect_hides_values(self):
        from stage import StageState,owner_text
        model=StageState()
        model.update(dict(profile='band',part=0,owner=17),10)
        model.update(dict(profile='band',part=1,owner=2),12)
        snap=model.snapshot(13,True)
        self.assertTrue(snap['live']);self.assertIsNone(snap['owners'][0]);self.assertEqual(snap['owners'][1],2)
        self.assertEqual(owner_text(17),'本地演奏席 1')
        self.assertFalse(model.snapshot(13,False)['live']);self.assertEqual(model.snapshot(13,False)['owners'],[None]*16)
        model.reset();self.assertIsNone(model.snapshot(13,True)['latest'])
    def test_identity_retry_is_rate_limited_and_stops_after_reply(self):
        from unittest.mock import patch
        self.d.identity_requested=10
        with patch('app.time.monotonic',return_value=10.4):self.d.heartbeat()
        self.assertFalse(any(e.kind==18 for e in self.d.queue));self.d.queue.clear()
        with patch('app.time.monotonic',return_value=10.6):self.d.heartbeat()
        self.assertEqual(sum(e.kind==18 for e in self.d.queue),1);self.d.queue.clear()
        self.d.board_identity=dict(build_id=1)
        with patch('app.time.monotonic',return_value=20):self.d.heartbeat()
        self.assertFalse(any(e.kind==18 for e in self.d.queue))
    def test_stage_poll_covers_all_tracks_and_yields_to_upload_and_backlog(self):
        self.d.board_identity=dict(build_id=1)
        self.d.open_stage();self.d.stage_view.timer.stop();self.d.queue.clear()
        for _ in range(8):self.d.heartbeat()
        # A blocked sender must stop projection polling, not grow it unbounded.
        self.assertLessEqual(len(self.d.queue),16)
        self.d.queue.clear();self.d.stage_poll_part=0
        observed=[]
        for _ in range(8):
            self.d.heartbeat();observed.extend(list(self.d.queue)[-2:]);self.d.queue.clear()
        self.assertEqual([e.part for e in observed],list(range(16)))
        self.assertTrue(all(e.kind==6 and e.source==self.d.source() for e in observed))
        self.d.await_upload=True;before=self.d.stage_poll_part;self.d.heartbeat()
        self.assertEqual(self.d.stage_poll_part,before)
        self.d.stage_view.close()
    def test_stage_accepts_crc_checked_board_frames_only(self):
        import struct,zlib
        body=struct.pack('<8BIIIII',4,129,18,7,12,0,142,0,3,48000,0,0,0)
        frame=b'\xb4\x4b'+body+struct.pack('<I',zlib.crc32(body))
        class ReceivingPort(Port):
            def __init__(self,data):super().__init__();self.rx=data;self.in_waiting=len(data)
            def read(self,n):data=self.rx;self.rx=b'';self.in_waiting=0;return data
        bad=bytearray(frame);bad[-1]^=1
        self.d.port=ReceivingPort(bytes(bad));self.d.pump()
        self.assertIsNone(self.d.stage_state.latest)
        self.d.port=ReceivingPort(frame);self.d.pump()
        self.assertEqual(self.d.stage_state.latest['voices'],12)
        self.assertEqual(self.d.stage_state.tracks[7][0]['owner'],18)
    def test_release_identity_survives_role_and_key_change(self):
        self.d.press(208,60,100);self.d.pump();self.d.part.setCurrentIndex(4);self.d.root.setCurrentIndex(9);self.d.release(208);self.d.pump()
        notes=[p for p in self.packets() if p[1] in(0,1)]
        self.assertEqual([p[1] for p in notes],[0,1]);self.assertEqual(notes[0][2:6],notes[1][2:6]);self.assertEqual(notes[0][8:16],notes[1][8:16])
    def test_two_seats_and_learning_do_not_swallow_other_seat_release(self):
        self.d.on_midi((2,[144,60,100]));self.d.pump();self.assertIn((2,0),self.d.held)
        self.d.learn();self.d.on_midi((2,[128,60,0]));self.d.pump();self.assertNotIn((2,0),self.d.held)
        self.assertTrue(any(p[1]==1 and p[2]==2 for p in self.packets()))
    def test_per_seat_mapping_learning_and_legacy_roundtrip(self):
        from unittest.mock import patch
        self.d.seat_mappings={1:{60:7}}
        self.d.seat.setValue(2);self.d.learn()
        with patch('app.save_maps') as save:
            for note in range(60,68):self.d.on_midi((2,[144,note,100]))
            save.assert_called_once()
        self.assertEqual(self.d.seat_mappings[1],{60:7})
        self.assertEqual(self.d.seat_mappings[2][60],0)
        self.d.seat_parts[2]=4
        with patch.object(self.d,'press') as press:
            self.d.on_midi((1,[144,60,100]));self.d.on_midi((2,[144,60,100]))
            self.assertEqual(press.call_args_list[0].args[1],self.d.scale_note(7))
            self.assertEqual(press.call_args_list[1].args[1],self.d.scale_note(0))
        saved=json.loads(json.dumps(self.d.capture_performance()))
        project=score.load(band/'assets/confluence.json');project['performance']=saved
        score.validate(project)
        self.d.seat_mappings={};self.d.restore_performance(saved)
        self.assertEqual(self.d.seat_mappings[1],{60:7})
        legacy=dict(saved);legacy.pop('seat_pad_mappings');self.d.restore_performance(legacy)
        self.assertEqual(self.d.seat_mappings,{})
        bad=copy.deepcopy(project);bad['performance']['seat_pad_mappings']={'5':{'60':0}}
        with self.assertRaises(ValueError):score.validate(bad)

    def test_pad_map_atomic_save_and_invalid_inputs(self):
        from pad_mapping import save_maps,read_maps,normalize_seats,normalize_mapping
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'map.json';path.write_text('{"60": 0}')
            self.assertEqual(read_maps(path),({60:0},{}))
            save_maps(path,{60:0},{1:{60:7},2:{60:0}})
            self.assertEqual(read_maps(path)[1],{1:{60:7},2:{60:0}})
            before=path.read_bytes()
            with patch('pad_mapping.os.replace',side_effect=OSError('disk')):
                with self.assertRaises(OSError):save_maps(path,{61:0},{})
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(len(list(Path(td).iterdir())),1)
        for bad in ({'60':8},{'128':0},{True:0},{'60':0,60:1},[]):
            with self.assertRaises(ValueError):normalize_mapping(bad)
        with self.assertRaises(ValueError):normalize_seats({'1':{60:0},1:{61:0}})

    def test_midi_reconnect_generation_and_failed_replacement(self):
        from unittest.mock import patch,Mock
        devices=[]
        class Device:
            def __init__(self):self.opened=False;self.callback=None;self.closed=False;devices.append(self)
            def get_ports(self):return ['Pad A','Pad B']
            def open_port(self,index):self.opened=True
            def is_port_open(self):return self.opened
            def set_callback(self,callback):self.callback=callback
            def cancel_callback(self):pass # Simulate an already queued callback.
            def close_port(self):self.closed=True;self.opened=False
        self.d.midi_ports.clear();self.d.midi_ports.addItems(['Pad A','Pad B'])
        with patch('app.rtmidi',Mock(MidiIn=Device)):
            self.d.connect_midi();old=devices[-1];generation=self.d.midi_generations[1]
            self.d.seat.setValue(2);self.d.connect_midi()
            self.assertNotIn(2,self.d.midis);self.assertEqual(len(devices),1)
            self.d.seat.setValue(1);self.d.midi_ports.setCurrentIndex(1)
            with patch.object(Device,'open_port',side_effect=OSError('unavailable')):
                self.d.connect_midi()
            self.assertIs(self.d.midis[1][0],old);self.assertFalse(old.closed)
            self.d.connect_midi();new=devices[-1];self.assertTrue(old.closed)
            with patch.object(self.d,'press') as press:
                old.callback(([144,60,100],0));self.assertFalse(press.called)
                new.callback(([144,60,100],0));self.assertTrue(press.called)
            self.assertGreater(self.d.midi_generations[1],generation)
            self.d.on_midi((1,[176,64,127]));self.assertIn((1,0),self.d.midi_sustain)
            new.get_ports=lambda:[]
            self.d.heartbeat();self.assertNotIn(1,self.d.midis)
            self.assertNotIn((1,0),self.d.midi_sustain)
            with patch.object(self.d,'press') as press:
                new.callback(([144,60,100],0));self.assertFalse(press.called)

    def test_midi_enumeration_failure_releases_only_failed_seat(self):
        from unittest.mock import Mock
        failed=Mock();failed.get_ports.side_effect=OSError('USB removed')
        good=Mock();good.get_ports.return_value=['B'];good.is_port_open.return_value=True
        self.d.midis={1:(failed,'A'),2:(good,'B')};self.d.midi_generations={1:1,2:1}
        self.d.on_midi((1,[144,60,100]));self.d.on_midi((2,[144,60,100]))
        self.d.heartbeat()
        self.assertNotIn(1,self.d.midis);self.assertIn(2,self.d.midis)
        self.assertFalse(any(s==1 for s,c in self.d.held))
        self.assertTrue(any(s==2 for s,c in self.d.held))
        self.assertTrue(any(e.kind==2 and e.source==1 for e in self.d.queue))
        self.d.port=None;good.get_ports.side_effect=OSError('removed while offline')
        self.d.heartbeat();self.assertEqual(self.d.midis,{})
        self.assertFalse(self.d.held)

    def test_panic_discards_parameter_backlog(self):
        self.d.queue.extend(Event(11,flags=0,parameter=i) for i in range(100));self.d.panic();self.d.pump()
        self.assertEqual([p[1] for p in self.packets()],[127])
    def test_editor_full_stage_export_and_role_guard(self):
        from unittest.mock import patch
        from editor import ScoreEditor
        editor=ScoreEditor(self.d)
        with patch('editor.QMessageBox.warning') as warning,patch('editor.QFileDialog.getExistingDirectory') as choose:
            editor.export_offline(stage=True);warning.assert_called_once();choose.assert_not_called()
        editor.profile.setCurrentIndex(1)
        with tempfile.TemporaryDirectory() as directory:
            with patch('editor.QFileDialog.getExistingDirectory',return_value=directory),patch('editor.QMessageBox.warning') as warning:
                editor.export_offline(stage=True);warning.assert_not_called()
            manifest=json.loads((Path(directory)/'export_manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['hardware_profile'],'stage-v1');self.assertTrue(manifest['autoplay'])
            self.assertTrue((Path(directory)/'rtl/offline_stage_top.sv').exists())
            self.assertEqual(json.loads((Path(directory)/'project.json').read_text(encoding='utf-8'))['performance'],json.loads(json.dumps(self.d.capture_performance())))
            self.assertIn('stage.cst',(Path(directory)/'build.tcl').read_text())
        editor.close()
    def test_editor_combined_workstation_export(self):
        from unittest.mock import patch
        from editor import ScoreEditor
        import hashlib
        editor=ScoreEditor(self.d)
        with patch('editor.QMessageBox.warning') as warning,patch('editor.QFileDialog.getExistingDirectory') as choose:
            editor.export_offline(workstation=True);warning.assert_called_once();choose.assert_not_called()
        editor.profile.setCurrentIndex(1)
        with tempfile.TemporaryDirectory() as directory:
            with patch('editor.QFileDialog.getExistingDirectory',return_value=directory),patch('editor.QMessageBox.warning') as warning:
                editor.export_offline(workstation=True);warning.assert_not_called()
            root=Path(directory);manifest=json.loads((root/'export_manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['hardware_profile'],'workstation-i2s-spectrum-v1')
            self.assertTrue(manifest['autoplay'])
            self.assertEqual(json.loads((root/'project.json').read_text(encoding='utf-8'))['performance'],json.loads(json.dumps(self.d.capture_performance())))
            for name,digest in manifest['sources'].items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)
            self.assertNotIn('"HP_BCK"',(root/'constraints/board.cst').read_text())
            self.assertTrue((root/'hann_2048.mem').exists())
            self.assertIn('offline_workstation_top',(root/'build.tcl').read_text())
        editor.close()
    def test_editor_logical_video_export(self):
        from unittest.mock import patch
        from editor import ScoreEditor
        import hashlib
        editor=ScoreEditor(self.d)
        with patch('editor.QMessageBox.warning') as warning,patch('editor.QFileDialog.getExistingDirectory') as choose:
            editor.export_offline(video=True);warning.assert_called_once();choose.assert_not_called()
        editor.profile.setCurrentIndex(1)
        with tempfile.TemporaryDirectory() as directory:
            with patch('editor.QFileDialog.getExistingDirectory',return_value=directory),patch('editor.QMessageBox.warning') as warning:
                editor.export_offline(video=True);warning.assert_not_called()
            root=Path(directory);manifest=json.loads((root/'export_manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['hardware_profile'],'workstation-i2s-rgb-v1')
            self.assertTrue(manifest['autoplay'])
            self.assertEqual(json.loads((root/'project.json').read_text(encoding='utf-8'))['performance'],json.loads(json.dumps(self.d.capture_performance())))
            for name,digest in manifest['sources'].items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)
            self.assertNotIn('"HP_BCK"',(root/'constraints/board.cst').read_text())
            self.assertTrue((root/'hann_2048.mem').exists())
            self.assertIn('offline_workstation_top',(root/'build.tcl').read_text())
        editor.close()
    def test_editor_clocked_dvi_export(self):
        from unittest.mock import patch
        from editor import ScoreEditor
        import hashlib
        editor=ScoreEditor(self.d)
        with patch('editor.QMessageBox.warning') as warning,patch('editor.QFileDialog.getExistingDirectory') as choose:
            editor.export_offline(dvi=True);warning.assert_called_once();choose.assert_not_called()
        editor.profile.setCurrentIndex(1)
        with tempfile.TemporaryDirectory() as directory:
            with patch('editor.QFileDialog.getExistingDirectory',return_value=directory),patch('editor.QMessageBox.warning') as warning:
                editor.export_offline(dvi=True);warning.assert_not_called()
            root=Path(directory);manifest=json.loads((root/'export_manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['hardware_profile'],'workstation-i2s-dvi-v1')
            self.assertTrue(manifest['autoplay'])
            self.assertEqual(json.loads((root/'project.json').read_text(encoding='utf-8'))['performance'],json.loads(json.dumps(self.d.capture_performance())))
            for name,digest in manifest['sources'].items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)
            self.assertNotIn('"HP_BCK"',(root/'constraints/board.cst').read_text())
            self.assertTrue((root/'hann_2048.mem').exists())
            self.assertIn('offline_workstation_top',(root/'build.tcl').read_text())
        editor.close()
    def test_editor_onboard_pt8211_dvi_export(self):
        from unittest.mock import patch
        from editor import ScoreEditor
        import hashlib
        editor=ScoreEditor(self.d)
        with patch('editor.QMessageBox.warning') as warning,patch('editor.QFileDialog.getExistingDirectory') as choose:
            editor.export_offline(pt8211_dvi=True);warning.assert_called_once();choose.assert_not_called()
        editor.profile.setCurrentIndex(1)
        with tempfile.TemporaryDirectory() as directory:
            with patch('editor.QFileDialog.getExistingDirectory',return_value=directory),patch('editor.QMessageBox.warning') as warning:
                editor.export_offline(pt8211_dvi=True);warning.assert_not_called()
            root=Path(directory);manifest=json.loads((root/'export_manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['hardware_profile'],'workstation-pt8211-dvi-v1')
            self.assertTrue(manifest['autoplay'])
            self.assertEqual(json.loads((root/'project.json').read_text(encoding='utf-8'))['performance'],json.loads(json.dumps(self.d.capture_performance())))
            for name,digest in manifest['sources'].items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)
            self.assertIn('"HP_BCK"',(root/'constraints/board.cst').read_text())
            self.assertTrue((root/'hann_2048.mem').exists())
            self.assertIn('offline_workstation_top',(root/'build.tcl').read_text())
        editor.close()
    def test_sustain_isolated_by_seat_and_channel(self):
        self.d.on_midi((1,[176,64,127]))
        for source,channel,note in [(1,0,60),(1,1,62),(2,0,36)]:
            self.d.on_midi((source,[144+channel,note,100]))
            self.d.on_midi((source,[128+channel,note,0]))
        self.assertEqual(self.d.midi_deferred,{(1,0,60)})
        self.assertEqual(len(self.d.held),1)
        self.d.on_midi((1,[177,64,0]));self.assertEqual(len(self.d.held),1)
        self.d.on_midi((1,[176,64,0]));self.assertFalse(self.d.held or self.d.midi_deferred or self.d.midi_contacts)
    def test_sustain_retrigger_has_new_serial_and_balanced_releases(self):
        self.d.on_midi((1,[176,64,64]));self.d.on_midi((1,[144,60,100]));self.d.pump()
        first=next(iter(self.d.held.values()))['serial']
        self.d.on_midi((1,[128,60,0]));self.d.pump()
        self.assertFalse(any(p[1]==1 for p in self.packets()))
        self.d.on_midi((1,[144,60,100]));self.d.pump();self.d.pump()
        second=next(iter(self.d.held.values()))['serial'];self.assertNotEqual(first,second)
        self.d.on_midi((1,[144,60,0]));self.d.on_midi((1,[176,64,63]));self.d.pump()
        notes=[p for p in self.packets() if p[1] in (0,1)]
        self.assertEqual([(p[1],int.from_bytes(p[12:16],'little')) for p in notes],[(0,first),(1,first),(0,second),(1,second)])
    def test_emergency_and_disconnect_clear_pedal_state(self):
        for action in (self.d.panic,lambda:self.d.release_all(1),self.d.disconnect_port):
            self.d.on_midi((1,[176,64,127]));self.d.on_midi((1,[144,60,100]));self.d.on_midi((1,[128,60,0]))
            action();self.assertFalse(self.d.midi_sustain or self.d.midi_deferred or self.d.midi_contacts or self.d.held)
    def test_disconnect_retires_upload_and_prioritizes_seat_release(self):
        from unittest.mock import patch
        self.d.press(208,60,100)
        self.d.queue.extend(Event(11,flags=0,parameter=i) for i in range(100))
        self.d.upload_generator=iter([Event(13,flags=2)]);self.d.await_upload=True
        self.d.midi_contacts[(1,60)]=0
        self.d.connect_port()
        self.assertEqual([(p[1],p[2]) for p in self.packets()],[(2,1),(2,2),(2,3),(2,4)])
        self.assertIsNone(self.d.port);self.assertIsNone(self.d.upload_generator)
        self.assertFalse(self.d.await_upload or self.d.held or self.d.queue or self.d.states or self.d.midi_contacts)
        new_port=Port()
        with patch('app.serial.Serial',return_value=new_port):self.d.connect_port()
        self.d.pump()
        self.assertEqual([p[1] for p in Decoder().feed(new_port.data)],[18])
    def test_io_failure_cancels_upload_even_when_close_fails(self):
        class BrokenPort(Port):
            def write(self,b):raise IOError('removed')
            def close(self):raise IOError('already removed')
        self.d.port=BrokenPort();self.d.upload_generator=iter([Event(13,flags=2)]);self.d.await_upload=True
        self.d.pump()
        self.assertIsNone(self.d.port);self.assertIsNone(self.d.upload_generator)
        self.assertFalse(self.d.await_upload or self.d.queue or self.d.states)
        self.assertIn('removed',self.d.info.text())
    def test_project_roundtrip_and_validation(self):
        s=score.load(band/'assets/confluence.json');self.d.parameter(4,128);s['performance']=self.d.capture_performance()
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'work.json';score.save(p,s);loaded=score.load(p);self.d.restore_performance(loaded['performance'])
        self.assertEqual(self.d.patch_values[6][4],128)
        bad=copy.deepcopy(s);bad['performance']['patches']={6:{7:100}}
        with self.assertRaises(ValueError):score.validate(bad)
    def test_failed_crc_is_rejected(self):
        data=bytearray(Event(6).encode());data[8]^=1;d=Decoder();self.assertEqual(d.feed(data),[]);self.assertEqual(d.bad_crc,1)
    def test_vowel_composition_roundtrip_and_atomic_failure(self):
        from editor import ScoreEditor
        editor=ScoreEditor(self.d);before=copy.deepcopy(editor.score)
        editor.vowel_position.setCurrentIndex(3);editor.vowel_choice.setCurrentIndex(4);editor.edit_vowel()
        sample=18000
        markers=[e for e in editor.score['events'] if e['kind']==2 and e['sample']==sample and e['part']==7]
        self.assertEqual(len(markers),1);self.assertEqual(markers[0]['note'],4)
        self.assertEqual([e for e in before['events'] if e['kind']!=2],[e for e in editor.score['events'] if e['kind']!=2])
        editor.vowel_choice.setCurrentIndex(1);editor.edit_vowel()
        self.assertEqual(len([e for e in editor.score['events'] if e['kind']==2 and e['sample']==sample]),1)
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'vowels.json';score.save(path,editor.score);self.assertEqual(score.load(path),editor.score)
            from offline import export_project
            target=export_project(editor.score,Path(t)/'offline',autoplay=True)
            saved=json.loads((target/'project.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['events'],editor.score['events'])
            self.assertIn('song_rom[', (target/'rtl/song_events.vh').read_text())
        snapshot=copy.deepcopy(editor.score)
        with self.assertRaises(ValueError):score.edit_vowel(editor.score,editor.score['duration_samples'],2)
        self.assertEqual(editor.score,snapshot)
        editor.edit_vowel(True)
        self.assertFalse(any(e['kind']==2 and e['sample']==sample and e['part']==7 for e in editor.score['events']))
        self.assertEqual(len(list(score.upload_events(editor.score))),3*len(editor.score['events'])+3)
        editor.close()
    def test_note_erase_preserves_other_pitch_and_vowel_identity(self):
        from editor import ScoreEditor
        editor=ScoreEditor(self.d);editor.part.setCurrentIndex(7)
        editor.score['events']=[dict(sample=0,kind=2,part=7,note=0,velocity=0,serial=1)]
        for pitch in (60,64):
            editor.score['events'] += [dict(sample=0,kind=0,part=7,note=pitch,velocity=90,serial=1),dict(sample=24000,kind=1,part=7,note=pitch,velocity=0,serial=1)]
        editor.score['events'].sort(key=lambda e:e['sample']);score.validate(editor.score)
        editor.edit(0,60,True);score.validate(editor.score)
        self.assertEqual(len(editor.score['events']),3)
        self.assertEqual([e['note'] for e in editor.score['events'] if e['kind']!=2],[64,64])
        self.assertEqual(len([e for e in editor.score['events'] if e['kind']==2]),1)
        editor.close()
    def test_pressure_calibration_fit_persistence_and_wire(self):
        from calibration_model import fit,pressure,events,normalize
        from calibration_editor import CalibrationEditor
        for released,pressed in [(500,3500),(3200,700)]:
            c=fit(released,pressed)
            self.assertEqual(pressure(released,c),0);self.assertEqual(pressure(pressed,c),127)
            self.assertTrue(55<=pressure((released+pressed)//2,c)<=70)
        with self.assertRaises(ValueError):fit(100,100)
        with self.assertRaises(ValueError):normalize({0:dict(baseline=4096,gain=127,invert=False)})
        editor=CalibrationEditor(self.d);editor.channel.setValue(8);editor.released.setValue(3200);editor.pressed.setValue(700);editor.calculate();editor.store()
        saved=self.d.capture_performance();self.d.pad_calibration={};self.d.restore_performance(json.loads(json.dumps(saved)))
        self.assertEqual(self.d.pad_calibration[8],fit(3200,700))
        self.p.data.clear();editor.send();self.d.pump()
        packets=self.packets();self.assertEqual([p[1] for p in packets],[127,17])
        raw=packets[1];self.assertEqual(raw[2],1);self.assertEqual(raw[4],8);self.assertEqual(raw[7],1)
        self.assertEqual(int.from_bytes(raw[12:16],'little'),self.d.pad_calibration[8]['gain'])
        self.assertEqual(int.from_bytes(raw[24:28],'little'),self.d.pad_calibration[8]['baseline'])
        editor.close()
    def test_uart_guard_preserves_crc_and_frame_boundaries(self):
        a,b=Event(6),Event(18)
        self.assertEqual(len(a.encode()),34);self.assertEqual(a.encode_uart(),a.encode()+bytes(UART_GUARD_BYTES))
        decoder=Decoder();frames=decoder.feed(a.encode_uart()+b.encode_uart())
        self.assertEqual(frames,[a.encode()[2:],b.encode()[2:]]);self.assertEqual(decoder.bad_crc,0)
        self.d.enqueue(a);self.d.pump();self.assertEqual(bytes(self.p.data),a.encode_uart())
        self.p.data.clear()
        for i in range(5):self.d.enqueue(Event(6,part=i))
        self.d.pump();self.assertEqual(len(self.packets()),4);self.assertEqual(len(self.d.queue),1)
        self.d.pump();self.assertEqual(len(self.packets()),5)
    def test_last_contact_returns_track_and_repress_cancels_return(self):
        self.d.press(208,60,100);self.d.press(209,64,100);self.d.pump();self.p.data.clear()
        self.d.release(208);self.d.pump();self.assertFalse(any(p[1]==4 and p[7]==1 for p in self.packets()))
        self.d.release(209);self.d.press(208,67,90);self.d.pump()
        commands=[p[7] for p in self.packets() if p[1]==4];self.assertEqual(commands,[1,0])
    def test_keyboard_release_survives_seat_change(self):
        self.d.press(208,60,100);self.d.pump();self.d.seat.setValue(3);self.d.release(208);self.d.pump()
        self.assertFalse(self.d.held);self.assertTrue(any(p[1]==1 and p[2]==1 for p in self.packets()))
    def test_stale_ownership_reply_is_recovered_for_held_contact(self):
        self.d.press(208,60,100);self.d.pump();self.d.flush_notes(6,dict(owner=0,epoch=3));self.d.pump()
        self.d.flush_notes(6,dict(owner=1,epoch=4));self.d.pump()
        ons=[p for p in self.packets() if p[1]==0];self.assertEqual([int.from_bytes(p[8:12],'little') for p in ons],[2,4])
    def test_drum_kit_routes_three_roles(self):
        self.d.states.update({p:dict(owner=2,epoch=3) for p in range(3)})
        for n in (36,38,42):self.d.on_midi((2,[144,n,80]))
        # Six ownership/note events span two bounded UART service ticks.
        self.d.pump();self.d.pump();self.assertEqual({p[3] for p in self.packets() if p[1]==0},{0,1,2})
if __name__=='__main__':unittest.main(verbosity=2)
