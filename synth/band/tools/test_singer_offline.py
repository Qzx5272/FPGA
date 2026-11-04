"""Compile the actual exported top, then verify uncommanded boot performance."""
from pathlib import Path
import sys,os,json,subprocess,hashlib,datetime
r=Path(__file__).resolve().parents[3];b=r/'synth/band';sys.path.insert(0,str(b/'host'))
from offline import export_project
workstation='--workstation' in sys.argv
stage='--stage' in sys.argv or workstation
if stage:
 from offline_stage import export_stage_project as export_project
if workstation:
 from offline_workstation import export_workstation_project as export_project
score=dict(format='starcluster-score-2',engine_profile='singer-v1',sample_rate=48000,bpm=120,duration_samples=192,
 events=[dict(sample=0,kind=0,part=15,note=60,velocity=90,serial=1),dict(sample=96,kind=1,part=15,note=60,velocity=0,serial=1)],
 performance=dict(master=20,wet=12,tempo=120,root=3,collaboration=False,patches={'15':{'0':64}}))
target=Path('D:/StarclusterBuilds')/(('workstation_offline_' if workstation else 'stage_offline_' if stage else 'singer_offline_')+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
export_project(score,target,autoplay=True)
o=b/'evidence'/('workstation_offline' if workstation else 'stage_offline' if stage else 'singer_offline');o.mkdir(exist_ok=True)
tb='''`timescale 1ns/1ps
module tb;
 reg clk=0;always #10 clk=~clk;
 wire tx,bck,ws,din,pa;
 offline_singer_top dut(.clk(clk),.uart_rx_pin(1'b1),.mic_bck(1'b0),.mic_ws(1'b0),.mic_sd(1'b0),
 .uart_tx_pin(tx),.HP_BCK(bck),.HP_WS(ws),.HP_DIN(din),.PA_EN(pa));
 initial begin
  wait(!dut.band.engine.rst);wait(dut.band.engine.playing);
  wait(dut.band.engine.song_position>=24);repeat(200)@(negedge clk);
  if(!dut.band.engine.singer_gate||dut.band.engine.singer_note!=63)$fatal(1,"Boot score/pitch");
  if(dut.band.engine.core.singer_expression!=64||dut.band.engine.master!=20||dut.band.engine.wet!=12||dut.band.engine.core.collaboration_enabled)$fatal(1,"Boot presets");
  if(!dut.band.microphone_stale||dut.band.engine.singer_mix!=0)$fatal(1,"Missing mic must mute voice");
  wait(!dut.band.engine.playing);repeat(200)@(negedge clk);
  if(dut.band.engine.song_position!=192||dut.band.engine.singer_gate||dut.band.engine.deadline_miss||dut.band.engine.dac_dropped)$fatal(1,"Boot completion");
  $display("PASS exported singer top: no UART commands,autoplay,transposed note63,expression64/master20/wet12/collaboration0,no-mic mute,naturalend192,zero deadlines/drops");$finish;
 end
 initial begin #10000000;$fatal(1,"Timeout");end
endmodule
'''
if stage:
 tb=tb.replace('offline_singer_top dut(', 'offline_stage_top dut(')
 tb=tb.replace('.clk(clk),', ".adc_dout(10'd0),.adc_cs_n(),.adc_sclk(),.adc_din(),.play_button(1'b0),.stop_button(1'b0),.panic_button(1'b0),.root(4'd0),.minor_mode(1'b0),.pedal_raw(4'd0),.seat_led(),.clk(clk),")
 tb=tb.replace('PASS exported singer top:', 'PASS exported full-stage top:')
if workstation:
 tb=tb.replace('offline_stage_top dut(', 'offline_workstation_top dut(')
 tb=tb.replace('.HP_BCK(bck),.HP_WS(ws),.HP_DIN(din),', '.audio_clk(audio_clk),.i2s_bck(bck),.i2s_ws(ws),.i2s_sd(din),.display_clk(clk),.display_read(1\'b0),.display_release(1\'b0),.display_address(11\'d0),')
 tb=tb.replace(' wire tx,bck,ws,din,pa;', ''' reg audio_clk=0,audio_run=0;always #20.345052 if(audio_run)audio_clk=~audio_clk;
 initial begin
  wait(!dut.band.engine.rst);repeat(12000)@(negedge clk);
  if(dut.band.engine.playing||dut.band.engine.offline_started||!dut.band.audio_clock_fault)$fatal(1,"autoplay escaped absent audio clock");
  audio_run=1;
 end
 wire tx,bck,ws,din,pa;''')
 tb=tb.replace('  $display("PASS exported full-stage top:', '''  @(negedge audio_clk);audio_run=0;repeat(51000)@(negedge clk);
  if(!dut.band.audio_clock_fault)$fatal(1,"missing clock not detected");
  audio_run=1;wait(!dut.band.audio_clock_fault);repeat(20000)@(negedge clk);
  if(dut.band.engine.playing||!dut.band.engine.offline_started)$fatal(1,"autoplay repeated after clock recovery");
  $display("PASS exported workstation:waited for clock,one-shot autoplay,no automatic replay after outage;''')
(o/'tb.v').write_text(tb)
t=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(t)+os.pathsep+str(t.parent/'lib')+os.pathsep+env['PATH']
files=list((target/'rtl').glob('*.v'))+list((target/'rtl').glob('*.sv'))+[o/'tb.v']
c=subprocess.run([str(t/'iverilog.exe'),'-g2012','-I',str(target/'rtl'),'-s','tb','-o',str(o/'test.vvp')]+list(map(str,files)),env=env,capture_output=True,text=True)
(o/'compile.log').write_text(c.stdout+c.stderr)
if c.returncode:raise RuntimeError(c.stderr)
p=subprocess.run([str(t/'vvp.exe'),str(o/'test.vvp')],cwd=target,env=env,capture_output=True,text=True,timeout=180)
# Running the actual vendor entry point must fail before synthesis, without
# invented microphone pins. This performs no programmer action.
gate=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(target/'build.tcl')],cwd=target,capture_output=True,text=True,timeout=30)
(o/'constraint_gate.log').write_text(gate.stdout+gate.stderr)
assert ('Workstation pin/timing constraints missing' if workstation else 'Microphone pin/timing constraints missing') in gate.stdout+gate.stderr
assert not (target/'impl/gwsynthesis').exists()
manifest=json.loads((target/'export_manifest.json').read_text(encoding='utf-8'))
for name,h in manifest['sources'].items():assert hashlib.sha256((target/name).read_bytes()).hexdigest()==h
record=dict(status='passed' if not p.returncode else 'failed',scope='Exported HDL cold-start simulation and missing-pin build gate; no physical boot/microphone/timing claim',export=str(target),build_id=manifest['build_id'],source_manifest=manifest,log=p.stdout+p.stderr)
(o/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(record['status'],record['log']);raise SystemExit(p.returncode)
