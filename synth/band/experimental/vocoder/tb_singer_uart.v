`timescale 1ns/1ps
module tb_singer_uart;
 reg clk=0;always #10 clk=~clk;
 reg rx=1;wire tx,bck,ws,din,pa,gate;wire[6:0]note;
 wire[31:0]drops,under;reg[31:0]noise=32'h12345678;
 always @(posedge clk)if(dut.sample_tick)noise<={noise[30:0],noise[31]^noise[21]^noise[1]^noise[0]};
 band_singer_board_engine #(.COEFF_FILE("COEFFICIENT_PATH")) dut(
 .clk(clk),.uart_rx_pin(rx),.uart_tx_pin(tx),.HP_BCK(bck),.HP_WS(ws),.HP_DIN(din),.PA_EN(pa),
 .adc_dout(10'd0),.local_play(1'b0),.local_stop(1'b0),.local_panic(1'b0),.local_root(4'd0),.local_minor(1'b0),.external_sample_tick(1'b0),
 .microphone_sample(noise[23:0]),.singer_mix(7'd100),.singer_gate(gate),.singer_note(note),.dac_dropped(drops),.dac_underruns(under));
 reg[7:0]bytes[0:305];integer i,j,peak=0,mag,wire_ones=0;
 always @(posedge clk)if(dut.audio_valid)begin mag=$signed(dut.left);if(mag<0)mag=-mag;if(mag>peak)peak=mag;end
 always @(posedge bck)if(!dut.rst&&din)wire_ones=wire_ones+1;
 task send_packet(input integer index);begin
  for(i=0;i<34;i=i+1)begin
   @(negedge clk);rx=0;repeat(50)@(negedge clk);
   for(j=0;j<8;j=j+1)begin rx=bytes[index*34+i][j];repeat(50)@(negedge clk);end
   rx=1;repeat(50)@(negedge clk);
  end
  repeat(20000)@(negedge clk);
 end endtask
 initial begin
  $readmemh("FIXTURE_PATH",bytes);wait(!dut.rst);repeat(9000)@(negedge clk);
  send_packet(0);if(dut.status_owner!=2||dut.status_epoch!=2)$fatal(1,"Singer take");
  send_packet(1);if(!gate||note!=60)$fatal(1,"Singer note");
  send_packet(2);if(!gate)$fatal(1,"Replacement note");
  send_packet(3);if(!gate)$fatal(1,"Stale off killed replacement");
  send_packet(4);if(!gate)$fatal(1,"Wrong owner killed singer");
  if(dut.core.banks[7].unit.allocator.active!=0)$fatal(1,"Duplicated choir");
  if(peak==0||wire_ones==0||drops||under||dut.deadline_miss)$fatal(1,"Singer audio/queue error");
  send_packet(5);if(gate)$fatal(1,"Matching off failed");
  send_packet(6);if(!gate)$fatal(1,"Restart failed");
  send_packet(7);if(gate||dut.dac.queued_frames!=0&&dut.left!=0)$fatal(1,"Panic failed");
  send_packet(8);if(!dut.identity_status||dut.receiver.crc_errors||dut.receiver.overflow)$fatal(1,"Identity/parser");
  $display("PASS singer UART:owner2 take,retrigger,stale/wrong-owner off,matched release,PCM+DAC activity,panic,identity;peak=%0d",peak);$finish;
 end
 initial begin #30000000;$fatal(1,"Timeout");end
endmodule
