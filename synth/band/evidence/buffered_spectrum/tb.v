`timescale 1ns/1ps
module tb;
reg ac=0,fc=0,dc=0,run=1;always #7 ac=~ac;always #5 fc=~fc;always #19 if(run)dc=~dc;
reg rst=1,pv=0,ren=0,rel=0;reg[10:0]addr=0;reg signed[15:0]l=0,r=0;
wire available,rv;wire signed[15:0]re,im;wire[31:0]frame,last,skips,clips,rejects;wire[16:0]pl,pr;
integer i,count=0,audio_count=0,before_count;reg[31:0]expected[0:2047];
pcm_spectrum_buffered #(.TWIDDLE_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/audio_visual/fft_twiddle_2048.mem"),.WINDOW_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/audio_visual/hann_2048.mem")) dut(
 ac,fc,dc,rst,pv,l,r,ren,addr,rel,available,rv,re,im,frame,last,pl,pr,skips,clips,rejects);
always @(posedge ac)if(pv&&!rst)audio_count=audio_count+1;
always @(posedge fc)if(!rst&&dut.valid&&dut.ready&&count<2048)begin
 if(dut.bin!=count)$fatal(1,"producer order");expected[count]={dut.re,dut.im};count=count+1;
end
initial begin
 repeat(4)@(negedge dc);rst=0;run=0;
 for(i=0;i<2048;i=i+1)begin @(negedge ac);pv=1;l=(i%32<16)?16000:-16000;r=1234;end
 @(negedge ac);l=0;r=0;
 wait(count==2048);repeat(250000)@(negedge fc);
 if(dut.ready||!dut.valid||skips==0)$fatal(1,"reader did not stall analysis with audio continuing");
 before_count=audio_count;run=1;wait(available);@(negedge dc);
 if(frame!=1||last!=2047||pl!=16000||pr!=1234)$fatal(1,"first metadata");
 for(i=0;i<2048;i=i+1)begin
  ren=1;addr=i;@(negedge dc);
  if(!rv||{re,im}!==expected[i])$fatal(1,"bin data %0d",i);
 end
 if(audio_count<=before_count||clips||rejects)$fatal(1,"audio continuity/errors");
 rel=1;@(negedge dc);ren=0;rel=0;
 wait(available);@(negedge dc);
 if(frame!=2||last<=2047)$fatal(1,"second frame identity");
 ren=1;addr=0;@(negedge dc);if(!rv||re||im)$fatal(1,"second frame should be silent");
 run=0;rst=1;pv=0;repeat(4)@(negedge ac);rst=0;
 if(available||rv)$fatal(1,"stopped-reader reset");run=1;repeat(10)@(negedge dc);
 if(available||rv)$fatal(1,"old frame after restart");
 $display("PASS2048 PCM->Hann/FFT->frozen display,all bins exact,three clocks,stalled reader,continued audio,two frames,reset");$finish;
end
initial begin #100000000;$fatal(1,"timeout");end
endmodule
