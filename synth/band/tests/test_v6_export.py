import copy,json,sys,tempfile,unittest
from pathlib import Path
band=Path(__file__).resolve().parents[1];sys.path.insert(0,str(band/'host'))
from score import load
from offline_v6 import export_v6_project


class V6Export(unittest.TestCase):
    def score(self):
        score=load(band/'assets/four_families_demo.json')
        score.update(format='starcluster-score-2',engine_profile='singer-v1')
        score['performance']=dict(master=0,wet=40,tempo=110,root=2,effect_mode=2,collaboration=False,
          patches={'6':{'0':99,'8':9,'9':20},'15':{'0':75}},mixer=dict(muted=[1],solo=None,bypass=False),
          pad_calibration={'0':dict(baseline=100,gain=127,invert=False)})
        return score

    def test_expansion_export_keeps_scene_and_rejects_unpinned_build(self):
        score=self.score()
        with tempfile.TemporaryDirectory() as folder:
            target=export_v6_project(score,Path(folder)/'export')
            config=json.loads((target/'export_manifest.json').read_text())
            self.assertFalse(config['autoplay']);self.assertFalse(config['physical_pins_reviewed'])
            self.assertEqual(config['events'],len(score['events']))
            controls=(target/'rtl/shared_role_controls.v').read_text()
            self.assertIn('instrument[i]<=offline_parameter_8(i)',controls)
            defaults=(target/'rtl/offline_patch_defaults.vh').read_text()
            self.assertIn("4'd6:offline_parameter_8=16'd9;",defaults)
            self.assertIn("4'd6:offline_parameter_9=16'd20;",defaults)
            self.assertIn("4'd6:offline_parameter_0=16'd99;",defaults)
            self.assertIn('effect_mode<=2;singer_status<=0;wet<=40;master<=0;tempo<=110;transpose<=2;',
              (target/'rtl/workstation_expansion_engine.sv').read_text())
            self.assertIn("mutes<=16'h0002",(target/'rtl/track_ownership.v').read_text())
            self.assertIn('offline_stage_calibration(address)',(target/'rtl/stage_pad_frontend.sv').read_text())
            self.assertEqual((target/'rtl/song_storage_init.vh').read_text().count('controls['),len(score['events']))
            self.assertIn('error "Expansion pins/timing are unreviewed;', (target/'build.tcl').read_text())
            self.assertFalse((target/'constraints/expansion.cst').exists())
            self.assertTrue((target/'licenses/VOXOS_MIT_LICENSE.txt').is_file())

    def test_existing_files_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'kept';p.write_text('do not overwrite')
            with self.assertRaisesRegex(ValueError,'空目录'):export_v6_project(self.score(),folder)
            self.assertEqual(p.read_text(),'do not overwrite')

    def test_compact16_uses_three_adc_and_all_eight_controls(self):
        with tempfile.TemporaryDirectory() as folder:
            target=export_v6_project(self.score(),Path(folder)/'compact',compact16=True)
            config=json.loads((target/'export_manifest.json').read_text())
            self.assertEqual(config['physical_adc_chips'],3)
            self.assertEqual(config['physical_pressure_pads'],16)
            self.assertIn(".adc_dout({7'd0,adc_dout})",(target/'rtl/workstation_v6_complete_top.sv').read_text())
            self.assertIn('stage_pad_frontend #(.PADS(16)) pads(', (target/'rtl/workstation_expansion_engine.sv').read_text())
            expression=(target/'rtl/local_expression.v').read_text()
            self.assertIn('address=channel;raw=samples[2*12+:12];',expression)
            self.assertNotIn('if(sample_valid&&channel<4)',expression)
    def test_usb16_omits_unwired_adc_and_keeps_digital_panel(self):
        with tempfile.TemporaryDirectory() as folder:
            target=export_v6_project(self.score(),Path(folder)/'usb',usb16=True)
            config=json.loads((target/'export_manifest.json').read_text())
            self.assertEqual(config['physical_adc_chips'],0)
            self.assertEqual(config['panel_profile'],'usb16_no_adc')
            top=(target/'rtl/workstation_v6_complete_top.sv').read_text()
            self.assertIn(".adc_dout(10'd0)",top)
            self.assertNotIn('input wire[9:0]adc_dout',top)
            self.assertIn('.LOCAL_INPUTS(0)',(target/'rtl/workstation_expansion_top.sv').read_text())
            self.assertIn('panel_controls controls(', (target/'rtl/workstation_expansion_engine.sv').read_text())

    def test_role_semantics_require_explicit_singer_profile(self):
        score=load(band/'assets/four_families_demo.json')
        score.update(format='starcluster-score-1',engine_profile='band-v1')
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'第16轨'):export_v6_project(score,folder)
