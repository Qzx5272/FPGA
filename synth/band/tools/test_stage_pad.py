"""Validate stage calibration pipeline against integer reference and event contract."""
from pathlib import Path
import subprocess,os,json,hashlib
r=Path(__file__).resolve().parents[3];b=r/'synth/band';o=b/'evidence/stage_pad';o.mkdir(exist_ok=True)
rtl=b/'experimental/stage/stage_pad_frontend.sv'
tb=(b/'tests/tb_pads.v').read_text().replace('pad_frontend #','stage_pad_frontend #').replace('repeat(6)@(negedge clk);','wait(!dut.busy);repeat(3)@(negedge clk);')
tb=tb.replace(' wire valid,off,exhausted;', ' reg cfg=0,inv=0;reg[11:0]base=0;reg[15:0]gain=127;integer n,expected;\n wire valid,off,exhausted;')
tb=tb.replace("1'b0,7'd0,12'd0,16'd127,1'b0",'cfg,7\'d0,base,gain,inv')
tb=tb.replace('  $display("PASS pad frontend:', '''  // Compare clamp/subtract/multiply including inverted and saturated inputs.
  for(n=0;n<256;n=n+1)begin
   @(negedge clk);cfg=1;base=(n*79)%4096;gain=(n*997)%65536;inv=n%2;
   @(negedge clk);cfg=0;
   expected=inv?4095-(n*37)%4096:(n*37)%4096;
   expected=expected>base?expected-base:0;
   expected=(expected*gain)>>12;if(expected>127)expected=127;
   frame(0,(n*37)%4096,0);
   if(values[6:0]!==expected)$fatal(1,"numeric mismatch n=%d got=%d expected=%d",n,values[6:0],expected);
  end
  // Configuration captured at lookup stays coherent through later phases.
  @(negedge clk);cfg=1;base=100;gain=4096;inv=0;
  @(negedge clk);cfg=0;sv=1;samples=150;
  @(negedge clk);sv=0;
  @(negedge clk);cfg=1;base=4000;gain=65535;inv=1;
  @(negedge clk);cfg=0;wait(!dut.busy);#1;
  if(values[6:0]!=50)$fatal(1,"mixed calibration generations");
  // A busy input is counted, not allowed to corrupt the in-flight batch.
  @(negedge clk);sv=1;samples=0;@(negedge clk);sv=0;
  @(negedge clk);sv=1;@(negedge clk);sv=0;wait(!dut.busy);#1;
  if(overruns!=1)$fatal(1,"busy batch was not rejected");
  @(negedge clk);sv=1;@(negedge clk);sv=0;
  repeat(2)@(negedge clk);panic=1;@(negedge clk);panic=0;
  if(dut.busy||valid||dut.physical)$fatal(1,"panic did not cancel pipeline");
  frame(0,150,0);
  if(values[6:0]!=0)$fatal(1,"panic discarded calibration");
  // Reset must invalidate old RAM contents and restore logical defaults.
  @(negedge clk);rst=1;repeat(2)@(negedge clk);rst=0;
  frame(0,4095,0);
  if(values[6:0]!=126)$fatal(1,"reset did not restore default calibration");
  $display("PASS pad frontend:''')
tb=tb.replace('#100000;','#1000000;')
(o/'tb.v').write_text(tb)
binary=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
commands=[[str(binary/'iverilog.exe'),'-g2012','-s','tb_pads','-o',str(o/'test.vvp'),str(rtl),str(o/'tb.v')],[str(binary/'vvp.exe'),str(o/'test.vvp')]]
priority=b/'tests/tb_stage_pad_priority.sv'
commands += [[str(binary/'iverilog.exe'),'-g2012','-s','tb','-o',str(o/'priority.vvp'),str(rtl),str(priority)],[str(binary/'vvp.exe'),str(o/'priority.vvp')]]
logs=[];ok=True
for command in commands:
 p=subprocess.run(command,env=env,capture_output=True,text=True,timeout=30);logs.append(p.stdout+p.stderr)
 if p.returncode:ok=False;break
record=dict(status='passed' if ok and 'PASS' in logs[-1] else 'failed',scope='Stage-only RTL calibration/event simulation; no board or timing acceptance',sources={str(p.relative_to(b)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (rtl,Path(__file__),b/'tests/tb_pads.v',priority)},log=''.join(logs))
(o/'result.json').write_text(json.dumps(record,indent=2));print(record['log']);raise SystemExit(record['status']!='passed')
