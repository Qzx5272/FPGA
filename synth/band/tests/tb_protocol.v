`timescale 1ns/1ps
module tb_protocol;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,bv=0,ready=0;reg [7:0] data=0;
 wire valid,panic;wire [223:0] payload;wire [31:0] crc_errors,overflow;
 reg [7:0] fixture[0:67];integer i;integer panics=0;
 event_receiver dut(clk,rst,data,bv,valid,ready,payload,panic,crc_errors,overflow);
 always @(posedge clk)if(panic)panics=panics+1;
 task byte_send;input [7:0] b;
 begin @(negedge clk);data=b;bv=1;@(negedge clk);bv=0;@(negedge clk);end endtask
 task packet;input integer base;input corrupt;
 begin
  for(i=0;i<34;i=i+1)byte_send(fixture[base+i]^(corrupt&&i==33?8'd1:8'd0));
  // Qualified PC transport appends 64 out-of-frame zero guard bytes.
  // They must not create events or alter the CRC/overflow/panic behavior.
  for(i=0;i<64;i=i+1)byte_send(8'd0);
 end endtask
 initial begin
  $readmemh("synth/band/assets/protocol_fixture.hex",fixture);
  repeat(3)@(negedge clk);rst=0;
  packet(0,0);if(!valid||payload[31:24]!=6||payload[47:40]!=69||payload[127:96]!=456)$fatal;
  packet(34,0);if(valid||panics!=1)$fatal;
  packet(0,1);if(valid||crc_errors!=1)$fatal;
  packet(0,0);packet(0,0);if(overflow!=1||panics!=2||valid)$fatal;
  ready=1;packet(0,0);repeat(3)@(negedge clk);if(valid)$fatal;
  $display("PASS V4 receiver: golden Python CRC, payload, corrupt frame, overflow-safe panic, pending bypass");$finish;
 end
 initial begin #100000;$fatal;end
endmodule
