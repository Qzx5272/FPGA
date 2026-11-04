`timescale 1ns/1ps
module tb;
reg clk=0;always #10 clk=~clk;
reg rst=1,raw=0;wire pulse;integer count=0;
button_pulse dut(clk,rst,raw,pulse);
always @(posedge clk)begin #1;if(pulse)count=count+1;end
initial begin
 repeat(4)@(negedge clk);rst=0;
 // A brief disturbance is rejected at the production setting.
 raw=1;repeat(100)@(negedge clk);raw=0;repeat(250010)@(negedge clk);
 if(count!=0)$fatal(1,"short glitch accepted");
 raw=1;repeat(249999)@(negedge clk);
 if(count!=0)$fatal(1,"press accepted before default5ms window");
 repeat(6)@(negedge clk);
 if(count!=1)$fatal(1,"default press not accepted");
 repeat(300)@(negedge clk);if(count!=1)$fatal(1,"held key repeated");
 raw=0;repeat(250010)@(negedge clk);if(count!=1)$fatal(1,"release generated press");
 raw=1;repeat(250010)@(negedge clk);if(count!=2)$fatal(1,"second press failed");
 rst=1;repeat(5)@(negedge clk);raw=0;rst=0;repeat(250010)@(negedge clk);
 if(count!=2)$fatal(1,"reset generated phantom pulse");
 $display("PASS default250000cycles: short glitch,5ms threshold,long hold,release,repress,reset");$finish;
end
endmodule
