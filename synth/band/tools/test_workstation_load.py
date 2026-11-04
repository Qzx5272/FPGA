"""Bounded256-slot automatic score on actual exported combined top, absent mic."""
from pathlib import Path
import sys,os,json,hashlib,subprocess,datetime
r=Path(__file__).resolve().parents[3];b=r/'synth/band';sys.path.insert(0,str(b/'host'))
from offline_workstation import export_workstation_project
events=[];parts=list(range(8,15))+[7]
for kind,sample in ((0,0),(1,5000)):
 for bank,part in enumerate(parts):
  for i in range(32):events.append(dict(sample=sample,kind=kind,part=part,note=40+i,velocity=80 if not kind else 0,serial=bank*32+i+1))
score=dict(format='starcluster-score-2',engine_profile='singer-v1',sample_rate=48000,bpm=120,duration_samples=6000,events=events,
 performance=dict(master=4,wet=24,tempo=120,collaboration=False,patches={str(p):{'6':16383,'7':0} for p in parts}))
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');target=Path('D:/StarclusterBuilds')/('workstation_load_'+stamp)
export_workstation_project(score,target,True)
o=b/'evidence/workstation_load'/stamp;o.mkdir(parents=True)
tb='''`timescale 1ns/1ps
module tb;
 reg clk=0,audio_clk=0;always #10 clk=~clk;always #20.345052 audio_clk=~audio_clk;
 offline_workstation_top dut(.clk(clk),.audio_clk(audio_clk),.uart_rx_pin(1'b1),
 .mic_bck(1'b0),.mic_ws(1'b0),.mic_sd(1'b0),.adc_dout(10'd0),
 .play_button(1'b0),.stop_button(1'b0),.panic_button(1'b0),.root(4'd0),.minor_mode(1'b0),.pedal_raw(4'd0),
 .display_clk(clk),.display_read(1'b0),.display_release(1'b0),.display_address(11'd0));
 integer checked=0,peak=0,maxcycles=0;reg started=0;
 always @(negedge clk)begin
  if(dut.band.engine.playing)started=1;
  if(started)begin
   if(dut.band.i2s_dropped||dut.band.i2s_underruns||dut.band.engine.deadline_miss||dut.band.engine.clips||dut.band.engine.rejected||dut.band.fft_clips||dut.band.rejected_bins)$fatal(1,"load error counters");
   if(dut.band.pcm_valid)begin
    if($signed(dut.band.pcm_left)>peak)peak=$signed(dut.band.pcm_left);
    if(dut.band.engine.render_cycles>maxcycles)maxcycles=dut.band.engine.render_cycles;
    if(dut.band.engine.song_position>=500&&dut.band.engine.song_position<5000)begin
     if(dut.band.engine.active_voices!=256)$fatal(1,"load lost position=%0d voices=%0d",dut.band.engine.song_position,dut.band.engine.active_voices);
     checked=checked+1;
    end
   end
  end
 end
 initial begin
  wait(dut.band.engine.playing);wait(!dut.band.engine.playing);repeat(10000)@(negedge clk);
  if(dut.band.engine.song_position!=6000||dut.band.engine.active_voices!=0||checked<4490||peak==0||!dut.display_available)$fatal(1,"completion/count/FFT");
  $display("PASS256 slots held:checked_frames=%0d peak=%0d maxcycles=%0d naturalend6000 released0 display_stalled zeroerrors",checked,peak,maxcycles);$finish;
 end
 initial begin #150000000;$fatal(1,"timeout");end
endmodule
'''
(o/'tb.v').write_text(tb);(o/'score.json').write_text(json.dumps(score,indent=2))
manifest=json.loads((target/'export_manifest.json').read_text(encoding='utf-8'))
for name,h in manifest['sources'].items():assert hashlib.sha256((target/name).read_bytes()).hexdigest()==h
record=dict(status='running',export=str(target),source_manifest=manifest,scope='Actual exported combined top:256 automatic band slots,delay,I2S,HannFFT,stalled display,release/natural end;no microphone/singer excitation,serial-pin equality,long-term or physical claim')
report=o/'result.json';report.write_text(json.dumps(record,indent=2))
t=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(t)+os.pathsep+str(t.parent/'lib')+os.pathsep+env['PATH']
try:
 files=sorted((target/'rtl').glob('*.v'))+sorted((target/'rtl').glob('*.sv'))+[o/'tb.v']
 c=subprocess.run([str(t/'iverilog.exe'),'-g2012','-I',str(target/'rtl'),'-s','tb','-o',str(o/'test.vvp'),*map(str,files)],env=env,capture_output=True,text=True,timeout=120)
 (o/'compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,'compile failed'
 p=subprocess.run([str(t/'vvp.exe'),str(o/'test.vvp')],cwd=target,env=env,capture_output=True,text=True,timeout=600)
 record.update(status='passed' if p.returncode==0 else 'failed',returncode=p.returncode,log=p.stdout+p.stderr)
except Exception as exc:record.update(status='failed',error=str(exc));raise
finally:report.write_text(json.dumps(record,indent=2))
print(record['status'],record.get('log',''));sys.exit(record['status']!='passed')
