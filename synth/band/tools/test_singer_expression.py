"""Authenticated singer expression must not modify the shared choir bank."""
from pathlib import Path
import os,subprocess,json,hashlib
r=Path(__file__).resolve().parents[3];b=r/'synth/band';s=b/'experimental/vocoder';o=b/'evidence/singer_expression';o.mkdir(exist_ok=True)
original=(s/'tb_singer_integration.v').read_text()
tb=original[:original.index(' task send;')]
tb=tb.replace('module tb_singer_integration;', '''module tb_singer_expression;
 reg xv=0;reg[3:0]xp=15;reg[7:0]xs=2;reg[31:0]xe=2;reg[13:0]value=0;
 integer bank_updates=0;''')
tb=tb.replace('.command_source(8\'d1)', '.command_source(8\'d2)')
tb=tb.replace('.control_valid(1\'b0),.control_part(4\'d0),.control_source(8\'d1),.control_epoch(32\'d0),.control_parameter(4\'d0),.control_value(14\'d0)', '.control_valid(xv),.control_part(xp),.control_source(xs),.control_epoch(xe),.control_parameter(4\'d0),.control_value(value)')
import re
tb=re.sub(r'\.COEFF_FILE\("[^"]+"\)', '.COEFF_FILE("'+(s/'ported/coeffs.mem').as_posix()+'")',tb)
tb+='''
 always @(posedge clk)if(dut.bank_control_valid)bank_updates=bank_updates+1;
 task control(input[7:0]source,input[31:0]epoch,input[3:0]part,input[13:0]v);begin
  @(negedge clk);xs=source;xe=epoch;xp=part;value=v;xv=1;
  @(negedge clk);xv=0;repeat(12)@(negedge clk);
 end endtask
 initial begin
  repeat(3)@(negedge clk);rst=0;repeat(20)@(negedge clk);
  cv=1;while(!cr)@(negedge clk);@(negedge clk);cv=0;
  wait(owner==2);repeat(100)@(negedge clk);
  if(epoch!=2||dut.singer_expression!=127||dut.singer_scaled_mix!=100)$fatal(1,"Default/owner");
  control(2,2,15,64);if(dut.singer_expression!=64||dut.singer_scaled_mix!=50)$fatal(1,"Owner expression");
  control(3,2,15,0);if(dut.singer_expression!=64)$fatal(1,"Unauthorized control");
  control(2,1,15,0);if(dut.singer_expression!=64)$fatal(1,"Stale epoch control");
  control(1,0,15,0);if(dut.singer_scaled_mix!=0)$fatal(1,"Conductor silence");
  control(1,0,15,16383);if(dut.singer_scaled_mix!=100||dut.singer_expression!=127)$fatal(1,"Clamp");
  if(bank_updates!=0)$fatal(1,"Singer control leaked into choir bank");
  control(1,0,7,32);if(bank_updates!=1||dut.singer_expression!=127)$fatal(1,"Choir control isolation");
  $display("PASS singer expression:owner/epoch authorization,conductor,zero/max/clamp,choir isolation");$finish;
 end
 initial begin #1000000;$fatal(1,"Timeout");end
endmodule
'''
(o/'tb.v').write_text(tb)
t=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(t)+os.pathsep+str(t.parent/'lib')+os.pathsep+env['PATH']
files=list((b/'rtl').glob('*.v'))+list((s/'ported').glob('*.sv'))+[s/'ported/singer_note_control.v',s/'integration/band_singer_core.sv',r/'synth/rtl/hq_sine_quarter.v',o/'tb.v']
hashes={str(f.relative_to(r)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
c=subprocess.run([str(t/'iverilog.exe'),'-g2012','-I',str(b/'rtl'),'-I',str(s/'ported'),'-I',str(r/'synth/rtl'),'-s','tb_singer_expression','-o',str(o/'test.vvp')]+list(map(str,files)),env=env,capture_output=True,text=True)
if c.returncode:raise RuntimeError(c.stderr)
p=subprocess.run([str(t/'vvp.exe'),str(o/'test.vvp')],env=env,capture_output=True,text=True,timeout=30)
d=dict(status='passed' if not p.returncode else 'failed',log=p.stdout+p.stderr,sha256=hashes)
(o/'result.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(d['status'],d['log']);raise SystemExit(p.returncode)
