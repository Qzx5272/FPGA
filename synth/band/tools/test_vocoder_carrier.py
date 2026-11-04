"""Independent Fourier reference for actual carrier RTL, including alias mask."""
from pathlib import Path
import math,json,hashlib,subprocess,os
R=Path(__file__).resolve().parents[3];B=R/'synth/band';S=B/'experimental/vocoder/ported';O=B/'evidence/vocoder_carrier';O.mkdir(parents=True,exist_ok=True)
phase=inc=env=vel=0;vectors=[];max_harmonics=0
for n in range(4096):
 gate=int(n<1024 or 1536<=n<3584)
 note=60 if n<1024 else 120 if n<2560 else 24
 v=100 if gate else 0
 if gate:inc=round(440*2**((note-69)/12)*2**32/48000);vel=v
 env=min(65535,env+1024) if gate else max(0,env-512)
 harmonics=[h for h in range(1,65) if inc*h<2**31]
 max_harmonics=max(max_harmonics,len(harmonics))
 # Double precision Fourier series, independent of FPGA sine LUT/interpolation.
 wave=math.floor(sum(131071*math.sin(2*math.pi*((phase*h)%2**32)/2**32)*round(32768/h) for h in harmonics)/2048)
 expected=wave*env*vel>>23
 vectors.extend([gate,note if gate else 0,v,expected,int(env==0)])
 phase=(phase+inc)%2**32
(O/'vectors.hex').write_text('\n'.join(f'{v&0xffffffff:08x}' for v in vectors)+'\n')
tb='''`timescale 1ns/1ps
module tb;
reg clk=0;always #10 clk=~clk;
reg rst=1,panic=0,frame_valid=0,gate=0;reg[6:0]note=0,velocity=0;
wire ready,valid_out;wire signed[23:0]sample_out;wire[31:0]dropped_frames;
vocoder_carrier dut(.*);
reg[31:0]v[0:20479];integer n,t,error,peak_error=0,maxcycles=0,pcm;reg signed[31:0]expectation;
initial begin
 pcm=$fopen("carrier.hex","w");
 $readmemh("vectors.hex",v);repeat(4)@(negedge clk);rst=0;@(negedge clk);
 for(n=0;n<4096;n=n+1)begin
  if(!ready)$fatal(1,"not ready");
  gate=v[n*5];note=v[n*5+1];velocity=v[n*5+2];frame_valid=1;
  @(negedge clk);frame_valid=0;gate=0;note=127;velocity=0;t=0;
  while(!valid_out)begin @(negedge clk);t=t+1;if(t>100)$fatal(1,"deadline");end
  $fdisplay(pcm,"%h",sample_out);
  expectation=v[n*5+3];error=$signed(sample_out)-expectation;if(error<0)error=-error;
  if(error>256)$fatal(1,"Fourier mismatch sample%0d got%0d expected%0d error%0d",n,sample_out,expectation,error);
  if(v[n*5+4]&&sample_out!==0)$fatal(1,"release not exact silence");
  if(error>peak_error)peak_error=error;if(t>maxcycles)maxcycles=t;
  @(negedge clk);
 end
 $fclose(pcm);
 gate=1;velocity=127;note=69;frame_valid=1;@(negedge clk);frame_valid=0;
 repeat(7)@(negedge clk);panic=1;@(negedge clk);
 if(sample_out!==0||valid_out!==0)$fatal(1,"panic");panic=0;
 repeat(100)begin @(negedge clk);if(valid_out)$fatal(1,"stale result after panic");end
 $display("PASS4096 Fourier samples,64harmonic/Nyquist mask,legato,release,panic;maxcycles=%0d maxerror24bitLSB=%0d",maxcycles,peak_error);$finish;
end
initial begin #10000000;$fatal(1,"timeout");end
endmodule
'''
(O/'tb.sv').write_text(tb)
sources=[S/'vocoder_carrier.sv',R/'synth/rtl/hq_sine_quarter.v']
tools=R/'tmp/oss-cad-suite/bin';envtools=dict(os.environ);envtools['PATH']=str(tools)+os.pathsep+str(tools.parent/'lib')+os.pathsep+envtools['PATH']
c=subprocess.run([str(tools/'iverilog.exe'),'-g2012','-I',str(S),'-I',str(B/'rtl'),'-I',str(R/'synth/rtl'),'-s','tb','-o',str(O/'sim.vvp')]+[str(p) for p in sources]+[str(O/'tb.sv')],env=envtools,capture_output=True,text=True)
if c.returncode:raise RuntimeError(c.stderr)
r=subprocess.run([str(tools/'vvp.exe'),str(O/'sim.vvp')],cwd=O,env=envtools,capture_output=True,text=True,timeout=90)
record=dict(status='passed' if r.returncode==0 else 'failed',scope='Monophonic carrier numerical simulation, no voice ownership or physical sound acceptance',log=r.stdout+r.stderr,sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[S/'carrier_weights.vh',B/'rtl/midi_increment.vh',R/'synth/rtl/sine_quarter_init.vh',Path(__file__)]})
(O/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record,indent=2))
if r.returncode:raise SystemExit(1)
