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
 reg analysis_clk=0,analysis_run=1,spectrum_ready=0;always #13 if(analysis_run)analysis_clk=~analysis_clk;
 reg display_clk=0,display_run=1,display_release=0;
 always #17 if(display_run)display_clk=~display_clk;
 wire display_available;wire[31:0]rejected_bins;integer frames_before;
 wire spectrum_valid;reg[10:0]spectrum_bin=0;wire signed[15:0]spectrum_real,spectrum_imag;
 wire[31:0]spectrum_frame,spectrum_last,visual_skipped,fft_clips;wire[16:0]peak_left,peak_right;
 integer captured=0,spectrum_checked=0,vi,pcm_file,bin_file;reg signed[15:0]hold_re,hold_im;
 initial begin pcm_file=$fopen("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/evidence/workstation_chain/pcm.txt","w");bin_file=$fopen("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/evidence/workstation_chain/bins.txt","w");end
 always @(posedge clk)if(!dut.rst&&!dut.panic&&dut.pcm_valid&&captured<2048)begin
  $fwrite(pcm_file,"%0d\n",$signed(dut.pcm_left));captured=captured+1;
 end
 initial begin
  wait(display_available);@(negedge display_clk);
  if(captured!=2048||spectrum_frame!=1||spectrum_last!=2047)$fatal(1,"buffered window identity");
  display_run=0;frames_before=pcm_frames;repeat(40*1042)@(negedge clk);
  if(pcm_frames-frames_before<39||drops||under||dut.engine.deadline_miss)$fatal(1,"stopped display interrupted audio");
  display_run=1;
  for(vi=0;vi<2048;vi=vi+1)begin
   @(negedge display_clk);spectrum_bin=vi;spectrum_ready=1;@(negedge display_clk);
   if(!spectrum_valid||spectrum_frame!=1||spectrum_last!=2047)$fatal(1,"buffered read identity");
   $fwrite(bin_file,"%0d %0d %0d\n",vi,$signed(spectrum_real),$signed(spectrum_imag));spectrum_ready=0;
  end
  display_release=1;@(negedge display_clk);display_release=0;
  if(display_available||spectrum_valid||rejected_bins||fft_clips||drops||under||dut.engine.deadline_miss)$fatal(1,"buffered release/errors");
  $fclose(pcm_file);$fclose(bin_file);spectrum_checked=1;
 end
 reg audio_clk=0,audio_run=1;always #20.345052 if(audio_run)audio_clk=~audio_clk;
 reg[47:0]expected_frames[0:4095];reg[47:0]expected_wire;reg[23:0]word=0;
 integer written=0,read_index=0,decoded=0,bit_slot=0;reg previous_ws=1,wire_active=0;
 always @(posedge clk)begin
  if(dut.rst||dut.panic||dut.audio_stop)written=0;
  else if(dut.pcm_valid)begin expected_frames[written]={dut.pcm_left,8'd0,dut.pcm_right,8'd0};written=written+1;end
 end
 always @(posedge audio_clk)begin
  if(dut.output_audio.audio_reset[1])begin read_index=0;wire_active=0;previous_ws=1;bit_slot=0;end
  else if(dut.output_audio.pop)begin
   if(read_index>=written)$fatal(1,"I2S played an unproduced frame");
   expected_wire=expected_frames[read_index];read_index=read_index+1;wire_active=1;
  end
 end
 always @(posedge bck)if(!dut.rst&&!dut.panic&&!dut.audio_stop)begin
  if(ws!=previous_ws)begin bit_slot=0;previous_ws=ws;end else bit_slot=bit_slot+1;
  if(bit_slot>=1&&bit_slot<=24)word={word[22:0],din};
  else if(din!==0)$fatal(1,"I2S padding");
  if(bit_slot==24&&wire_active)begin
   if(word!==(ws?expected_wire[23:0]:expected_wire[47:24]))$fatal(1,"I2S fullstage frame mismatch");
   decoded=decoded+1;
  end
 end
 band_workstation_top #(.TWIDDLE_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/audio_visual/fft_twiddle_2048.mem"),.WINDOW_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/audio_visual/hann_2048.mem"),.PEDAL_STABLE_CYCLES(3),.COEFF_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/vocoder/ported/coeffs.mem"),.MIC_TIMEOUT(4000)) dut(
 .clk(clk),.uart_rx_pin(rx),.uart_tx_pin(tx),.audio_clk(audio_clk),.i2s_bck(bck),.i2s_ws(ws),.i2s_sd(din),.i2s_dropped(),.i2s_underruns(),
 .mic_bck(mic_bck),.mic_ws(mic_ws),.mic_sd(mic_sd),.microphone_stale(mic_stale),
 .adc_dout(adc_dout),.adc_cs_n(adc_cs),.adc_sclk(adc_sclk),.adc_din(adc_din),
 .play_button(1'b0),.stop_button(1'b0),.panic_button(1'b0),.root(4'd0),.minor_mode(1'b0),
 .pedal_raw(pedals),.pedal_down(),.seat_led(seat_led),.deferred_returns(deferred_returns),
 .analysis_clk(analysis_clk),.display_clk(display_clk),.display_read(spectrum_ready),.display_release(display_release),.display_available(display_available),.rejected_bins(rejected_bins),.spectrum_valid(spectrum_valid),
 .display_address(spectrum_bin),.spectrum_real(spectrum_real),.spectrum_imag(spectrum_imag),
 .spectrum_frame(spectrum_frame),.spectrum_last_sample(spectrum_last),.visualization_skipped(visual_skipped),.fft_clips(fft_clips),
 .spectrum_peak_left(peak_left),.spectrum_peak_right(peak_right),.mic_received(mic_received),.mic_repeated(),.mic_skipped(),.mic_timeouts());
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
  $readmemh("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/evidence/workstation_chain/fixture.hex",bytes);wait(!dut.engine.rst);repeat(9000)@(negedge clk);
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
  wait(spectrum_checked);@(negedge analysis_clk);analysis_run=0;@(negedge display_clk);display_run=0;  @(negedge audio_clk);audio_run=0;repeat(51000)@(negedge clk);
  if(!dut.audio_clock_fault||dut.audio_clock_losses!=1||gate||dut.engine.playing||bck||ws||din)$fatal(1,"audio clock loss did not stop band/output");
  audio_run=1;wait(!dut.audio_clock_fault);repeat(8000)@(negedge clk);
  if(gate||dut.engine.playing||drops||under)$fatal(1,"old performance resumed after clock recovery");
  send_packet(9);if(!dut.engine.playing||drops||under)$fatal(1,"explicit restart after clock recovery failed");
  send_packet(7);if(gate||dut.engine.left!=0||dut.engine.right!=0||dut.engine.playing)$fatal(1,"Panic failed");
  if(spectrum_valid)$fatal(1,"panic while analysis clock stopped");if(display_available)$fatal(1,"panic retained frozen frame");analysis_run=1;display_run=1;send_packet(8);if(!dut.engine.identity_status||dut.engine.receiver.crc_errors||dut.engine.receiver.overflow)$fatal(1,"Identity/parser");
  $display("PASS ADC two-seat/pedal plus microphone top I2S/CDC/singer/DAC,clockloss singer-only fade while score/PCM continue,recovery; singer UART:owner2 take,retrigger,stale/wrong-owner off,matched release,PCM+DAC activity,panic,identity;peak=%0d",peak);if(!stage_checked)$fatal(1,"stage scenario incomplete");if(!spectrum_checked)$fatal(1,"spectrum incomplete");$display("PASS2048 actual band PCM -> Hann -> FFT -> frozen display,stopped display40frames,release,panic,zero audio errors");if(decoded<100)$fatal(1,"too few I2S words");$display("PASS queued I2S fullstage actual PCM decoded words=%0d",decoded);$finish;
 end
 initial begin #100000000;$fatal(1,"Timeout");end
endmodule
