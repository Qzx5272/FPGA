"""Cold-start the exported project's actual board top in RTL simulation."""
from pathlib import Path
import sys,json,copy,os,subprocess,datetime,hashlib
root=Path(__file__).resolve().parents[3];band=root/'synth/band';sys.path.insert(0,str(band/'host'))
from offline import export_project
from score import edit_vowel,insert_vowel_phrase
score=json.loads((band/'assets/confluence.json').read_text(encoding='utf-8'))
score.update(duration_samples=960,events=[dict(sample=0,kind=0,part=5,note=69,velocity=90,serial=1),dict(sample=240,kind=1,part=5,note=69,velocity=0,serial=1)])
score['events'] += [dict(sample=24,kind=0,part=7,note=60,velocity=90,serial=2),dict(sample=300,kind=1,part=7,note=60,velocity=0,serial=2)]
score['events'].sort(key=lambda e:e['sample'])
score=edit_vowel(score,0,4)
score=insert_vowel_phrase(score,360,[(0,60,80),(2,64,80),(3,67,80),(1,72,80)])
score['performance']=dict(master=40,wet=10,tempo=120,root=2,collaboration=False,patches={5:{0:99,2:3,4:1000,5:7,6:12345,7:6}})
score['performance']['pad_calibration']={0:dict(baseline=1000,gain=200,invert=False),8:dict(baseline=1095,gain=261,invert=True)}
target=root/'tmp'/('offline_validation_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
export_project(score,target,autoplay=True)
try:export_project(score,target,autoplay=True);raise AssertionError('Overwrote existing project')
except ValueError:pass
tb=target/'tb_offline.v'
tb.write_text('''`timescale 1ns/1ps
module tb_offline;
 reg clk=0;always #10 clk=~clk;wire tx,b,w,d,p;
 reg pad_sample_valid=0;reg [11:0] raw0=0,raw8=0;
 band_top dut(clk,1'b1,tx,b,w,d,p);
 pad_frontend #(.CHIPS(2),.PADS(16)) calibrated(.clk(clk),.rst(dut.engine.rst),.panic(1'b0),.sample_valid(pad_sample_valid),.sample_channel(3'd0),.samples({raw8,raw0}),.config_valid(1'b0),.config_channel(7'd0),.config_baseline(12'd0),.config_gain(16'd127),.config_invert(1'b0),.on_threshold(7'd24),.off_threshold(7'd12),.event_ready(1'b1));
 task pressure_frame;input [11:0] a,b;
 begin @(negedge clk);raw0=a;raw8=b;pad_sample_valid=1;@(negedge clk);pad_sample_valid=0;repeat(8)@(negedge clk);end endtask
 task syllable;input [2:0] expected_vowel;input [6:0] expected_pitch;integer slot,found;
 begin
  wait(dut.engine.core.banks[7].unit.allocator.gate!=0);@(negedge clk);found=0;
  if(dut.engine.core.banks[7].unit.vowel[0]!=expected_vowel)$fatal(1,"phrase vowel ordering");
  for(slot=0;slot<32;slot=slot+1)if(dut.engine.core.banks[7].unit.allocator.gate[slot])begin
   if(dut.engine.core.banks[7].unit.allocator.note[slot]!=expected_pitch)$fatal(1,"phrase pitch/transposition");found=found+1;
  end
  if(found!=1)$fatal(1,"phrase must have one gated syllable");
  wait(dut.engine.core.banks[7].unit.allocator.gate==0);
 end endtask
 initial begin
  wait(!dut.engine.rst);repeat(10)@(negedge clk);
  if(dut.engine.master!=40||dut.engine.wet!=10||dut.engine.transpose!=2||dut.engine.core.collaboration_enabled)$fatal(1,"boot settings");
  if(dut.engine.core.banks[5].unit.attack[0]!=1000||dut.engine.core.banks[5].unit.sustain[0]!=49380||dut.engine.core.banks[5].unit.target_expression[0]!=99)$fatal(1,"boot patch");
  if(calibrated.baselines[0]!=1000||calibrated.gains[0]!=200||calibrated.baselines[8]!=1095||calibrated.gains[8]!=261||!calibrated.inversions[8]||calibrated.inversions[0]||calibrated.gains[1]!=127)$fatal(1,"boot pressure calibration");
  pressure_frame(1000,3000);pressure_frame(3600,1000);
  if(calibrated.pressure_values[0+:7]!=126||calibrated.pressure_values[56+:7]!=127||!calibrated.physical[0]||!calibrated.physical[8])$fatal(1,"positive and inverted calibrated pressure");
  pressure_frame(1000,3000);
  if(calibrated.physical[0]||calibrated.physical[8]||calibrated.pressure_values[0+:7]!=0||calibrated.pressure_values[56+:7]!=0)$fatal(1,"calibrated release");
  wait(dut.engine.playing);wait(dut.engine.active_voices>0);
  wait(dut.engine.core.banks[7].unit.vowel[0]==4);
  if(dut.engine.core.banks[7].unit.allocator.gate!=0)$fatal(1,"vowel must precede choir note");
  wait(dut.engine.core.banks[7].unit.allocator.gate!=0);
  wait(dut.engine.core.banks[7].unit.allocator.gate==0);
  syllable(0,62);syllable(2,66);syllable(3,69);syllable(1,74);
  wait(dut.engine.song_position>=700);
  if(dut.engine.core.banks[7].unit.vowel[0]!=4)$fatal(1,"phrase vowel restore");
  wait(!dut.engine.playing);repeat(500)@(negedge clk);
  if(dut.engine.core.banks[5].unit.allocator.gate!=0||dut.engine.core.banks[7].unit.allocator.gate!=0||dut.engine.deadline_miss!=0)$fatal(1,"offline completion");
  $display("PASS exported offline project: autonomous cold-start, four phrase syllables reach actual choir allocator with correct vowel/pitch and separate gates, vowel restoration, transpose/mix/ADSR and per-pad calibration defaults, correct releases and zero deadline misses");$finish;
 end
 initial begin #30000000;$fatal(1,"timeout");end
endmodule
''')
bin=root/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(bin)+os.pathsep+str(bin.parent/'lib')+os.pathsep+env['PATH']
c=subprocess.run([str(bin/'iverilog.exe'),'-g2012','-I',str(target/'rtl'),'-s','tb_offline','-o',str(target/'test.vvp'),*[str(p) for p in (target/'rtl').glob('*.v')],str(tb)],env=env,capture_output=True,text=True)
if c.returncode:raise RuntimeError(c.stderr)
r=subprocess.run([str(bin/'vvp.exe'),str(target/'test.vvp')],env=env,capture_output=True,text=True,timeout=180)
record=dict(status='passed' if r.returncode==0 and 'PASS' in r.stdout else 'failed',evidence_level='exported HDL cold-start simulation only; no Flash write',source_project=str(target),export_manifest_sha256=hashlib.sha256((target/'export_manifest.json').read_bytes()).hexdigest(),log=r.stdout+r.stderr)
(band/'evidence/offline_export.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
if record['status']!='passed':raise SystemExit(1)
