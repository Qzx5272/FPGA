`timescale 1ns/1ps
module tb_pads;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,panic=0,sv=0,ready=0;reg [2:0] ch=0;reg [23:0] samples=0;
 wire valid,off,exhausted;wire [6:0] contact,pressure;wire [31:0] serial,overruns;wire [111:0] values;
 pad_frontend #(.CHIPS(2),.PADS(16)) dut(clk,rst,panic,sv,ch,samples,1'b0,7'd0,12'd0,16'd127,1'b0,7'd24,7'd12,valid,ready,off,contact,pressure,serial,values,overruns,exhausted);
 task frame;input [2:0] c;input [11:0] a,b;
 begin @(negedge clk);ch=c;samples={b,a};sv=1;@(negedge clk);sv=0;repeat(6)@(negedge clk);end endtask
 task accept;input o;input [6:0] c;input [31:0] s;
 begin wait(valid);#1;if(off!=o||contact!=c||serial!=s)begin $display("FAIL pad event off=%b contact=%d serial=%d",off,contact,serial);$fatal;end
  @(negedge clk);ready=1;@(negedge clk);ready=0;end endtask
 initial begin
  repeat(3)@(negedge clk);rst=0;
  frame(0,0,0);frame(0,2000,0);accept(0,0,1);
  frame(0,0,0);frame(0,2500,0); // old release must precede the new contact generation
  accept(1,0,1);accept(0,0,2);
  frame(0,0,2000);accept(1,0,2);accept(0,8,1);
  panic=1;@(negedge clk);panic=0;
  frame(0,0,2000);if(valid)$fatal; // held pad must not retrigger after panic
  frame(0,0,0);frame(0,0,3000);accept(0,8,2);
  if(overruns!=0||exhausted)$fatal;
  $display("PASS pad frontend: calibration scaling, hysteresis, release priority, identities, panic inhibit");$finish;
 end
 initial begin #100000;$fatal;end
endmodule
