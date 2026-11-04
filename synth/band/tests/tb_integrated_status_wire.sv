`timescale 1ns/1ps
module tb;
 reg clk=0,rst=1,request=0; always #10 clk=~clk;
 wire tx,valid;wire[7:0]data;
 reg[223:0]payload=224'h0123456789abcdef_23456789abcdef01_456789abcdef0123_6789abcd;
 status_sender #(.UART_DIV(16)) dut(clk,rst,request,payload,tx);
 uart_rx #(.DIV(16)) monitor(clk,rst,tx,data,valid);
 reg[271:0]expected;reg[31:0]crc;integer i,j,received=0;
 always @(posedge clk)if(valid)begin
   if(received<34)begin
     if(data!==expected[received*8+:8])$fatal(1,"bad byte %0d",received);
   end else if(data!==0||received>=38)$fatal(1,"invalid trailing byte");
   received=received+1;
 end
 initial begin
   crc=32'hffffffff;
   for(i=0;i<28;i=i+1)begin
     crc=crc^payload[i*8+:8];
     for(j=0;j<8;j=j+1)crc=crc[0]?(crc>>1)^32'hedb88320:crc>>1;
   end
   expected={~crc,payload,16'h4bb4};
   repeat(4)@(negedge clk);rst=0;request=1;@(negedge clk);request=0;
   repeat(8500)@(negedge clk);
   if(received!=38)$fatal(1,"received %0d",received);
   $display("PASS wire frame, CRC and four trailing guard bytes");$finish;
 end
endmodule
