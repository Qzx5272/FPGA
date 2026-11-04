"""Independent stateful integer reference versus the actual 16-band RTL."""
from pathlib import Path
import json, math, random, hashlib, subprocess, os
from generate_vocoder_coeffs import signed

ROOT=Path(__file__).resolve().parents[3]
B=ROOT/'synth/band'; SRC=B/'experimental/vocoder/ported'
OUT=B/'evidence/vocoder_filterbank'; OUT.mkdir(parents=True,exist_ok=True)

def wrap(n): return (n+2**31)%2**32-2**31

class Cascade:
    def __init__(self,c): self.c=c; self.history=[[0]*4 for _ in range(2)]
    def step(self,x):
        for k in range(2):
            b0,b1,b2,a1,a2=self.c[k*5:k*5+5]
            x1,x2,y1,y2=self.history[k]
            y=wrap(b0*x>>20)
            for t in (-(a1*y1>>20),b1*x1>>20,-(a2*y2>>20),b2*x2>>20): y=wrap(y+t)
            self.history[k]=[x,x1,y,y1]; x=y
        return x

rows=[[signed(x) for x in l.split()] for l in (SRC/'coeffs.mem').read_text().splitlines()]
def bank(): return [[Cascade(rows[i]),Cascade(rows[16]),Cascade(rows[i])] for i in range(16)]
filters=bank(); rng=random.Random(3588); vectors=[]; peak=0; tail=0
COUNT=4096; RESET_AT=2048
for n in range(COUNT):
    if n==RESET_AT: filters=bank()
    if n<1024:
        mod=int(2000000*math.sin(2*math.pi*940*n/48000)); carrier=rng.randint(-2000000,2000000)
    elif n<1536: mod=rng.randint(-8388608,8388607); carrier=rng.randint(-8388608,8388607)
    elif n<2048: mod=carrier=0
    elif n<2080: mod=carrier=0
    elif n<2100: mod=8388607 if n%2 else -8388608;carrier=mod
    else: mod=carrier=0
    expected=[]
    for m,e,c in filters:
        v=m.step(mod); env=e.step(min(abs(v),2147483647)); out=c.step(carrier)
        expected.extend([out,env]); peak=max(peak,abs(out),abs(env))
        if n>=4000: tail=max(tail,abs(out),abs(env))
    vectors.extend([mod,carrier]+expected)
(OUT/'vectors.hex').write_text('\n'.join(f'{v&0xffffffff:08x}' for v in vectors)+'\n',encoding='ascii')
tb='''`timescale 1ns/1ps
module tb;
reg clk_in=0;always #10 clk_in=~clk_in;
reg rst_in=1,valid_in=0;
reg signed [31:0] carrier_sample_in=0,modulator_sample_in=0;
wire signed [31:0] carrier_out[15:0],envelope_out[15:0];
wire valid_out,ready_out;
filterbank #(.COEFF_FILE("COEFF_PATH")) dut(.*);
reg [31:0] vectors[0:139263];
integer n,j,cycles,maximum=0;
initial begin
 $readmemh("vectors.hex",vectors);
 repeat(4)@(negedge clk_in);
 if(valid_out!==0||ready_out!==0)$fatal(1,"reset control");
 rst_in=0;@(negedge clk_in);
 for(n=0;n<4096;n=n+1)begin
  if(n==2048)begin
   // Reset while a poisoned transaction is actually in progress.
   valid_in=1;modulator_sample_in=1234567;carrier_sample_in=-1234567;
   repeat(7)@(negedge clk_in);rst_in=1;valid_in=0;
   repeat(2)@(negedge clk_in);
   if(valid_out!==0)$fatal(1,"reset valid");
   for(j=0;j<16;j=j+1)if(carrier_out[j]!==0||envelope_out[j]!==0)$fatal(1,"reset data");
   rst_in=0;@(negedge clk_in);
  end
  if(!ready_out)$fatal(1,"not ready before sample");
  modulator_sample_in=vectors[n*34];carrier_sample_in=vectors[n*34+1];valid_in=1;
  @(negedge clk_in);valid_in=0;cycles=0;
  while(!valid_out)begin
   // Inputs can change while busy; a spurious valid must not corrupt state.
   if(cycles==5)begin valid_in=1;modulator_sample_in=32'h7fffffff;carrier_sample_in=32'h80000000;end
   if(cycles==6)valid_in=0;
   @(negedge clk_in);cycles=cycles+1;
   if(cycles>200)$fatal(1,"deadline");
  end
  for(j=0;j<16;j=j+1)begin
   if(carrier_out[j]!==vectors[n*34+2+j*2]||envelope_out[j]!==vectors[n*34+3+j*2])
    $fatal(1,"sample %0d band %0d got %h/%h expected %h/%h",n,j,carrier_out[j],envelope_out[j],vectors[n*34+2+j*2],vectors[n*34+3+j*2]);
  end
  if(cycles>maximum)maximum=cycles;
  @(negedge clk_in);
  if(valid_out!==0)$fatal(1,"valid not pulse");
 end
 $display("PASS4096 samples x16 bands; busy input rejection, mid-transaction reset; maxcycles=%0d",maximum);$finish;
end
initial begin #100000000;$fatal(1,"timeout");end
endmodule
'''.replace('COEFF_PATH',(SRC/'coeffs.mem').as_posix())
(OUT/'tb.sv').write_text(tb,encoding='ascii')
tools=ROOT/'tmp/oss-cad-suite/bin';env=dict(os.environ)
env['PATH']=str(tools)+os.pathsep+str(tools.parent/'lib')+os.pathsep+env['PATH']
files=[SRC/'filterbank.sv',SRC/'double_biquad.sv',SRC/'coeffs.mem',Path(__file__)]
record=dict(status='running',scope='Bit-exact filterbank simulation only, no mixer, board, analog audio or long-tail stability claim',
            samples=COUNT,bands=16,peak_reference=peak,last_96_samples_tail_peak=tail,
            sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
(OUT/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
c=subprocess.run([str(tools/'iverilog.exe'),'-g2012','-s','tb','-o',str(OUT/'sim.vvp'),str(SRC/'double_biquad.sv'),str(SRC/'filterbank.sv'),str(OUT/'tb.sv')],env=env,capture_output=True,text=True)
(OUT/'compile.log').write_text(c.stdout+c.stderr,encoding='utf-8')
if c.returncode: raise RuntimeError(c.stderr)
r=subprocess.run([str(tools/'vvp.exe'),str(OUT/'sim.vvp')],cwd=OUT,env=env,capture_output=True,text=True,timeout=180)
(OUT/'simulation.log').write_text(r.stdout+r.stderr,encoding='utf-8')
record.update(status='passed' if r.returncode==0 else 'failed',log=r.stdout+r.stderr)
(OUT/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record,indent=2))
if r.returncode:raise SystemExit(1)

