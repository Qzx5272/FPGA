`timescale 1ns/1ps
module tb_singer_uart;
 reg clk=0;always #10 clk=~clk;
 reg rx=1;wire tx,bck,ws,din,pa,gate;wire[6:0]note;
 wire[31:0]drops,under;reg[31:0]noise=32'h12345678;
 always @(posedge clk)if(dut.engine.sample_tick)noise<={noise[30:0],noise[31]^noise[21]^noise[1]^noise[0]};
 reg mic_bck=0,mic_ws=0,mic_sd=0,mic_run=1;
 wire mic_stale;wire[31:0]mic_received;integer before_frames=0,before_input=0,pcm_frames=0;
 band_microphone_top #(.COEFF_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/vocoder/ported/coeffs.mem"),.MIC_TIMEOUT(4000)) dut(
 .clk(clk),.uart_rx_pin(rx),.uart_tx_pin(tx),.HP_BCK(bck),.HP_WS(ws),.HP_DIN(din),.PA_EN(pa),
 .mic_bck(mic_bck),.mic_ws(mic_ws),.mic_sd(mic_sd),.microphone_stale(mic_stale),
 .mic_received(mic_received),.mic_repeated(),.mic_skipped(),.mic_timeouts());
 assign gate=dut.engine.singer_gate;assign note=dut.engine.singer_note;
 assign drops=dut.engine.dac_dropped;assign under=dut.engine.dac_underruns;
 always #160 if(mic_run)mic_bck=~mic_bck;
 always @(posedge clk)if(dut.engine.audio_valid)pcm_frames=pcm_frames+1;
 task mic_bit(input ch,data);begin @(negedge mic_bck);mic_ws=ch;mic_sd=data;@(posedge mic_bck);#2;end endtask
 task mic_word(input ch,input[23:0]data);integer k;begin
  mic_bit(ch,0);for(k=1;k<32;k=k+1)mic_bit(ch,k<=24?data[24-k]:1'b0);
 end endtask
 initial begin wait(!dut.engine.rst);repeat(5)@(negedge mic_bck);mic_word(1,0);
  forever begin mic_word(0,noise[23:0]);mic_word(1,0);end
 end
 reg[7:0]bytes[0:339];integer i,j,peak=0,mag,wire_ones=0;
 always @(posedge clk)if(dut.engine.audio_valid)begin mag=$signed(dut.engine.left);if(mag<0)mag=-mag;if(mag>peak)peak=mag;end
 always @(posedge bck)if(!dut.engine.rst&&din)wire_ones=wire_ones+1;
 task send_packet(input integer index);begin
  for(i=0;i<34;i=i+1)begin
   @(negedge clk);rx=0;repeat(50)@(negedge clk);
   for(j=0;j<8;j=j+1)begin rx=bytes[index*34+i][j];repeat(50)@(negedge clk);end
   rx=1;repeat(50)@(negedge clk);
  end
  repeat(20000)@(negedge clk);
 end endtask
 initial begin
  $readmemh("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/evidence/microphone_top_chain/fixture.hex",bytes);wait(!dut.engine.rst);repeat(9000)@(negedge clk);
  send_packet(0);if(dut.engine.status_owner!=2||dut.engine.status_epoch!=2)$fatal(1,"Singer take");
  send_packet(1);if(!gate||note!=60)$fatal(1,"Singer note");
  send_packet(2);if(!gate)$fatal(1,"Replacement note");
  send_packet(3);if(!gate)$fatal(1,"Stale off killed replacement");
  send_packet(4);if(!gate)$fatal(1,"Wrong owner killed singer");
  if(dut.engine.core.banks[7].unit.allocator.active!=0)$fatal(1,"Duplicated choir");
  if(peak==0||wire_ones==0||drops||under||dut.engine.deadline_miss)$fatal(1,"Singer audio/queue error");
  send_packet(9);if(!dut.engine.playing)$fatal(1,"Band did not start");
  @(negedge mic_bck);mic_run=0;before_frames=pcm_frames;
  repeat(170*1042)@(negedge clk);
  if(!mic_stale||dut.engine.core.electronic_singer.audio.smooth_gain!=0||!gate)$fatal(1,"Mic-only fade failed");
  if(!dut.engine.playing||pcm_frames-before_frames<165||drops||under||dut.engine.deadline_miss)$fatal(1,"Mic loss interrupted band");
  before_input=mic_received;mic_run=1;repeat(12000)@(negedge clk);
  if(mic_stale||mic_received<=before_input||dut.engine.core.electronic_singer.audio.smooth_gain==0)$fatal(1,"Mic resume failed");
  send_packet(5);if(gate)$fatal(1,"Matching off failed");
  send_packet(6);if(!gate)$fatal(1,"Restart failed");
  send_packet(7);if(gate||dut.engine.left!=0||dut.engine.right!=0||dut.engine.playing)$fatal(1,"Panic failed");
  send_packet(8);if(!dut.engine.identity_status||dut.engine.receiver.crc_errors||dut.engine.receiver.overflow)$fatal(1,"Identity/parser");
  $display("PASS microphone top I2S/CDC/singer/DAC,clockloss singer-only fade while score/PCM continue,recovery; singer UART:owner2 take,retrigger,stale/wrong-owner off,matched release,PCM+DAC activity,panic,identity;peak=%0d",peak);$finish;
 end
 initial begin #30000000;$fatal(1,"Timeout");end
endmodule
