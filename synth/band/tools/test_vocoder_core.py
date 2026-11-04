"""Full chain regression from independent filterbank state vectors; run that first."""
from pathlib import Path
import hashlib,json,os,subprocess,random
ROOT=Path(__file__).resolve().parents[3]; B=ROOT/'synth/band'
SRC=B/'experimental/vocoder/ported';OUT=B/'evidence/vocoder_core';OUT.mkdir(parents=True,exist_ok=True)
prior=B/'evidence/vocoder_filterbank'
evidence=json.loads((prior/'result.json').read_text(encoding='utf-8'))
assert evidence['status']=='passed'
for name,h in evidence['sha256'].items(): assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h
def signed(v):return v if v<2**31 else v-2**32
data=[signed(int(x,16)) for x in (prior/'vectors.hex').read_text().split()]
vectors=[];clips=0
for n in range(4096):
 r=data[n*34:n*34+34]
 if n==2048:clips=0
 y=sum(r[2+i*2]*max(0,r[3+i*2]) for i in range(16))>>23
 clips+=int(y>8388607 or y < -8388608)
 vectors.extend(r[:2]+[max(-8388608,min(8388607,y)),clips])
(OUT/'vectors.hex').write_text('\n'.join(f'{v&0xffffffff:08x}' for v in vectors)+'\n',encoding='ascii')
tb='''`timescale 1ns/1ps
module tb;
reg clk_in=0;always #10 clk_in=~clk_in;
reg rst_in=1,valid_in=0;
reg signed [23:0] carrier_sample_in=0,modulator_sample_in=0;
wire signed [23:0] sample_out;
wire valid_out,ready_out;wire [31:0] clip_count,rejected_count;
vocoder_core #(.COEFF_FILE("COEFF_PATH")) dut(.*);
reg [31:0] vectors[0:16383];integer n,cycles,maximum=0,rejected=0;
initial begin
 $readmemh("vectors.hex",vectors);
 repeat(4)@(negedge clk_in);rst_in=0;@(negedge clk_in);
 for(n=0;n<4096;n=n+1)begin
  if(n==2048)begin
   valid_in=1;repeat(7)@(negedge clk_in);rst_in=1;valid_in=0;
   repeat(2)@(negedge clk_in);
   if(valid_out!==0||sample_out!==0||clip_count!==0||rejected_count!==0)$fatal(1,"reset");
   rst_in=0;rejected=0;@(negedge clk_in);
  end
  if(!ready_out)$fatal(1,"not ready");
  modulator_sample_in=vectors[n*4];carrier_sample_in=vectors[n*4+1];valid_in=1;
  @(negedge clk_in);valid_in=0;cycles=0;
  while(!valid_out)begin
   if(cycles==5)begin valid_in=1;rejected=rejected+1;end
   if(cycles==6)valid_in=0;
   @(negedge clk_in);cycles=cycles+1;
   if(cycles>200)$fatal(1,"deadline");
  end
  if(sample_out!==vectors[n*4+2][23:0]||clip_count!==vectors[n*4+3]||rejected_count!==rejected)
   $fatal(1,"sample %0d got %h expected %h clips %0d reject %0d",n,sample_out,vectors[n*4+2],clip_count,rejected_count);
  if(cycles>maximum)maximum=cycles;
  repeat(2)@(negedge clk_in);
 end
 $display("PASS full vocoder4096 samples, reset, backpressure, clip/reject counters; maxcycles=%0d",maximum);$finish;
end
initial begin #100000000;$fatal(1,"timeout");end
endmodule
'''.replace('COEFF_PATH',(SRC/'coeffs.mem').as_posix())
(OUT/'tb.sv').write_text(tb,encoding='ascii')
tools=ROOT/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+str(tools.parent/'lib')+os.pathsep+env['PATH']
sources=[SRC/n for n in ('double_biquad.sv','filterbank.sv','vocoder_mixer.sv','vocoder_core.sv')]
record=dict(status='running',scope='4096-sample bit-exact standalone chain, not synthesis/timing/audio-quality acceptance',sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[SRC/'coeffs.mem']})
(OUT/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
c=subprocess.run([str(tools/'iverilog.exe'),'-g2012','-s','tb','-o',str(OUT/'sim.vvp')]+[str(p) for p in sources]+[str(OUT/'tb.sv')],env=env,capture_output=True,text=True)
(OUT/'compile.log').write_text(c.stdout+c.stderr,encoding='utf-8')
if c.returncode:raise RuntimeError(c.stderr)
r=subprocess.run([str(tools/'vvp.exe'),str(OUT/'sim.vvp')],cwd=OUT,env=env,capture_output=True,text=True,timeout=180)
record.update(status='passed' if r.returncode==0 else 'failed',log=r.stdout+r.stderr)
(OUT/'simulation.log').write_text(r.stdout+r.stderr,encoding='utf-8')
(OUT/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record,indent=2))
if r.returncode:raise SystemExit(1)
