`timescale 1ns/1ps
module tb_upload;
 reg clk=0;always #10 clk=~clk;
 reg rx=1;wire tx,bck,ws,din,pa;
 band_top dut(clk,rx,tx,bck,ws,din,pa);
 reg [7:0] bytes[0:781];integer p,i,j;
 task packet;input integer number;
 begin
  for(i=0;i<34;i=i+1)begin
   @(negedge clk);rx=0;repeat(50)@(negedge clk);
   for(j=0;j<8;j=j+1)begin rx=bytes[number*34+i][j];repeat(50)@(negedge clk);end
   rx=1;repeat(50)@(negedge clk);
  end
  repeat(100)@(negedge clk);
 end endtask
 initial begin
  $readmemh("synth/band/assets/upload_fixture.hex",bytes);
  wait(!dut.engine.rst);repeat(9000)@(negedge clk);
  for(p=0;p<11;p=p+1)packet(p);
  if(!dut.engine.upload_pending||dut.engine.upload_errors!=0)$fatal(1,"commit");
  packet(11);wait(dut.engine.active_voices==1);
  if(dut.engine.stored_events!=3||dut.engine.stored_duration!=480||dut.engine.core.banks[7].unit.vowel[0]!=4)$fatal(1,"score/vowel activation");
  wait(!dut.engine.playing);repeat(100)@(negedge clk);if(dut.engine.core.banks[7].unit.allocator.gate!=0)$fatal(1,"note release");
  for(p=12;p<23;p=p+1)packet(p);
  if(dut.engine.upload_pending||dut.engine.upload_errors!=1||dut.engine.stored_events!=3||dut.engine.deadline_miss!=0)$fatal(1,"corrupt score retention");
  $display("PASS UART score upload: Python encoder -> CRC parser -> atomic RAM -> vowel/note performance -> release; corrupt replacement retained old score");$finish;
 end
 initial begin #250000000;$fatal(1,"timeout");end
endmodule
