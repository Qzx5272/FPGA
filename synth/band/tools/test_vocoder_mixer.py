"""Boundary/saturation coverage separate from normal vocoder signals."""
from pathlib import Path
import random,os,subprocess,json,hashlib
ROOT=Path(__file__).resolve().parents[3];B=ROOT/'synth/band'
SRC=B/'experimental/vocoder/ported/vocoder_mixer.sv';OUT=B/'evidence/vocoder_mixer';OUT.mkdir(parents=True,exist_ok=True)
rng=random.Random(138);vectors=[];clip=0
for n in range(256):
 if n==0:c=[0]*16;e=[2147483647]*16
 elif n==1:c=[2147483647]*16;e=[2147483647]*16
 elif n==2:c=[-2147483648]*16;e=[2147483647]*16
 elif n==3:c=[2147483647]*16;e=[-2147483648]*16
 else:
  c=[rng.randint(-2**31,2**31-1) for _ in range(16)]
  e=[rng.randint(-2**31,2**31-1) for _ in range(16)]
 y=sum(a*max(b,0) for a,b in zip(c,e))>>23
 clip+=int(y>8388607 or y < -8388608)
 vectors.extend(c+e+[max(-8388608,min(8388607,y)),clip])
(OUT/'vectors.hex').write_text('\n'.join(f'{v&0xffffffff:08x}' for v in vectors)+'\n')
tb='''`timescale 1ns/1ps
module tb;
reg clk_in=0;always #10 clk_in=~clk_in;
reg rst_in=1,valid_in=0;
reg signed [31:0] carrier_in[15:0],envelope_in[15:0];
wire ready_out,valid_out;wire signed [23:0] sample_out;wire [31:0]clip_count;
vocoder_mixer dut(.*);
reg [31:0] v[0:8703];integer n,j,t;
initial begin
 $readmemh("vectors.hex",v);
 repeat(3)@(negedge clk_in);rst_in=0;@(negedge clk_in);
 for(n=0;n<256;n=n+1)begin
  for(j=0;j<16;j=j+1)begin carrier_in[j]=v[n*34+j];envelope_in[j]=v[n*34+16+j];end
  valid_in=1;@(negedge clk_in);valid_in=0;t=0;
  for(j=0;j<16;j=j+1)begin carrier_in[j]=0;envelope_in[j]=0;end
  while(!valid_out)begin @(negedge clk_in);t=t+1;if(t>40)$fatal(1,"timeout");end
  if(t!=32||sample_out!==v[n*34+32][23:0]||clip_count!==v[n*34+33])$fatal(1,"vector %0d",n);
  @(negedge clk_in);
 end
 rst_in=1;@(negedge clk_in);
 if(clip_count!==0||valid_out!==0||sample_out!==0)$fatal(1,"reset");
 $display("PASS256 mixer boundary vectors: positive/negative saturation, negative envelope clamp, input latching, counter/reset,32cycles");$finish;
end
endmodule
'''
(OUT/'tb.sv').write_text(tb)
tools=ROOT/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+str(tools.parent/'lib')+os.pathsep+env['PATH']
c=subprocess.run([str(tools/'iverilog.exe'),'-g2012','-s','tb','-o',str(OUT/'sim.vvp'),str(SRC),str(OUT/'tb.sv')],env=env,capture_output=True,text=True)
if c.returncode:raise RuntimeError(c.stderr)
r=subprocess.run([str(tools/'vvp.exe'),str(OUT/'sim.vvp')],env=env,cwd=OUT,capture_output=True,text=True,timeout=30)
result=dict(status='passed' if r.returncode==0 else 'failed',log=r.stdout+r.stderr,source_sha256=hashlib.sha256(SRC.read_bytes()).hexdigest(),test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if r.returncode:raise SystemExit(1)
