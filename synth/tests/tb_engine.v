`timescale 1ns/1ps
module tb_engine;
reg clk=0,rst=1,tick=0,panic=0;
always #10 clk=~clk;
reg [7:0] keys=0,brightness=0;
reg [2:0] octave=4;
reg [1:0] tone=0;
reg [6:0] volume=127,velocity=127;
reg [15:0] attack=1365,release_s=14;
wire signed [15:0] sample;
wire [3:0] voices;
engine dut(clk,rst,tick,panic,keys,brightness,octave,tone,volume,velocity,attack,release_s,sample,voices);
integer f,i;
task frame;
begin
    @(negedge clk);tick=1; @(negedge clk);tick=0;
    repeat(42) @(negedge clk);
end
endtask
initial begin
    f=$fopen("synth/test-output/engine_samples.csv","w");
    repeat(4) @(negedge clk);rst=0;
    keys=8'h20; // A4, pure sine
    for(i=0;i<24000;i=i+1) begin frame; $fdisplay(f,"0,%d",sample); end
    if(voices!=1) begin $display("FAIL single voice");$finish;end
    keys=8'hff; brightness=255;tone=1;
    for(i=0;i<24000;i=i+1) begin frame; $fdisplay(f,"1,%d",sample); end
    if(voices!=8) begin $display("FAIL eight voices");$finish;end
    keys=0;
    for(i=0;i<6000;i=i+1) begin frame; $fdisplay(f,"2,%d",sample); end
    if(voices!=0 || sample!=0) begin $display("FAIL release");$finish;end
    keys=1;tone=2;
    for(i=0;i<13000;i=i+1) begin frame; $fdisplay(f,"3,%d",sample); end
    if(sample!=0 || voices!=0) begin $display("FAIL pluck decay");$finish;end
    keys=3;tone=0;repeat(100) frame;
    @(negedge clk);panic=1; @(negedge clk);panic=0;
    if(sample!=0) begin $display("FAIL panic");$finish;end
    $fclose(f); $display("PASS engine: single/eight voices, release, pluck, panic");$finish;
end
endmodule
