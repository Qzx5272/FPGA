`timescale 1ns/1ps
module tb_stable_selector;
 reg clk=0;always #10 clk=~clk;
 reg rst=1;reg [4:0] raw=0;wire [4:0] value;
 stable_selector #(.STABLE_CYCLES(4)) dut(clk,rst,raw,value);
 initial begin
  repeat(2)@(negedge clk);rst=0;
  raw=5'b10101;repeat(2)@(negedge clk);raw=0;
  repeat(8)@(negedge clk);if(value!=0)$fatal(1,"short bounce accepted");
  raw=5'b10011;repeat(5)@(negedge clk);if(value!=0)$fatal(1,"accepted before stable interval");
  repeat(2)@(negedge clk);if(value!=5'b10011)$fatal(1,"stable selector not applied");
  raw=5'b01111;@(negedge clk);raw=5'b00101;@(negedge clk);raw=5'b00110;
  repeat(5)@(negedge clk);if(value!=5'b10011)$fatal(1,"intermediate word accepted");
  repeat(2)@(negedge clk);if(value!=5'b00110)$fatal(1,"final word lost");
  rst=1;@(negedge clk);if(value!=0)$fatal(1,"reset");
  $display("PASS stable selector: short bounce rejected, stable whole-word commit, transition settling, reset");$finish;
 end
endmodule
