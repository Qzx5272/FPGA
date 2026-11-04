"""Decode pins of async queued I2S: jitter, starvation, overflow, stopped clock reset."""
from pathlib import Path
import os,subprocess,json,hashlib
r=Path(__file__).resolve().parents[3];b=r/'synth/band';o=b/'evidence/i2s24_queue';o.mkdir(exist_ok=True)
tb='''`timescale 1ns/1ps
module tb;
reg clk=0,ac=0,run=1;always #10 clk=~clk;always #20.345052 if(run)ac=~ac;
reg rst=1,panic=0,valid=0,produce=1,check_audio=1;
reg signed[23:0]l=0,r=0;wire ready,tick,bck,ws,sd;wire[31:0]drops,under,under_core;
i2s24_queue_bridge dut(clk,ac,rst,panic,valid,l,r,ready,tick,bck,ws,sd,drops,under,under_core);
integer cycle=0,n=0,seen=0,slot=0,j,expected_drops=0;
reg previous_ws=1;reg[23:0]word=0,left_word=0,expected_l,expected_r;
always @(negedge clk)if(!rst&&produce)begin
 valid=0;
 if(n<32&&cycle==n*1042+(n%2?1094:200))begin
  if(!ready)$fatal(1,"jitter FIFO full");valid=1;l=24'h800001+n;r=24'h7ffffe-n;n=n+1;
 end
 cycle=cycle+1;
end
always @(posedge clk)if(!rst&&!panic&&valid&&!ready)expected_drops=expected_drops+1;
always @(posedge bck)if(!rst&&!panic&&check_audio)begin
 if(ws!=previous_ws)begin slot=0;previous_ws=ws;end else slot=slot+1;
 if(slot>=1&&slot<=24)word={word[22:0],sd};
 else if(sd!==0)$fatal(1,"nonzero padding");
 if(slot==24)begin
  if(!ws)left_word=word;
  else if({left_word,word}!=0)begin
   expected_l=24'h800001+seen;expected_r=24'h7ffffe-seen;
   if({left_word,word}!=={expected_l,expected_r})$fatal(1,"frame %d got %h expected %h",seen,{left_word,word},{expected_l,expected_r});
   seen=seen+1;
  end else if(seen>0&&seen<32)$fatal(1,"jitter inserted silence");
 end
end
task push(input integer k);begin
 @(negedge clk);while(!ready)@(negedge clk);valid=1;l=24'h800001+k;r=24'h7ffffe-k;
 @(negedge clk);valid=0;
end endtask
initial begin
 repeat(6)@(negedge clk);rst=0;
 wait(seen==32);if(drops||under)$fatal(1,"jitter counters");produce=0;valid=0;
 wait(under>=2);push(32);push(33);wait(seen==34);check_audio=0;
 repeat(10)@(negedge clk);if(under_core!=under)$fatal(1,"core underrun event synchronization");
 // Stop serializer, reset both domains, then deliberately overflow the FIFO.
 @(negedge ac);run=0;panic=1;repeat(3)@(negedge clk);panic=0;
 repeat(4)@(negedge clk);if(bck||ws||sd||drops)$fatal(1,"stopped audio reset/gating");
 expected_drops=0;
 for(j=0;j<20;j=j+1)begin @(negedge clk);valid=1;l=j;r=-j;end
 @(negedge clk);valid=0;
 if(drops==0||drops!=expected_drops)$fatal(1,"overflow accounting");
 panic=1;repeat(3)@(negedge clk);panic=0;run=1;
 repeat(6)@(negedge ac);if(drops||under||dut.count)$fatal(1,"reset retained queued frames");
 $display("PASS I2S queue:32 exact stereo jitter frames200/1094cycles,zero inserted silence,starvation recovery,overflow accounting,stopped-clock panic");$finish;
end
initial begin #3000000;$fatal(1,"timeout seen=%0d",seen);end
endmodule
'''
(o/'tb.v').write_text(tb);binary=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
files=[b/'rtl/audio_cdc_fifo.v',b/'rtl/i2s24_tx.v',b/'experimental/audio_input/i2s24_queue_bridge.v',o/'tb.v'];logs=[];ok=True
for command in ([str(binary/'iverilog.exe'),'-g2012','-s','tb','-o',str(o/'test.vvp'),*map(str,files)],[str(binary/'vvp.exe'),str(o/'test.vvp')]):
 p=subprocess.run(command,env=env,capture_output=True,text=True,timeout=30);logs.append(p.stdout+p.stderr)
 if p.returncode:ok=False;break
record=dict(status='passed' if ok and 'PASS' in logs[-1] else 'failed',scope='Queued standard I2S24 CDC/serializer RTL pin decode; no stage integration,PLL,external DAC,timing or physical acceptance',sources={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files+[Path(__file__)]},log=''.join(logs))
(o/'result.json').write_text(json.dumps(record,indent=2));print(record['log']);raise SystemExit(record['status']!='passed')
