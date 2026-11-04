`timescale 1ns/1ps
module tb;
 reg clk=0,rst=1,valid=0;reg[7:0]data=0;always #10 clk=~clk;
 wire update,online;wire[119:0]mv;wire[31:0]errors;integer commits=0;
 adc_voltage_parser #(.TIMEOUT(1000)) dut(clk,rst,data,valid,update,mv,online,errors);
 always @(negedge clk)if(update)commits=commits+1;
 task send(input string s);integer i;begin
  for(i=0;i<s.len();i=i+1)begin @(negedge clk);data=s[i];valid=1;@(negedge clk);valid=0;end
  repeat(3)@(negedge clk);
 end endtask
 initial begin
  repeat(4)@(negedge clk);rst=0;
  send("junk<v>:0.426,3.269,3.269,3.281,0.953,0.574,0.489,0.479,0.479,0.467\n");
  if(commits!=1||!online||mv[11:0]!=426||mv[47:36]!=3281||mv[119:108]!=467)$fatal(1,"observed frame");
  send("<v>:3.301,0.000,0.000,0.000,0.000,0.000,0.000,0.000,0.000,0.000\n");
  send("<v>:0.12x,0.000\n<v>:0.123,0.456");
  if(commits!=1||mv[11:0]!=426||errors<2)$fatal(1,"bad frame committed");
  send("<v>:0.000,0.001,0.010,0.100,1.000,2.000,3.000,3.300,1.234,2.345\015\n");
  if(commits!=2||mv[95:84]!=3300||mv[119:108]!=2345)$fatal(1,"recovery/CRLF commits=%d mv=%h errors=%d",commits,mv,errors);
  repeat(1005)@(negedge clk);if(online)$fatal(1,"timeout");
  $display("PASS ADC observed payload, atomic commit, invalid range/digit, truncation resync, CRLF, timeout");$finish;
 end
endmodule

