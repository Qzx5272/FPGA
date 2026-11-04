`timescale 1ns/1ps
module tb_board;
 reg clk=0;always #10 clk=~clk;
 reg rx=1;wire tx,bck,ws,din,pa;
 band_top dut(clk,rx,tx,bck,ws,din,pa);
 wire [7:0] received;wire received_valid;
 uart_rx #(.DIV(50)) capture(clk,dut.engine.rst,tx,received,received_valid);
 reg [7:0] bytes[0:237];integer i,j,k,f,replies=0;
 always @(posedge clk)if(received_valid)begin $fwrite(f,"%02x\n",received);replies=replies+1;end
 task send_packet;input integer base;
 begin
  for(i=0;i<34;i=i+1)begin
   @(negedge clk);rx=0;repeat(50)@(negedge clk);
   for(j=0;j<8;j=j+1)begin rx=bytes[base+i][j];repeat(50)@(negedge clk);end
   rx=1;repeat(50)@(negedge clk);
  end
  repeat(20000)@(negedge clk);
 end endtask
 initial begin
  $readmemh("synth/band/assets/board_fixture.hex",bytes);f=$fopen("synth/band/evidence/board_telemetry.hex","w");
  wait(!dut.engine.rst);repeat(9000)@(negedge clk);
  send_packet(0);if(dut.engine.status_owner!=1||dut.engine.status_epoch!=2)$fatal;
  send_packet(34);if(dut.engine.active_voices==0||dut.engine.deadline_miss!=0)$fatal;
  send_packet(68);if(dut.engine.core.banks[4].unit.allocator.gate!=0)$fatal;
  send_packet(102);if(!dut.engine.playing)$fatal;
  send_packet(136);if(dut.engine.playing||dut.engine.left!=0||dut.engine.right!=0)$fatal;
  send_packet(170);if(dut.engine.receiver.crc_errors!=0||dut.engine.receiver.overflow!=0||replies<170)$fatal;
  send_packet(204);if(!dut.engine.identity_status||replies<204)$fatal(1,"identity telemetry missing");
  $fclose(f);$display("PASS board top: UART take/note/release/play/stop/panic, telemetry, zero parser errors");$finish;
 end
 initial begin #30000000;$fatal;end
endmodule
