`include "build_identity.vh"
// Board audition build: existing, verified PT8211 pins only. Not standard-I2S acceptance.
module band_board_engine #(parameter LOCAL_INPUTS=0,parameter EXTERNAL_AUDIO=0)(input clk,input uart_rx_pin,output uart_tx_pin,
 output HP_BCK,HP_WS,HP_DIN,output PA_EN,
 input wire [9:0] adc_dout,output wire adc_cs_n,adc_sclk,adc_din,
 input wire local_play,local_stop,local_panic,input wire [3:0] local_root,input wire local_minor,
 output wire [63:0] local_held,input wire external_sample_tick,
 output wire signed [15:0] pcm_left,pcm_right,output wire pcm_valid,reset_out,panic_out);
 reg [15:0] startup=0;always @(posedge clk)if(!(&startup))startup<=startup+1'b1;
 // Register the startup terminal decode before distributing reset widely.
 reg rst=1;always @(posedge clk)rst<=!(&startup);
 wire [7:0] byte_data;wire byte_valid;
 uart_rx #(.DIV(50)) rx(clk,rst,uart_rx_pin,byte_data,byte_valid);
 wire packet_valid,packet_ready,host_panic;wire [223:0] packet;wire [31:0] crc_errors,overflow;
 wire local_panic_sync,local_play_pulse,local_stop_pulse;
 wire panic=host_panic||local_panic_sync;
 assign reset_out=rst;assign panic_out=panic;
 event_receiver receiver(clk,rst,byte_data,byte_valid,packet_valid,packet_ready,packet,host_panic,crc_errors,overflow);
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
 assign host_control=accepted&&kind==11&&source_ok;
 reg [6:0] wet,master;reg [3:0] status_part;reg status_request,upload_status,identity_status;
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
  if(rst)begin wet<=32;master<=96;tempo<=120;transpose<=0;status_part<=0;status_request<=0;upload_status<=0;identity_status<=0;lost_pending<=0;play<=0;stop<=0;for(i=1;i<=4;i=i+1)lease[i]<=0;end
  else begin
   play<=(accepted&&source_ok&&kind==5&&packet[63:56]==0)||local_play_pulse;
   stop<=(accepted&&source_ok&&kind==5&&packet[63:56]==1)||local_stop_pulse;
   status_request<=accepted;
   if(accepted)begin upload_status<=kind==13||kind==14;identity_status<=kind==18;end
   if(sample_tick)for(i=1;i<=4;i=i+1)if(lease[i]!=0)begin
    lease[i]<=lease[i]-1'b1;if(lease[i]==1)lost_pending[i-1]<=1;
   end
   if((|lost_pending)&&lost_ready)lost_pending[lost_source-1]<=0;
   if(accepted&&source_ok)begin
    status_part<=part;
    if(kind==7&&source==1)wet<=packet[198:192];
    if(kind==10&&source==1)master<=packet[198:192];
    if(kind==15&&source==1&&packet[223:192]>=40&&packet[223:192]<=240)tempo<=packet[199:192];
    if(kind==16&&source==1&&$signed(packet[199:192])>=-24&&$signed(packet[199:192])<=24)transpose<=packet[199:192];
   end
   if(lease_refresh)lease[lease_source]<=24000;
  end
 end
 band_core core(clk,rst,panic,sample_tick,play,stop,
  local_mv||(packet_valid&&source_ok&&is_manual),core_manual_ready,local_mv?local_kind:kind[1:0],local_mv?local_source:source,local_mv?local_contact:packet[39:32],local_mv?local_part:part,
  local_mv?local_epoch:packet[95:64],local_mv?local_serial:packet[127:96],local_mv?local_note:packet[46:40],local_mv?local_velocity:packet[54:48],
  local_cv||(packet_valid&&is_command&&command_allowed),core_command_ready,local_cv?local_command:packet[57:56],local_cv?local_command_part:part,local_cv?local_command_source:source,wet,master,tempo,transpose,
  left,right,audio_valid,playing,song_position,local_busy?local_status_part:status_part,status_owner,status_epoch,
  active_voices,render_cycles,rejected,deadline_miss,clips,denied,|lost_pending,lost_ready,lost_source,
  packet_valid&&kind==13&&source==1,upload_ready,packet[58:56],packet[95:64],packet[127:96],packet[223:192],
  upload_pending,uploading,received_entries,expected_word,upload_errors,stored_events,stored_duration,,
  host_control||local_xv,host_control?part:local_xpart,host_control?source:8'd1,host_control?packet[95:64]:32'd0,
  host_control?packet[59:56]:local_xparameter,host_control?packet[205:192]:local_xvalue,,);
 wire debug_tick;
 audio_serial #(.MODE_I2S(0)) dac(clk,rst,left,right,HP_BCK,HP_WS,HP_DIN,debug_tick);
 assign sample_tick=EXTERNAL_AUDIO?external_sample_tick:debug_tick;
 assign pcm_left=left;assign pcm_right=right;assign pcm_valid=audio_valid;
 assign PA_EN=~rst;
 wire [223:0] status_snapshot={clips,deadline_miss,rejected,song_position,status_epoch,
  render_cycles,active_voices,{4'd0,status_part},status_owner,{7'b1000000,playing},8'd4};
 wire [223:0] upload_snapshot={32'd0,stored_duration,{19'd0,stored_events},upload_errors,
  {30'd0,expected_word},{19'd0,received_entries},8'd0,{5'd0,uploading,upload_pending,upload_ready},8'ha0,8'd4};
 localparam [31:0] FEATURE_FLAGS=32'd28|(LOCAL_INPUTS?32'd1:32'd0)|(EXTERNAL_AUDIO?32'd2:32'd0);
 wire [223:0] identity_snapshot={crc_errors,FEATURE_FLAGS,32'd50000000,32'd48000,32'd256,`BAND_BUILD_ID,8'd1,8'd0,8'ha1,8'd4};
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
   telemetry_snapshot<=identity_status?identity_snapshot:upload_status?upload_snapshot:status_snapshot;
  end
 end
 status_sender telemetry(clk,rst,telemetry_request,telemetry_snapshot,uart_tx_pin);
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
  pad_frontend pads(clk,rst,panic||stop,sv,channel,samples,
   accepted&&source==1&&kind==17,packet[38:32],packet[203:192],packet[111:96],packet[56],
   7'd24,7'd12,pv,pr,po,contact,pressure,serial,pressures,overruns,exhausted);
  local_performer performer(clk,rst,panic||stop,pv,pr,po,contact,pressure,serial,local_root,local_minor,
   local_busy,local_status_part,!host_control&&!local_xv,status_owner,status_epoch,
   local_cv,core_command_ready,local_command,local_command_part,local_command_source,
   local_mv,core_manual_ready,local_kind,local_source,local_contact,local_part,local_epoch,local_serial,local_note,local_velocity,local_denied,local_held);
 end else begin:no_local_inputs
  assign adc_cs_n=1;assign adc_sclk=0;assign adc_din=0;assign local_held=0;
  assign local_panic_sync=0;assign local_play_pulse=0;assign local_stop_pulse=0;
  assign local_busy=0;assign local_mv=0;assign local_cv=0;assign local_kind=0;assign local_command=0;
  assign local_source=0;assign local_contact=0;assign local_command_source=0;assign local_part=0;assign local_status_part=0;assign local_command_part=0;
  assign local_epoch=0;assign local_serial=0;assign local_denied=0;assign local_note=0;assign local_velocity=0;
  assign local_xv=0;assign local_xpart=0;assign local_xparameter=0;assign local_xvalue=0;
 end endgenerate
endmodule
