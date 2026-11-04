`timescale 1ns/1ps
module tb;
 reg clk=0,rst=1,iv=0,ready=0;reg[223:0]ip=0;wire ir,valid;wire[223:0]payload;
 always #10 clk=~clk;
 event_packet_buffer dut(clk,rst,iv,ir,ip,valid,ready,payload);
 integer sent=0,received=0,cycle=0;reg[31:0]random=32'h87654321;reg stalled=0;reg[223:0]prior;
 always @(posedge clk)if(!rst)begin
  if(stalled&&payload!==prior)$fatal(1,"payload changed under backpressure");
  if(valid&&ready)begin if(payload!==received)$fatal(1,"ordering %d %d",payload,received);received=received+1;end
  if(iv&&ir)sent=sent+1;
  stalled=valid&&!ready;prior=payload;
 end
 initial begin
  repeat(4)@(negedge clk);rst=0;
  while(received<1000)begin
   random={random[30:0],random[31]^random[21]^random[1]^random[0]};
   ready=random[0];iv=sent<1000&&random[1];ip=sent;cycle=cycle+1;
   @(negedge clk);if(cycle>10000)$fatal(1,"progress");
  end
  iv=1;ip=1000;ready=0;@(negedge clk);iv=0;repeat(5)@(negedge clk);
  rst=1;@(negedge clk);if(valid)$fatal(1,"panic flush");
  $display("PASS elastic event pipeline: 1000 ordered packets, randomized backpressure, stable payload, panic flush");$finish;
 end
endmodule
