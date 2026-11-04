`timescale 1ns/1ps
module tb_singer_uart;
 reg clk=0;always #10 clk=~clk;
 reg rx=1;wire tx,bck,ws,din,pa,gate;wire[6:0]note;
 wire[31:0]drops,under;reg[31:0]noise=32'h12345678;
 always @(posedge clk)if(dut.engine.sample_tick)noise<={noise[30:0],noise[31]^noise[21]^noise[1]^noise[0]};
 reg mic_bck=0,mic_ws=0,mic_sd=0,mic_run=1;
 wire mic_stale;wire[31:0]mic_received;integer before_frames=0,before_input=0,pcm_frames=0;
 reg [9:0] adc_dout=0;wire adc_cs,adc_sclk,adc_din;wire [3:0] seat_led;
 reg [3:0] pedals=0;wire [15:0] deferred_returns;reg stage_checked=0;
 reg [11:0] lead_pressure=0,drum_pressure=0;integer edges=0,adc_i,raw;
 reg [31:0] adc_command=0;reg [2:0] selected=0;
 always @(negedge adc_cs)begin edges=0;adc_command=0;adc_dout=0;end
 always @(posedge adc_sclk)if(!adc_cs)begin edges=edges+1;adc_command={adc_command[30:0],adc_din};end
 always @(negedge adc_sclk)if(!adc_cs)begin
  if(edges==18)selected=adc_command[2:0];
  for(adc_i=0;adc_i<10;adc_i=adc_i+1)begin
   raw=selected==0?(adc_i==0?lead_pressure:adc_i==2?drum_pressure:0):0;
   adc_dout[adc_i]=(edges>=20&&edges<32)?((raw>>(31-edges))&1):0;
  end
 end
 initial begin
  wait(!dut.engine.rst);repeat(30000)@(negedge clk);
  pedals=1;lead_pressure=2500;drum_pressure=3500;wait(seat_led[1:0]==3);
  if(dut.engine.core.ownership.owners[6]!=17||dut.engine.core.ownership.owners[0]!=18)$fatal(1,"stage local ownership");
  lead_pressure=0;wait(!seat_led[0]);wait(deferred_returns[6]);
  // Local handshake precedes the core auth/allocator pipeline, bounded here.
  repeat(100)@(negedge clk);
  if(dut.engine.core.banks[6].unit.allocator.gate!=0)$fatal(1,"pedal must not hold audio gate");
  pedals=0;wait(!deferred_returns[6]);repeat(20)@(negedge clk);
  if(!dut.engine.core.ownership.returns[6])$fatal(1,"stage pedal return");
  drum_pressure=0;wait(seat_led==0);stage_checked=1;
 end
 reg display_clk=0,display_run=1,display_read=0,display_release=0;reg[8:0]display_address=0;
 always #7 if(display_run)display_clk=~display_clk;
 wire display_available,display_valid;wire signed[15:0]display_left,display_right;
 wire[16:0]display_peak_left,display_peak_right;wire[31:0]display_last,display_frame,display_skipped;
 reg[31:0]expected_pcm[0:511];integer expected_count=0,expected_peak_l=0,expected_peak_r=0,vm,vi,visual_before,visual_nonzero=0;
 reg visual_checked=0;
 always @(posedge clk)begin
  if(dut.engine.rst||dut.engine.panic)begin expected_count=0;expected_peak_l=0;expected_peak_r=0;end
  else if(dut.engine.pcm_valid&&expected_count<512)begin
   expected_pcm[expected_count]={dut.engine.pcm_left,dut.engine.pcm_right};expected_count=expected_count+1;
   vm=$signed(dut.engine.pcm_left);if(vm<0)vm=-vm;if(vm>expected_peak_l)expected_peak_l=vm;
   vm=$signed(dut.engine.pcm_right);if(vm<0)vm=-vm;if(vm>expected_peak_r)expected_peak_r=vm;
  end
 end
 initial begin
  wait(display_available);#1;
  if(expected_count!=512||display_last!=511||display_frame!=1||display_peak_left!=expected_peak_l||display_peak_right!=expected_peak_r)$fatal(1,"visual snapshot metadata");
  @(negedge display_clk);display_run=0;visual_before=pcm_frames;
  repeat(40*1042)@(negedge clk);
  if(pcm_frames-visual_before<39||display_skipped<39||drops||under||dut.engine.deadline_miss)$fatal(1,"stopped display clock interrupted audio");
  display_run=1;
  for(vi=0;vi<512;vi=vi+1)begin
   @(negedge display_clk);display_read=1;display_address=vi;@(negedge display_clk);
   if(!display_valid||{display_left,display_right}!==expected_pcm[vi])$fatal(1,"visual PCM mismatch %0d",vi);
   if(display_left||display_right)visual_nonzero=visual_nonzero+1;display_read=0;
  end
  if(!visual_nonzero)$fatal(1,"visual snapshot only silence");
  @(negedge display_clk);display_release=1;@(negedge display_clk);display_release=0;
  if(display_available||display_valid)$fatal(1,"visual release");
  visual_checked=1;
 end
 band_stage_visual_top #(.PEDAL_STABLE_CYCLES(3),.COEFF_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/vocoder/ported/coeffs.mem"),.MIC_TIMEOUT(4000)) dut(
 .clk(clk),.uart_rx_pin(rx),.uart_tx_pin(tx),.HP_BCK(bck),.HP_WS(ws),.HP_DIN(din),.PA_EN(pa),
 .mic_bck(mic_bck),.mic_ws(mic_ws),.mic_sd(mic_sd),.microphone_stale(mic_stale),
 .adc_dout(adc_dout),.adc_cs_n(adc_cs),.adc_sclk(adc_sclk),.adc_din(adc_din),
 .play_button(1'b0),.stop_button(1'b0),.panic_button(1'b0),.root(4'd0),.minor_mode(1'b0),
 .pedal_raw(pedals),.pedal_down(),.seat_led(seat_led),.deferred_returns(deferred_returns),
 .display_clk(display_clk),.display_read(display_read),.display_release(display_release),.display_address(display_address),
 .display_available(display_available),.display_valid(display_valid),.display_left(display_left),.display_right(display_right),
 .display_peak_left(display_peak_left),.display_peak_right(display_peak_right),.display_last_sample(display_last),.display_frame(display_frame),.display_skipped(display_skipped),
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
  $readmemh("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/evidence/visual_stage_chain/fixture.hex",bytes);wait(!dut.engine.rst);repeat(9000)@(negedge clk);
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
  wait(visual_checked);send_packet(7);if(gate||dut.engine.left!=0||dut.engine.right!=0||dut.engine.playing)$fatal(1,"Panic failed");
  if(display_available||display_valid)$fatal(1,"panic did not clear display");send_packet(8);if(!dut.engine.identity_status||dut.engine.receiver.crc_errors||dut.engine.receiver.overflow)$fatal(1,"Identity/parser");
  $display("PASS ADC two-seat/pedal plus microphone top I2S/CDC/singer/DAC,clockloss singer-only fade while score/PCM continue,recovery; singer UART:owner2 take,retrigger,stale/wrong-owner off,matched release,PCM+DAC activity,panic,identity;peak=%0d",peak);if(!stage_checked)$fatal(1,"stage scenario incomplete");if(!visual_checked)$fatal(1,"visual scenario incomplete");$display("PASS512 actual synthesized stereo PCM samples,exact peaks,display clock stopped40frames with audio continuing,release andpanic invalidate snapshot");$finish;
 end
 initial begin #30000000;$fatal(1,"Timeout");end
endmodule
