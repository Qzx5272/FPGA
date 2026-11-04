"""Host score encoder -> atomic storage -> auto singer and human takeover."""
from pathlib import Path
import os,sys,subprocess,json,hashlib,re
r=Path(__file__).resolve().parents[3];b=r/'synth/band';s=b/'experimental/vocoder';o=b/'evidence/singer_score';o.mkdir(exist_ok=True)
sys.path.insert(0,str(b/'host'));from score import upload_events,validate
score=dict(format='starcluster-score-2',engine_profile='singer-v1',sample_rate=48000,bpm=120,duration_samples=320,events=[])
for serial,on,off,note in [(1,0,96,60),(2,160,240,67)]:
 for kind,at,vel in [(0,on,100),(1,off,0)]:score['events'].append(dict(sample=at,kind=kind,part=15,note=note,velocity=vel,serial=serial))
validate(score);(o/'score.json').write_text(json.dumps(score,indent=2))
events=[e for e in upload_events(score) if e.kind==13]
original=(s/'tb_singer_integration.v').read_text();tb=original[:original.index(' initial begin')]
tb=tb.replace('module tb_singer_integration;', '''module tb_singer_score;
 reg play=0,uv=0;reg[2:0]uc=0;reg[31:0]ui=0,uw=0,ua=0;
 wire ur,pending,playing;wire[31:0]upload_errors,position;
''')
tb=tb.replace('.play(1\'b0)', '.play(play),.playing(playing),.song_position(position)')
tb=tb.replace('.upload_valid(1\'b0),.upload_command(3\'d0),.upload_index(32\'d0),.upload_value(32\'d0),.upload_aux(32\'d0)', '.upload_valid(uv),.upload_ready(ur),.upload_command(uc),.upload_index(ui),.upload_value(uw),.upload_aux(ua),.upload_pending(pending),.upload_errors(upload_errors)')
tb=re.sub(r'\.COEFF_FILE\("[^"]+"\)', '.COEFF_FILE("'+(s/'ported/coeffs.mem').as_posix()+'")',tb)
tb+='''
 task upload(input[2:0]c,input[31:0]i,v,a);begin
  @(negedge clk);while(!ur)@(negedge clk);uc=c;ui=i;uw=v;ua=a;uv=1;
  @(negedge clk);uv=0;while(!ur)@(negedge clk);
 end endtask
 task launch;begin
  @(negedge clk);play=1;@(negedge clk);play=0;run_audio=1;
 end endtask
 task at_sample(input integer n);begin wait(position>=n);repeat(200)@(negedge clk);end endtask
 task drain;begin run_audio=0;repeat(400)@(negedge clk);end endtask
 integer base_frames;
 initial begin
  repeat(3)@(negedge clk);rst=0;repeat(9000)@(negedge clk);
'''
for e in events:tb+=f"  upload(3'd{e.flags},32'd{e.epoch},32'd{e.serial},32'd{e.parameter});\n"
tb+='''
  if(!pending||upload_errors)$fatal(1,"Atomic score commit");
  launch();at_sample(20);if(!dut.singer_gate||dut.singer_note!=60||owner!=0)$fatal(1,"Auto note1");
  at_sample(120);if(dut.singer_gate)$fatal(1,"Auto off1");
  at_sample(180);if(!dut.singer_gate||dut.singer_note!=67)$fatal(1,"Auto note2");
  at_sample(280);if(dut.singer_gate)$fatal(1,"Auto off2");
  wait(!playing);repeat(64*1041)@(negedge clk);drain();
  if(position!=320||peak==0||dut.singer_gate||deadline_miss||singer_dropped)$fatal(1,"Auto completion");
  // Take the running machine's track. Old machine off and natural end must
  // not terminate the human note on the same track.
  launch();at_sample(32);@(negedge clk);cv=1;while(!cr)@(negedge clk);@(negedge clk);cv=0;
  wait(owner==1);repeat(100)@(negedge clk);ep=epoch;send(0,500,72);
  at_sample(128);if(!dut.singer_gate||dut.singer_note!=72)$fatal(1,"Old auto release killed human");
  at_sample(200);if(dut.singer_note!=72)$fatal(1,"Machine stole human track");
  wait(!playing);repeat(2000)@(negedge clk);
  if(!dut.singer_gate||dut.singer_note!=72)$fatal(1,"Natural end killed human");
  // Request next-bar return; the next performance start emits the real bar
  // boundary, allowing machine notes again without a forced internal signal.
  @(negedge clk);cmd=1;cv=1;while(!cr)@(negedge clk);@(negedge clk);cv=0;
  repeat(100)@(negedge clk);drain();launch();at_sample(24);
  if(owner!=0||epoch!=3||!dut.singer_gate||dut.singer_note!=60)$fatal(1,"Machine return at new bar");
  if(dut.banks[7].unit.allocator.active||deadline_miss||singer_dropped||upload_errors)$fatal(1,"Singer isolated accounting");
  panic=1;@(negedge clk);panic=0;repeat(100)@(negedge clk);
  if(dut.singer_gate||playing)$fatal(1,"Panic");
  $display("PASS encoded singer score:atomic upload,2auto notes/off,natural end,human takeover survives old release/end,new-bar return,panic;peak=%0d",peak);$finish;
 end
 initial begin #30000000;$fatal(1,"Timeout");end
endmodule
'''
(o/'tb.v').write_text(tb)
t=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(t)+os.pathsep+str(t.parent/'lib')+os.pathsep+env['PATH']
files=list((b/'rtl').glob('*.v'))+list((s/'ported').glob('*.sv'))+[s/'ported/singer_note_control.v',s/'integration/band_singer_core.sv',r/'synth/rtl/hq_sine_quarter.v',o/'tb.v']
hashes={str(f.relative_to(r)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
c=subprocess.run([str(t/'iverilog.exe'),'-g2012','-I',str(b/'rtl'),'-I',str(s/'ported'),'-I',str(r/'synth/rtl'),'-s','tb_singer_score','-o',str(o/'test.vvp')]+list(map(str,files)),env=env,capture_output=True,text=True)
if c.returncode:raise RuntimeError(c.stderr)
p=subprocess.run([str(t/'vvp.exe'),str(o/'test.vvp')],env=env,capture_output=True,text=True,timeout=300)
d=dict(status='passed' if not p.returncode else 'failed',scope='Short score through actual storage/sequencer/ownership/singer; host encoder words via upload port, not UART; synthetic mic; no full concert or physical claim',sha256=hashes,log=p.stdout+p.stderr)
(o/'result.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(d['status'],d['log']);raise SystemExit(p.returncode)
