`timescale 1ns/1ps
module tb_arranger;
reg clk=0,rst=1,tick=1,panic=0,enabled=0;
reg [5:0] tempo=28;
wire [7:0] keys;
wire [3:0] position;
always #10 clk=~clk;
auto_accompaniment dut(clk,rst,tick,panic,enabled,tempo,keys,position);
integer n;
initial begin
    repeat(3) @(negedge clk);rst=0;enabled=1;
    @(negedge clk);
    if(keys!=8'h15) begin $display("FAIL initial chord");$finish;end
    for(n=1;n<12751;n=n+1) @(negedge clk);
    if(keys!=0 || position!=0) begin $display("FAIL articulation gap");$finish;end
    for(n=12751;n<15000;n=n+1) @(negedge clk);
    if(position!=1) begin $display("FAIL 96 BPM eighth-note duration");$finish;end
    enabled=0;@(negedge clk);
    if(keys!=0 || position!=0) begin $display("FAIL disable");$finish;end
    tempo=40;enabled=1;
    repeat(12000) @(negedge clk);
    if(position!=1) begin $display("FAIL 120 BPM duration");$finish;end
    panic=1;@(negedge clk);
    if(keys!=0 || position!=0) begin $display("FAIL panic");$finish;end
    $display("PASS arranger: exact 96/120 BPM, articulation, stop, panic");$finish;
end
endmodule
