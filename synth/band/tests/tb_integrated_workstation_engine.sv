`timescale 1ns/1ps
module tb;
 reg clk=0;always #10 clk=~clk;
 reg request=0;wire busy,failed,rst;reg pv=0;reg[223:0]packet=0;wire pr;
 wire[31:0]drops,under;wire[3:0]take_state;
 reg[3:0]seat=8;reg[7:0]contact=0;reg[31:0]serial_number=1;reg[31:0]held_position;reg[1:0]mode=1;wire bck,ws;tri mic_sd;reg mic_drive=0,mic_enable=0;
 assign mic_sd=mic_enable?mic_drive:1'bz;pullup(mic_sd);
 reg prevws=1;integer slot=0;reg[23:0]mic_sample=24'h100000;
 always @(negedge bck)if(!rst)begin
  #1;if(ws!=prevws)begin slot=0;prevws=ws;end else slot=slot+1;
  if(!ws&&slot>=1&&slot<=24)begin mic_enable<=#69 1;mic_drive<=#69 mic_sample[24-slot];end else mic_enable<=#69 0;
 end
 band_stage_pt8211_engine #(.LOCAL_INPUTS(0),.LOCAL_ANALOG(0)) dut(
 .clk(clk),.uart_rx_pin(1'b1),.ble_rx(1'b1),.panel_valid(pv),.panel_ready(pr),.panel_payload(packet),
 .presented(128'h76543210_abcdef01_10325476_fe018a8a),.frame_number(16'h439a),.slider_mv(48'h123456789abc),
 .seat(1'b0),.audition(1'b0),.faders({7'd24,7'd64,7'd64,7'd64}),.vibrato(7'd0),.visual_presented(948'd0),.panel_part(seat),.panel_octave(-4'sd2),.panel_sustain(1'b1),.mic_mode(mode),.mic_sd(mic_sd),.HP_BCK(bck),.HP_WS(ws),
 .song_request(request),.song_selection(3'd3),.song_busy(busy),.song_failed(failed),
 .record_toggle(1'b0),.replay_request(1'b0),.take_state(take_state),
 .adc_dout(10'd0),.local_play(1'b0),.local_stop(1'b0),.local_panic(1'b0),.local_root(4'd0),.local_minor(1'b0),
 .external_sample_tick(1'b0),.microphone_sample(24'sd0),.singer_mix(7'd0),.pedal_raw(4'd0),
 .reset_out(rst),.dac_dropped(drops),.dac_underruns(under));
 defparam dut.dac.WARMUP=4;
 task send(input[7:0]kind,input[7:0]source,input[3:0]part,input[7:0]flags,input[31:0]epoch);begin
  @(negedge clk);packet=0;packet[7:0]=4;packet[15:8]=kind;packet[23:16]=source;packet[27:24]=part;
  packet[46:40]=60;packet[54:48]=100;packet[63:56]=flags;packet[95:64]=epoch;packet[127:96]=serial_number;packet[39:32]=contact;pv=1;
  @(posedge clk);while(!pr)@(posedge clk);@(negedge clk);pv=0;repeat(150)@(negedge clk);
 end endtask
 initial begin
  wait(!rst);repeat(100)@(negedge clk);
  if(dut.config_snapshot[23:16]!=8||dut.config_snapshot[31:24]!=8'hfe||dut.config_snapshot[32]!=1)$fatal(1,"config packing");
  send(20,1,8,8'h4d,0);
  if(dut.telemetry_snapshot!=={16'd0,48'h123456789abc,128'h76543210_abcdef01_10325476_fe018a8a,16'h439a,8'ha4,8'd4})$fatal(1,"mirror packet");
  send(20,2,8,0,0);if(dut.telemetry_snapshot[15:8]!=8'ha3)$fatal(1,"C3 config after mirror request");
  seat=4;mode=3;
  send(5,1,4,0,0);
  if(dut.lesson_cue!==16||dut.config_snapshot[79:72]!=8'hb5)$fatal(1,"missing first guided pad");
  held_position=dut.song_position;
  serial_number=dut.lesson_tag;contact=1;send(22,2,4,0,0);
  contact=0;serial_number=32'hffff;send(22,2,4,0,0);
  repeat(2500)@(negedge clk);
  if(dut.lesson_cue!==16||dut.song_position!=held_position)$fatal(1,"wrong or stale hit advanced the song");
  serial_number=dut.lesson_tag;send(22,2,4,0,0);repeat(4500)@(negedge clk);
  if(dut.lesson_cue[4]||dut.song_position<=held_position||!dut.active_voices)$fatal(1,"correct pad did not release transport and play");
  send(5,1,4,1,0);mode=1;seat=8;serial_number=1;
  wait(dut.microphone_ready);repeat(5000)@(negedge clk);
  if(dut.microphone_level!==24'h100000||dut.mixed_left<8000)$fatal(1,"monitor input/mix");
  mode=2;send(4,2,15,0,0);send(6,2,15,0,0);
  if(dut.status_owner!=2)$fatal(1,"singer ownership");
  send(0,2,15,0,dut.status_epoch);repeat(50000)@(negedge clk);
  if(dut.singer_gate!==dut.FEATURE_FLAGS[5]||dut.singer_drop_count)$fatal(1,"singer capability disagrees with gate/drop");
  send(1,2,15,0,dut.status_epoch);mode=0;
  request=1;@(negedge clk);request=0;wait(busy);wait(!busy);repeat(200)@(negedge clk);
  if(failed||dut.upload_errors||!dut.playing||dut.stored_events!=64||dut.stored_duration!=792000)$fatal(1,"song upload/start");
  repeat(3000)@(negedge clk);
  if(drops||under||dut.deadline_miss)$fatal(1,"audio faults");
  send(5,1,8,1,0);if(dut.halt_counter!=3)$fatal(1,"stop counter (ROM load also stops)");
  send(5,1,8,0,0);repeat(2000)@(negedge clk);
  if(!dut.playing)$fatal(1,"play before panic");
  force dut.host_panic=1'b1;repeat(3)@(negedge clk);release dut.host_panic;
  repeat(2000)@(negedge clk);
  if(dut.playing||dut.singer_gate||dut.active_voices||dut.packet_valid||dut.halt_counter!=4)$fatal(1,"registered panic must clear transport, voices and pending event");
  if(drops||under)$fatal(1,"panic audio queue faults");
  $display("PASS full engine physical mic model, monitor, singer, ROM CRC/commit/play, config, stop counter, audio deadlines, panic clears transport/voices/event queue");$finish;
 end
 initial begin #20000000;$fatal(1,"timeout");end
endmodule
