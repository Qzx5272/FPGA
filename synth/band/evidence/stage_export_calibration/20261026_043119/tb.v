`timescale 1ns/1ps
module tb;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,panic=0,sv=0,cfg=0;reg[2:0]ch=0;reg[119:0]samples=0;
 wire[559:0]values;
 stage_pad_frontend dut(.clk(clk),.rst(rst),.panic(panic),.sample_valid(sv),.sample_channel(ch),.samples(samples),
 .config_valid(cfg),.config_channel(7'd0),.config_baseline(12'd0),.config_gain(16'd4096),.config_invert(1'b0),
 .on_threshold(7'd24),.off_threshold(7'd12),.event_ready(1'b0),.pressure_values(values));
 task frame(input[2:0]channel,input[11:0]first,last);
 begin @(negedge clk);ch=channel;samples=0;samples[11:0]=first;samples[7*12+:12]=last;samples[9*12+:12]=4095;sv=1;
 @(negedge clk);sv=0;wait(!dut.busy);repeat(2)@(negedge clk);end endtask
 initial begin
  repeat(3)@(negedge clk);rst=0;
  frame(0,3990,0);if(values[6:0]!=5)$fatal(1,"saved inverted pad0 default lost");
  frame(7,0,100);if(values[63*7+:7]!=25||values[79*7+:7]!=126)$fatal(1,"pad63/default lane calibration lost");
  @(negedge clk);cfg=1;@(negedge clk);cfg=0;
  frame(0,20,0);if(values[6:0]!=20)$fatal(1,"live calibration override lost");
  panic=1;@(negedge clk);panic=0;
  frame(0,20,0);if(values[6:0]!=20)$fatal(1,"panic erased live calibration");
  rst=1;repeat(2)@(negedge clk);rst=0;
  frame(0,3990,0);if(values[6:0]!=5)$fatal(1,"reset failed to restore saved calibration");
  frame(7,0,100);if(values[63*7+:7]!=25)$fatal(1,"reset failed pad63 saved calibration");
  $display("PASS actual exported calibration:pad0 inversion,pad63 gain,default channel79,live override,panic preserve,reset saved defaults");$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
