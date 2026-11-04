`timescale 1ns/1ps
module tb;
reg clk=0,ac=0,run=0,rst=1;always #10 clk=~clk;always #7 if(run)ac=~ac;
wire fault;wire[31:0]losses;
audio_clock_watchdog #(.DIV_BITS(2),.TIMEOUT_CYCLES(50)) dut(clk,ac,rst,fault,losses);
initial begin
 repeat(4)@(negedge clk);rst=0;repeat(80)@(negedge clk);
 if(!fault||losses)$fatal(1,"missing startup clock must stay muted");
 run=1;wait(dut.recovery==1);@(negedge ac);run=0;
 repeat(80)@(negedge clk);if(!fault||losses||dut.recovery)$fatal(1,"isolated pulse train must not qualify recovery");
 run=1;wait(!fault);@(negedge ac);run=0;repeat(4)@(negedge clk);
 if(fault)$fatal(1,"brief gap below timeout");run=1;repeat(40)@(negedge clk);
 @(negedge ac);run=0;repeat(80)@(negedge clk);
 if(!fault||losses!=1)$fatal(1,"first outage");repeat(100)@(negedge clk);
 if(losses!=1)$fatal(1,"outage counted repeatedly");run=1;wait(!fault);
 @(negedge ac);run=0;repeat(80)@(negedge clk);if(!fault||losses!=2)$fatal(1,"second outage");
 rst=1;repeat(4)@(negedge clk);rst=0;repeat(5)@(negedge clk);
 if(!fault||losses)$fatal(1,"reset while audio clock absent");
 $display("PASS audio-clock watchdog:missing startup,three-toggle recovery,brief gap,two outages counted once,stopped-clock reset");$finish;
end
initial begin #100000;$fatal(1,"timeout");end
endmodule
