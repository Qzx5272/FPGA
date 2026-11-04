`timescale 1ns/1ps
module tb_control;
reg clk=0,rst=1,valid=0;
always #10 clk=~clk;
reg [7:0] data=0;
wire [7:0] keys,seq,bright;
wire [2:0] oct;
wire [1:0] tone;
wire [6:0] vol,vel;
wire [15:0] a,r;
wire panic,ok,online,auto_play;
wire [5:0] tempo_code;
control #(.WATCHDOG(1000)) dut(clk,rst,data,valid,keys,seq,bright,oct,tone,vol,vel,a,r,panic,ok,online,auto_play,tempo_code);
integer accepted=0;
always @(posedge clk) if(ok)accepted=accepted+1;
task byte_send;
input [7:0] b;
begin @(negedge clk);data=b;valid=1;@(negedge clk);valid=0;end
endtask
task packet;
input [7:0] mask,flags;
input corrupt;
reg [7:0] checksum;
begin
    checksum=8'd1^mask^8'd4^8'd0^8'd80^8'd32^8'd100^8'd91^8'd0^8'd4^8'd0^flags;
    byte_send(8'ha5);byte_send(8'h5a);byte_send(1);byte_send(mask);byte_send(4);byte_send(0);
    byte_send(80);byte_send(32);byte_send(100);byte_send(91);byte_send(0);byte_send(4);byte_send(0);
    byte_send(flags);byte_send(checksum^corrupt);repeat(4) @(negedge clk);
end
endtask
initial begin
    repeat(4) @(negedge clk);rst=0;
    byte_send(8'hff);byte_send(8'ha5); // repeated header must resynchronize
    packet(8'h55,0,0);
    if(keys!=8'h55 || !online || a!=91 || r!=4 || accepted!=1) begin $display("FAIL valid packet");$finish;end
    packet(8'hff,0,1);
    if(keys!=8'h55 || accepted!=1) begin $display("FAIL checksum");$finish;end
    packet(8'hff,1,0);
    if(keys!=0 || accepted!=2) begin $display("FAIL panic packet");$finish;end
    packet(8'hff,8'd114,0);
    if(!auto_play || tempo_code!=28) begin $display("FAIL transport flags");$finish;end
    repeat(1010) @(negedge clk);
    if(keys!=0 || online || !panic || auto_play) begin $display("FAIL watchdog");$finish;end
    $display("PASS control: atomic state, checksum rejection, resync, panic, watchdog");$finish;
end
endmodule
