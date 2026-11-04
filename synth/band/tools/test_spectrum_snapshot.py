"""Full2048-bin frozen display frame, CDC stalls, ordering and reset integrity."""
from pathlib import Path
import os,subprocess,json,hashlib
r=Path(__file__).resolve().parents[3];b=r/'synth/band';s=b/'experimental/audio_visual';o=b/'evidence/spectrum_snapshot';o.mkdir(exist_ok=True)
tb='''`timescale 1ns/1ps
module tb;
reg ac=0,dc=0,run=1;always #5 ac=~ac;always #13 if(run)dc=~dc;
reg rst=1,bv=0,ren=0,rel=0;wire br,available,rv;
reg[10:0]bi=0,addr=0;reg signed[15:0]xr=0,xi=0;wire signed[15:0]yr,yi;
reg[31:0]fid=7,last=9999;wire[31:0]ofid,olast,rejects;wire[16:0]pl,pr;
integer i;
spectrum_snapshot dut(ac,dc,rst,bv,br,bi,xr,xi,fid,last,17'd32768,17'd1234,ren,addr,rel,available,rv,yr,yi,ofid,olast,pl,pr,rejects);
task put(input integer k);begin
 @(negedge ac);while(!br)@(negedge ac);bi=k;xr=k-1024;xi=1024-k;bv=1;
 @(negedge ac);bv=0;
end endtask
initial begin
 repeat(4)@(negedge dc);rst=0;
 put(1);if(rejects!=1)$fatal(1,"out of order not rejected");
 put(0);fid=8;put(1);if(rejects!=2)$fatal(1,"mixed frame not rejected");fid=7;
 @(negedge dc);run=0;
 for(i=0;i<2048;i=i+1)put(i);
 if(br)$fatal(1,"full frame not frozen");
 // Producer may hold next valid while display is absent; RAM stays frozen.
 bv=1;bi=0;xr=123;xi=456;fid=9;repeat(200)@(negedge ac);
 if(br||rejects!=2)$fatal(1,"reader backpressure");run=1;
 wait(available);@(negedge dc);
 if(ofid!=7||olast!=9999||pl!=32768||pr!=1234)$fatal(1,"metadata");
 for(i=0;i<2048;i=i+1)begin
  ren=1;addr=i;@(negedge dc);
  if(!rv||yr!=i-1024||yi!=1024-i)$fatal(1,"frozen bin mismatch %d",i);
 end
 // Release wins over a simultaneous read and retracts valid.
 rel=1;@(negedge dc);rel=0;ren=0;
 if(available||rv)$fatal(1,"release/read collision");
 wait(br);@(posedge ac);#1;@(negedge ac);bv=0; // first bin accepted on ready/valid edge
 if(dut.expected!=1)$fatal(1,"held producer did not resume exactly once");
 for(i=1;i<2048;i=i+1)put(i);
 wait(available);@(negedge dc);if(ofid!=9)$fatal(1,"next frame identity");
 ren=1;addr=0;@(negedge dc);if(yr!=123||yi!=456)$fatal(1,"next frame data");
 run=0;rst=1;repeat(3)@(negedge ac);rst=0;
 if(available||rv||rejects)$fatal(1,"stopped display reset");run=1;
 repeat(5)@(negedge dc);if(available||rv)$fatal(1,"stale publication after reset");
 $display("PASS spectrum snapshot2048:two complete frames,all bins,metadata,stopped reader,backpressure,ordering,release collision,reset");$finish;
end
initial begin #1000000;$fatal(1,"timeout");end
endmodule
'''
(o/'tb.v').write_text(tb);binary=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
files=[s/'spectrum_snapshot.v',o/'tb.v'];logs=[];ok=True
for command in ([str(binary/'iverilog.exe'),'-g2012','-s','tb','-o',str(o/'test.vvp'),*map(str,files)],[str(binary/'vvp.exe'),str(o/'test.vvp')]):
 p=subprocess.run(command,env=env,capture_output=True,text=True,timeout=30);logs.append(p.stdout+p.stderr)
 if p.returncode:ok=False;break
record=dict(status='passed' if ok and 'PASS' in logs[-1] else 'failed',scope='Isolated FFT display frame transport RTL; no analyzer integration,HDMI,timing or physical claim',sources={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files+[Path(__file__)]},log=''.join(logs))
(o/'result.json').write_text(json.dumps(record,indent=2));print(record['log']);raise SystemExit(record['status']!='passed')
