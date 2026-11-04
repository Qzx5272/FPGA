"""Logical-video export preserves music and fails closed without physical constraints."""
import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from offline_video import export_video_project
from offline_dvi import export_dvi_project

class VideoExportTests(unittest.TestCase):
    def test_dvi_clock_and_reset_contract(self):
        song=dict(format='starcluster-score-2',sample_rate=48000,bpm=120,
                  duration_samples=48000,engine_profile='singer-v1',
                  events=[dict(sample=0,kind=0,part=0,note=60,velocity=90,serial=1),
                          dict(sample=24000,kind=1,part=0,note=60,velocity=0,serial=1)])
        with tempfile.TemporaryDirectory() as directory:
            target=export_dvi_project(song,Path(directory)/'dvi')
            manifest=json.loads((target/'export_manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['hardware_profile'],'workstation-i2s-dvi-v1')
            for name,digest in manifest['sources'].items():
                self.assertEqual(hashlib.sha256((target/name).read_bytes()).hexdigest(),digest,name)
            wrapper=(target/'rtl/offline_workstation_top.sv').read_text()
            self.assertNotIn('input pixel_clk',wrapper)
            self.assertIn('gowin_dvi_output video_output',wrapper)
            core=(target/'rtl/band_workstation_video_top.sv').read_text()
            self.assertIn('.rst(rst||panic||audio_stop||!video_link_ready)',core)
            self.assertEqual(core.count(' pcm_spectrum_buffered #('),1)
            self.assertTrue((target/'licenses/dvi_SOURCE.json').is_file())
            result=subprocess.run([sys.executable,str(target/'check_workstation_pins.py')],cwd=target,capture_output=True)
            self.assertNotEqual(result.returncode,0)

    def test_music_manifest_and_missing_pins(self):
        song=dict(format='starcluster-score-2',sample_rate=48000,bpm=120,
                  duration_samples=48000,engine_profile='singer-v1',
                  events=[dict(sample=0,kind=0,part=0,note=60,velocity=90,serial=1),
                          dict(sample=24000,kind=1,part=0,note=60,velocity=0,serial=1)])
        with tempfile.TemporaryDirectory() as directory:
            target=export_video_project(song,Path(directory)/'video')
            self.assertEqual(json.loads((target/'project.json').read_text()),song)
            manifest=json.loads((target/'export_manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['hardware_profile'],'workstation-i2s-rgb-v1')
            for name,digest in manifest['sources'].items():
                self.assertEqual(hashlib.sha256((target/name).read_bytes()).hexdigest(),digest,name)
            core=(target/'rtl/band_workstation_video_top.sv').read_text()
            self.assertEqual(core.count(' pcm_spectrum_buffered #('),1)
            wrapper=(target/'rtl/offline_workstation_top.sv').read_text()
            self.assertIn('input pixel_clk',wrapper)
            self.assertNotIn('output[31:0]video_frame_count',wrapper)
            result=subprocess.run([sys.executable,str(target/'check_workstation_pins.py')],cwd=target,capture_output=True)
            self.assertNotEqual(result.returncode,0)

if __name__=='__main__':unittest.main()
