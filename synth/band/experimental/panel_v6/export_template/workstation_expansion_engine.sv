// GENERATED experimental wrapper; not a physical pin assignment.
`include "build_identity.vh"
// Board audition build: existing, verified PT8211 pins only. Not standard-I2S acceptance.
module workstation_expansion_engine #(parameter PEDAL_STABLE_CYCLES=250000,parameter LOCAL_INPUTS=0,parameter EXTERNAL_AUDIO=0,parameter COEFF_FILE="coeffs.mem")(input clk,input uart_rx_pin,output uart_tx_pin,
 input wire ble_rx,usb_rx,output wire ble_tx,usb_tx,input wire[7:0]enc_a,enc_b,input wire song_next,
 input wire transport_fault,input wire[31:0]external_drops,external_underruns,
 output wire[11:0]guide_pitch,output wire guide_bar,
 output wire[3:0]panel_part,output wire[111:0]panel_values,
 output HP_BCK,HP_WS,HP_DIN,output PA_EN,
 input wire [9:0] adc_dout,output wire adc_cs_n,adc_sclk,adc_din,
 input wire local_play,local_stop,local_panic,input wire [3:0] local_root,input wire local_minor,
 output wire [63:0] local_held,input wire external_sample_tick,
 output wire signed [15:0] pcm_left,pcm_right,output wire pcm_valid,reset_out,panic_out,
 input wire signed [23:0] microphone_sample,input wire [6:0] singer_mix,
 output wire [31:0] dac_dropped,dac_underruns,
 output wire singer_gate,output wire [6:0] singer_note,
 output wire transport_sample_tick,output wire audio_stop,
 input wire [3:0] pedal_raw,output wire [3:0] pedal_down,output wire [15:0] deferred_returns);
 reg [15:0] startup=0;always @(posedge clk)if(!(&startup))startup<=startup+1'b1;
 // Register the startup terminal decode before distributing reset widely.
 reg rst=1;always @(posedge clk)rst<=!(&startup);
 reg [13:0] offline_wait;reg offline_started,offline_play;
 always @(posedge clk)begin
  if(rst)begin offline_wait<=0;offline_started<=0;offline_play<=0;end
  else begin
   offline_play<=0;
   if(!offline_started)begin
    if(offline_wait==9000)begin offline_started<=1;offline_play<=0;end
    else offline_wait<=offline_wait+1'b1;
   end
  end
 end

 wire [7:0] byte_data;wire byte_valid;
 uart_rx #(.DIV(50)) rx(clk,rst,uart_rx_pin,byte_data,byte_valid);
 wire packet_valid,packet_ready,host_panic;wire [223:0] packet;wire [31:0] crc_errors,overflow;
 wire local_panic_sync,local_play_pulse,local_stop_pulse;
 wire panic=host_panic||local_panic_sync||transport_fault;
 assign reset_out=rst;assign panic_out=panic;
 wire[7:0]ble_data,usb_data;wire ble_valid,usb_valid,panel_valid,panel_ready,packet_remote;wire[1:0]packet_route;wire[223:0]panel_payload;
 uart_rx #(.DIV(50)) ble_uart(clk,rst,ble_rx,ble_data,ble_valid);
 uart_rx #(.DIV(50)) usb_uart(clk,rst,usb_rx,usb_data,usb_valid);
 assign ble_tx=uart_tx_pin;assign usb_tx=uart_tx_pin;
 three_uart_events ingress(clk,rst,byte_data,ble_data,usb_data,byte_valid,ble_valid,usb_valid,
  panel_valid,panel_ready,panel_payload,packet_valid,packet_ready,packet,host_panic,crc_errors,overflow,packet_remote,packet_route);
 wire [7:0] kind=packet[15:8],source=packet[23:16];wire [3:0] part=packet[27:24];
 wire source_ok=source>=1&&source<=4;
 wire manual_ready,command_ready,core_manual_ready,core_command_ready;
 wire local_busy,local_mv,local_cv;wire [1:0] local_kind,local_command;
 wire [7:0] local_source,local_contact,local_command_source;wire [3:0] local_part,local_status_part,local_command_part;
 wire [31:0] local_epoch,local_serial,local_denied;wire [6:0] local_note,local_velocity;
 wire local_xv,local_xready;wire [3:0] local_xpart,local_xparameter;wire [13:0] local_xvalue;
 wire host_control;
 assign local_xready=!host_control;
 assign manual_ready=core_manual_ready&&!local_mv;assign command_ready=core_command_ready&&!local_cv;
 wire upload_ready,upload_pending,uploading;wire [12:0] received_entries,stored_events;
 wire [1:0] expected_word;wire [31:0] upload_errors,stored_duration;
 wire is_manual=kind<4;
 wire is_command=kind==4;
 wire command_allowed=source_ok&&(packet[57:56]<2||source==1);
 assign packet_ready=!source_ok?1'b1:is_manual?manual_ready:is_command&&command_allowed?command_ready:kind==13&&source==1?upload_ready:1'b1;
 wire accepted=packet_valid&&packet_ready;
 assign host_control=packet_valid&&kind==11&&source_ok;
 reg library_status;reg[1:0]effect_mode;reg [6:0] wet,master;reg [3:0] status_part;reg status_request,upload_status,identity_status,singer_status;
 reg [7:0] tempo;reg signed [7:0] transpose;
 reg play,stop;
 wire sample_tick,playing,audio_valid;wire signed [15:0] left,right;
 wire [31:0] song_position,status_epoch,rejected,deadline_miss,clips,denied;
 wire [15:0] active_voices,render_cycles;wire [7:0] status_owner;
 reg [14:0] lease[1:4];reg [3:0] lost_pending;
 // Lease refresh is housekeeping, not part of the event-ready critical path.
 // Register its one-bit strobe and identity before the indexed counter write.
 reg lease_refresh;reg [2:0] lease_source;
 always @(posedge clk)begin
  if(rst)begin lease_refresh<=0;lease_source<=0;end
  else begin lease_refresh<=accepted&&source_ok;lease_source<=source[2:0];end
 end
 reg [7:0] lost_source;integer i;wire lost_ready;
 always @*begin
  if(lost_pending[0])lost_source=1;else if(lost_pending[1])lost_source=2;
  else if(lost_pending[2])lost_source=3;else lost_source=4;
 end
 always @(posedge clk)begin
  if(rst)begin library_status<=0;effect_mode<=0;singer_status<=0;wet<=24;master<=64;tempo<=120;transpose<=0;status_part<=0;status_request<=0;upload_status<=0;identity_status<=0;lost_pending<=0;play<=0;stop<=0;for(i=1;i<=4;i=i+1)lease[i]<=0;end
  else begin
   play<=(accepted&&source_ok&&kind==5&&packet[63:56]==0)||local_play_pulse||offline_play;
   stop<=(accepted&&source_ok&&kind==5&&packet[63:56]==1)||local_stop_pulse;
   status_request<=accepted;
   if(accepted)begin library_status<=kind==20||kind==21;upload_status<=kind==13||kind==14;identity_status<=kind==18;singer_status<=kind==19;end
   if(sample_tick)for(i=1;i<=4;i=i+1)if(lease[i]!=0)begin
    lease[i]<=lease[i]-1'b1;if(lease[i]==1)lost_pending[i-1]<=1;
   end
   if((|lost_pending)&&lost_ready)lost_pending[lost_source-1]<=0;
   if(accepted&&source_ok)begin
    status_part<=part;
    if(kind==7&&source==1)begin wet<=packet[198:192];if(packet[63:56]<3)effect_mode<=packet[57:56];end
    if(kind==10&&source==1)master<=packet[198:192];
    if(kind==15&&source==1&&packet[223:192]>=40&&packet[223:192]<=240)tempo<=packet[199:192];
    if(kind==16&&source==1&&$signed(packet[199:192])>=-24&&$signed(packet[199:192])<=24)transpose<=packet[199:192];
   end
   if(lease_refresh)lease[lease_source]<=24000;
  end
 end
 wire [31:0] singer_drop_count,singer_stale_count;
 wire raw_valid,raw_ready,library_valid,library_ready,library_busy,library_failed,next_song;
 wire[223:0]raw_payload,library_payload;wire[7:0]library_current;
 panel_controls controls(clk,rst||panic,enc_a,enc_b,raw_valid,raw_ready,raw_payload,panel_part,panel_values);
 button_pulse song_selector(clk,rst,song_next,next_song);
 wire library_request=(accepted&&(source==1||source==3)&&kind==20)||next_song;
 wire[7:0]library_selection=next_song?(library_current>=2?8'd0:library_current+1'b1):packet[199:192];
 rom_song_loader library_loader(clk,rst||panic,library_request,library_selection,upload_pending,uploading,upload_errors,
 library_valid,library_ready,library_payload,library_busy,library_failed,library_current);
 reg panel_lock,panel_grant;wire panel_choose=panel_lock?panel_grant:library_valid;
 always @(posedge clk)begin
  if(rst||panic)begin panel_lock<=0;panel_grant<=0;end
  else if(panel_valid)begin
   if(panel_ready)panel_lock<=0;else begin panel_lock<=1;panel_grant<=panel_choose;end
  end
 end
 assign panel_valid=panel_choose?library_valid:raw_valid;
 assign panel_payload=panel_choose?library_payload:raw_payload;
 assign raw_ready=panel_ready&&!panel_choose;assign library_ready=panel_ready&&panel_choose;

 band_singer_core #(.COEFF_FILE(COEFF_FILE)) core(clk,rst,panic,sample_tick,play,stop,
  local_mv||(packet_valid&&source_ok&&is_manual),core_manual_ready,local_mv?local_kind:kind[1:0],local_mv?local_source:source,local_mv?local_contact:packet[39:32],local_mv?local_part:part,
  local_mv?local_epoch:packet[95:64],local_mv?local_serial:packet[127:96],local_mv?local_note:packet[46:40],local_mv?local_velocity:packet[54:48],
  local_cv||(packet_valid&&is_command&&command_allowed),core_command_ready,local_cv?local_command:packet[57:56],local_cv?local_command_part:part,local_cv?local_command_source:source,wet,master,tempo,transpose,
  left,right,audio_valid,playing,song_position,local_busy?local_status_part:status_part,status_owner,status_epoch,
  active_voices,render_cycles,rejected,deadline_miss,clips,denied,|lost_pending,lost_ready,lost_source,
  packet_valid&&kind==13&&source==1,upload_ready,packet[58:56],packet[95:64],packet[127:96],packet[223:192],
  upload_pending,uploading,received_entries,expected_word,upload_errors,stored_events,stored_duration,,
  host_control||local_xv,host_control?part:local_xpart,host_control?source:8'd1,host_control?packet[95:64]:32'd0,
  host_control?packet[59:56]:local_xparameter,host_control?packet[205:192]:local_xvalue,,,microphone_sample,singer_mix,singer_gate,singer_note,singer_drop_count,singer_stale_count,guide_pitch,guide_bar,effect_mode);
 wire debug_tick;
 // Queue completion frames: render latency changes with voice load.
 wire dac_ready;wire [2:0] dac_queued;
 assign debug_tick=0;assign HP_BCK=0;assign HP_WS=0;assign HP_DIN=0;
 assign dac_ready=1;assign dac_queued=0;assign dac_dropped=external_drops;assign dac_underruns=external_underruns;
 assign sample_tick=EXTERNAL_AUDIO?external_sample_tick:debug_tick;
 assign transport_sample_tick=sample_tick;
 assign audio_stop=stop;assign pcm_left=left;assign pcm_right=right;assign pcm_valid=audio_valid;
 assign PA_EN=0;
 wire [223:0] status_snapshot={clips,deadline_miss,rejected,song_position,status_epoch,
  render_cycles,active_voices,{4'd0,status_part},status_owner,{7'b1000000,playing},8'd4};
 wire [223:0] upload_snapshot={32'd0,stored_duration,{19'd0,stored_events},upload_errors,
  {30'd0,expected_word},{19'd0,received_entries},8'd0,{5'd0,uploading,upload_pending,upload_ready},8'ha0,8'd4};
 localparam [31:0] FEATURE_FLAGS=32'h80000ffc|(LOCAL_INPUTS?32'd1:32'd0)|(EXTERNAL_AUDIO?32'd2:32'd0);
 wire [223:0] identity_snapshot={crc_errors,FEATURE_FLAGS,32'd50000000,32'd48000,32'd256,`BAND_BUILD_ID,8'd1,8'd0,8'ha1,8'd4};
 wire[223:0]library_snapshot={192'd0,library_current,{6'd0,library_busy,library_failed},8'ha3,8'd4};
 wire [223:0] singer_snapshot={32'd0,32'd0,dac_underruns,dac_dropped,
  singer_stale_count,singer_drop_count,{1'b0,singer_note},{7'd0,singer_gate},8'ha2,8'd4};
 reg pending_status;
 always @(posedge clk)if(rst)pending_status<=0;else if(status_request)pending_status<=1;else if(!local_busy&&!local_xv&&!host_control)pending_status<=0;
 // Freeze reply data and its request together. Do not fan the combinational
 // authorization/ready chain into the sender's 224-bit frame register enable.
 reg telemetry_request;
 reg [223:0] telemetry_snapshot;
 always @(posedge clk)begin
  if(rst)begin telemetry_request<=0;telemetry_snapshot<=0;end
  else begin
   telemetry_request<=pending_status&&!local_busy&&!local_xv&&!host_control;
   telemetry_snapshot<=library_status?library_snapshot:identity_status?identity_snapshot:singer_status?singer_snapshot:upload_status?upload_snapshot:status_snapshot;
  end
 end
 wire event_capture_valid,event_capture_ready,sender_ready;
 wire[223:0]event_capture_data;wire[31:0]capture_overflows;
 wire capture_remote=accepted&&packet_remote&&(kind==0||kind==1||kind==2||kind==7||kind==10||kind==11||kind==15||kind==16);
 wire capture_local=local_mv&&core_manual_ready&&(local_kind==0||local_kind==1);
 wire[223:0]local_capture={32'd0,64'd0,local_serial,local_epoch,8'd0,{1'b0,local_velocity},{1'b0,local_note},local_contact,{4'd0,local_part},local_source,{6'd0,local_kind},8'd4};
 wire capture_x=local_xv&&local_xready;
 wire[223:0]x_capture={18'd0,local_xvalue,64'd0,32'd0,32'd0,{4'd0,local_xparameter},8'd100,8'd60,8'd0,{4'd0,local_xpart},8'd1,8'd11,8'd4};
 reg capture_panic_held;always @(posedge clk)if(rst)capture_panic_held<=0;else capture_panic_held<=panic;
 wire capture_panic=capture_panic_held&&!panic;
 wire[223:0]panic_capture={200'd0,8'd1,8'd127,8'd4};
 wire[2:0]capture_count={2'd0,capture_remote}+{2'd0,capture_local}+{2'd0,capture_x}+{2'd0,capture_panic};
 wire[1:0]capture_collision=capture_count>0?capture_count-1'b1:2'd0;
 event_capture_fifo capture_events(clk,rst,panic,sample_tick,capture_remote||capture_local||capture_x||capture_panic,
 capture_panic?panic_capture:capture_local?local_capture:capture_x?x_capture:packet,event_capture_valid,event_capture_ready,event_capture_data,capture_overflows,capture_collision);
 reg[31:0]reported_overflows;reg capture_turn;reg status_pending;reg[223:0]status_held;
 wire overflow_notice=capture_overflows!=reported_overflows;
 wire send_capture=event_capture_valid&&(!status_pending||capture_turn);
 wire[223:0]overflow_snapshot={capture_overflows,176'd0,8'hdf,8'd4};
 assign event_capture_ready=sender_ready&&!overflow_notice&&send_capture;
 always @(posedge clk)begin
  if(rst)begin reported_overflows<=0;capture_turn<=0;status_pending<=0;status_held<=0;end
  else begin
   if(telemetry_request)begin status_pending<=1;status_held<=telemetry_snapshot;end
   if(sender_ready)begin
   if(!overflow_notice&&!send_capture&&status_pending&&!telemetry_request)status_pending<=0;
   if(overflow_notice)reported_overflows<=capture_overflows;
   if(send_capture||status_pending)capture_turn<=!capture_turn;
   end
  end
 end
 event_status_sender telemetry(clk,rst,overflow_notice||send_capture||status_pending,
 overflow_notice?overflow_snapshot:send_capture?event_capture_data:status_held,uart_tx_pin,sender_ready);
 generate if(LOCAL_INPUTS)begin:local_inputs
  wire sv,pv,pr,po,exhausted;wire [2:0] channel;wire [119:0] samples;wire [6:0] contact,pressure;
  wire [31:0] serial,overruns;wire [559:0] pressures;
  reg [1:0] panic_sync;
  always @(posedge clk)if(rst)panic_sync<=0;else panic_sync<={panic_sync[0],local_panic};
  assign local_panic_sync=panic_sync[1];
  button_pulse play_button(clk,rst,local_play,local_play_pulse);
  button_pulse stop_button(clk,rst,local_stop,local_stop_pulse);
  mcp3208_scanner scanner(clk,rst,adc_dout,adc_cs_n,adc_sclk,adc_din,sv,channel,samples);
  local_expression expression(clk,rst,panic,sv,channel,samples,local_xv,local_xready,local_xpart,local_xparameter,local_xvalue);
  stage_pad_frontend pads(clk,rst,panic||stop,sv,channel,samples,
   accepted&&source==1&&kind==17,packet[38:32],packet[203:192],packet[111:96],packet[56],
   7'd24,7'd12,pv,pr,po,contact,pressure,serial,pressures,overruns,exhausted);
  local_pedal_performer #(.STABLE_CYCLES(PEDAL_STABLE_CYCLES)) performer(clk,rst,panic||stop,pv,pr,po,contact,pressure,serial,local_root,local_minor,
   local_busy,local_status_part,!host_control&&!local_xv,status_owner,status_epoch,
   local_cv,core_command_ready,local_command,local_command_part,local_command_source,
   local_mv,core_manual_ready,local_kind,local_source,local_contact,local_part,local_epoch,local_serial,local_note,local_velocity,local_denied,local_held,pedal_raw,pedal_down,deferred_returns);
 end else begin:no_local_inputs
  assign pedal_down=0;assign deferred_returns=0;
  assign adc_cs_n=1;assign adc_sclk=0;assign adc_din=0;assign local_held=0;
  reg[1:0]panel_panic_sync;
 always @(posedge clk)if(rst)panel_panic_sync<=0;else panel_panic_sync<={panel_panic_sync[0],local_panic};
 assign local_panic_sync=panel_panic_sync[1];
 button_pulse panel_play(clk,rst,local_play,local_play_pulse);
 button_pulse panel_stop(clk,rst,local_stop,local_stop_pulse);
  assign local_busy=0;assign local_mv=0;assign local_cv=0;assign local_kind=0;assign local_command=0;
  assign local_source=0;assign local_contact=0;assign local_command_source=0;assign local_part=0;assign local_status_part=0;assign local_command_part=0;
  assign local_epoch=0;assign local_serial=0;assign local_denied=0;assign local_note=0;assign local_velocity=0;
  assign local_xv=0;assign local_xpart=0;assign local_xparameter=0;assign local_xvalue=0;
 end endgenerate
endmodule
