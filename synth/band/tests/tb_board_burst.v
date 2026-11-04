`timescale 1ns/1ps
module tb_board_burst;
 reg clk=0;always #10 clk=~clk;
 reg rx=1;wire tx,bck,ws,din,pa;
 band_top dut(clk,rx,tx,bck,ws,din,pa);
 wire [7:0] received;wire received_valid;
 uart_rx #(.DIV(50)) capture(clk,dut.engine.rst,tx,received,received_valid);
 reg [7:0] bytes[0:237];integer i,j,k,f,n=0;
 always @(posedge clk)if(received_valid)begin $fwrite(f,"%02x\n",received);n=n+1;end
 initial begin
  $readmemh("synth/band/assets/board_fixture.hex",bytes);f=$fopen("synth/band/evidence/board_burst.hex","w");
  wait(!dut.engine.rst);repeat(9000)@(negedge clk);
  for(k=0;k<100;k=k+1)for(i=204;i<238;i=i+1)begin
   @(negedge clk);rx=0;repeat(50)@(negedge clk);
   for(j=0;j<8;j=j+1)begin rx=bytes[i][j];repeat(50)@(negedge clk);end
   rx=1;repeat(50)@(negedge clk);
  end
  repeat(40000)@(negedge clk);$fclose(f);
  if(n<34||dut.engine.crc_errors!=0||dut.engine.overflow!=0)$fatal;
  $display("PASS board burst stimulus finished, bytes=%0d",n);$finish;
 end
 initial begin #50000000;$fatal;end
endmodule
