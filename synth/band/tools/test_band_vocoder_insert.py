"""Frame-aligned band/voice mixing against previously bit-exact core vectors."""
from pathlib import Path
import json,hashlib,os,subprocess
R=Path(__file__).resolve().parents[3];B=R/'synth/band';S=B/'experimental/vocoder/ported';O=B/'evidence/band_vocoder_insert';O.mkdir(parents=True,exist_ok=True)
base=B/'evidence/vocoder_core';proof=json.loads((base/'result.json').read_text())
assert proof['status']=='passed'
for name,h in proof['sha256'].items():assert hashlib.sha256((S/name).read_bytes()).hexdigest()==h
raw=[int(x,16) for x in (base/'vectors.hex').read_text().split()]
def signed(v):return v if v<2**31 else v-2**32
vectors=[];clips=0;smooth_gain=0
for n in range(512):
 mic,carrier,voice,_=raw[n*4:n*4+4];voice=signed(voice)
 left=32767 if n%2 else -32768;right=-left if left!= -32768 else 32767
 gain=0 if n%4==0 else 127
 smooth_gain+=int(smooth_gain<gain)-int(smooth_gain>gain)
 wet=voice*smooth_gain>>7;l=(left<<8)+wet;r=(right<<8)+wet
 clips+=int(l>8388607 or l < -8388608 or r>8388607 or r < -8388608)
 vectors.extend([mic,carrier,left,right,gain,max(-8388608,min(8388607,l)),max(-8388608,min(8388607,r)),clips])
(O/'vectors.hex').write_text('\n'.join(f'{x&0xffffffff:08x}' for x in vectors)+'\n')
tb='''`timescale 1ns/1ps
module tb;
reg clk=0;always #10 clk=~clk;
reg rst=1,panic=0,frame_valid=0;
reg signed[15:0]band_left=0,band_right=0;
reg signed[23:0]carrier_in=0,mic_in=0;reg[6:0]voice_gain=0;
wire frame_ready,audio_valid;wire signed[23:0]left_out,right_out;
wire[31:0]dropped_frames,mix_clips,vocoder_clips;
band_vocoder_insert #(.COEFF_FILE("COEFF_PATH"))dut(.*);
reg[31:0]v[0:4095];integer n,t,maximum=0;
initial begin
 $readmemh("vectors.hex",v);repeat(4)@(negedge clk);rst=0;@(negedge clk);
 for(n=0;n<512;n=n+1)begin
  if(!frame_ready)$fatal(1,"frame service deadline");
  mic_in=v[n*8];carrier_in=v[n*8+1];band_left=v[n*8+2];band_right=v[n*8+3];voice_gain=v[n*8+4];frame_valid=1;
  @(negedge clk);frame_valid=0;t=0;
  // Change every external payload; accepted frame must remain coherent.
  mic_in=0;carrier_in=0;band_left=0;band_right=0;voice_gain=0;
  while(!audio_valid)begin
   if(t==4)frame_valid=1;if(t==5)frame_valid=0;
   @(negedge clk);t=t+1;if(t>=1040)$fatal(1,"48k throughput exceeded");
  end
  if(left_out!==v[n*8+5][23:0]||right_out!==v[n*8+6][23:0]||mix_clips!==v[n*8+7]||dropped_frames!==n+1)
   $fatal(1,"aligned frame %0d L=%h R=%h expected=%h/%h clip=%0d",n,left_out,right_out,v[n*8+5],v[n*8+6],mix_clips);
  if(t>maximum)maximum=t;
  repeat(1040-t)@(negedge clk);
 end
 frame_valid=1;@(negedge clk);frame_valid=0;repeat(20)@(negedge clk);panic=1;@(negedge clk);
 if(left_out!==0||right_out!==0||audio_valid!==0)$fatal(1,"panic");
 panic=0;repeat(200)begin @(negedge clk);if(audio_valid)$fatal(1,"old frame escaped panic");end
 $display("PASS512 aligned band+vocoder frames at1041clocks/frame; mute gain, saturation, busy rejection, panic; maxcycles=%0d",maximum);$finish;
end
initial begin #20000000;$fatal(1,"timeout");end
endmodule
'''.replace('COEFF_PATH',(S/'coeffs.mem').as_posix())
(O/'tb.sv').write_text(tb)
sources=[S/n for n in ('double_biquad.sv','filterbank.sv','vocoder_mixer.sv','vocoder_core.sv','band_vocoder_insert.sv')]
tools=R/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+str(tools.parent/'lib')+os.pathsep+env['PATH']
c=subprocess.run([str(tools/'iverilog.exe'),'-g2012','-s','tb','-o',str(O/'sim.vvp')]+[str(p) for p in sources]+[str(O/'tb.sv')],env=env,capture_output=True,text=True)
if c.returncode:raise RuntimeError(c.stderr)
r=subprocess.run([str(tools/'vvp.exe'),str(O/'sim.vvp')],cwd=O,env=env,capture_output=True,text=True,timeout=90)
record=dict(status='passed' if r.returncode==0 else 'failed',scope='Frame join simulation only; real band-top routing, carrier ownership, ADC clocks and physical DAC latency still pending',log=r.stdout+r.stderr,sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[S/'coeffs.mem',Path(__file__)]})
(O/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record,indent=2))
if r.returncode:raise SystemExit(1)
