"""I2S -> asynchronous FIFO -> 16-band core, plus clock-loss silence."""
from pathlib import Path
import os,subprocess,json,hashlib
R=Path(__file__).resolve().parents[3];B=R/'synth/band';S=B/'experimental/vocoder/ported';O=B/'evidence/vocoder_input';O.mkdir(parents=True,exist_ok=True)
v=(B/'evidence/vocoder_core/vectors.hex').read_text().splitlines()[:128*4]
(O/'vectors.hex').write_text('\n'.join(v)+'\n')
tb='''`timescale 1ns/1ps
module tb;
reg core_clk=0,input_bck=0,bck_run=1;always #10 core_clk=~core_clk;
always #160 if(bck_run)input_bck=~input_bck;
reg rst=1,panic=0,input_ws=0,input_sd=0;reg signed[23:0] synth_carrier=0;
wire signed[23:0]sample_out;wire sample_valid,input_stale;
wire[31:0]clip_count,rejected_count,framing_errors_bck,overruns_bck;
vocoder_i2s_frontend #(.COEFF_FILE("COEFF_PATH"),.TIMEOUT_CYCLES(4000),.STEREO_TEST_CARRIER(1))dut(.*);
reg[31:0]v[0:511];integer received=0,i;reg verify=1,saw_timeout=0;
always @(negedge core_clk)if(!rst&&sample_valid)begin
 if(input_stale)begin
  if(sample_out!==0)$fatal(1,"stale output nonzero");saw_timeout=1;
 end else if(verify)begin
  if(received>=128||sample_out!==v[received*4+2][23:0])$fatal(1,"I2S sample %0d got %h expected %h",received,sample_out,v[received*4+2]);
  received=received+1;
 end
end
task bit_tick;input ch,data;begin @(negedge input_bck);input_ws=ch;input_sd=data;@(posedge input_bck);#2;end endtask
task word;input ch;input[23:0]data;integer j;begin
 bit_tick(ch,0);for(j=1;j<32;j=j+1)bit_tick(ch,j<=24?data[24-j]:1'b1);
end endtask
initial begin
 $readmemh("vectors.hex",v);repeat(5)@(negedge input_bck);rst=0;repeat(5)@(negedge input_bck);
 word(1,0);
 for(i=0;i<128;i=i+1)begin word(0,v[i*4][23:0]);word(1,v[i*4+1][23:0]);end
 bit_tick(0,0);repeat(3)bit_tick(0,0);@(negedge input_bck);bck_run=0;
 repeat(300)@(negedge core_clk);
 if(received!=128||clip_count||rejected_count||framing_errors_bck||overruns_bck)$fatal(1,"normal stream counts received=%0d clip=%0d reject=%0d frame=%0d overrun=%0d",received,clip_count,rejected_count,framing_errors_bck,overruns_bck);
 repeat(4100)@(negedge core_clk);
 if(!input_stale||!saw_timeout||sample_out!==0)$fatal(1,"stopped BCK watchdog");
 // Resume the interrupted left slot and deliver a fresh pair without reset.
 verify=0;bck_run=1;
 repeat(27)bit_tick(0,0);word(1,0);bit_tick(0,0);
 repeat(200)@(negedge core_clk);
 if(input_stale||sample_out!==0)$fatal(1,"restart stale=%0d sample=%h frameerrors=%0d",input_stale,sample_out,framing_errors_bck);
 panic=1;repeat(4)@(negedge core_clk);
 if(sample_out!==0||sample_valid!==0)$fatal(1,"panic silence");
 $display("PASS128 exact I2S/CDC/vocoder samples; physical BCK-stop simulation, watchdog zero, resume, panic");$finish;
end
initial begin #10000000;$fatal(1,"timeout");end
endmodule
'''.replace('COEFF_PATH',(S/'coeffs.mem').as_posix())
(O/'tb.sv').write_text(tb)
sources=[S/n for n in ('double_biquad.sv','filterbank.sv','vocoder_mixer.sv','vocoder_core.sv','vocoder_i2s_frontend.sv')]+[B/'experimental/audio_input'/n for n in ('i2s24_rx.v','i2s_input_bridge.v')]+[B/'rtl/audio_cdc_fifo.v']
tools=R/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+str(tools.parent/'lib')+os.pathsep+env['PATH']
c=subprocess.run([str(tools/'iverilog.exe'),'-g2012','-s','tb','-o',str(O/'sim.vvp')]+[str(p) for p in sources]+[str(O/'tb.sv')],env=env,capture_output=True,text=True)
if c.returncode:raise RuntimeError(c.stderr)
r=subprocess.run([str(tools/'vvp.exe'),str(O/'sim.vvp')],cwd=O,env=env,capture_output=True,text=True,timeout=90)
record=dict(status='passed' if r.returncode==0 else 'failed',scope='Digital simulation; stereo test carrier only, no real ADC/microphone/pin acceptance',log=r.stdout+r.stderr,sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[S/'coeffs.mem',Path(__file__)]})
(O/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record,indent=2))
if r.returncode:raise SystemExit(1)
