// GENERATED experimental integration; do not substitute for released band_core.
// Integrated performance core. Standardized events can originate from local sensors or host.
module band_singer_core #(parameter BANKS=8,parameter COEFF_FILE="coeffs.mem")(
 input wire clk,rst,panic,sample_tick,play,stop,
 input wire manual_valid,output wire manual_ready,input wire [1:0] manual_kind,
 input wire [7:0] manual_source,manual_contact,input wire [3:0] manual_part,
 input wire [31:0] manual_epoch,manual_serial,input wire [6:0] manual_note,manual_velocity,
 input wire command_valid,output wire command_ready,input wire [1:0] command,
 input wire [3:0] command_part,input wire [7:0] command_source,
 input wire [6:0] wet,master,input wire [7:0] tempo,input wire signed [7:0] transpose,
 output wire signed [15:0] left_out,right_out,output wire audio_valid,
 output wire playing,output wire [31:0] song_position,
 input wire [3:0] status_part,output wire [7:0] status_owner,output wire [31:0] status_epoch,
 output wire [15:0] active_voices,render_cycles,
 output wire [31:0] rejected,deadline_miss,clips,output reg [31:0] denied,
 input wire source_lost,output wire lost_ready,input wire [7:0] lost_source,
 input wire upload_valid,output wire upload_ready,input wire [2:0] upload_command,
 input wire [31:0] upload_index,upload_value,upload_aux,
 output wire upload_pending,uploading,output wire [12:0] received_entries,
 output wire [1:0] expected_word,output wire [31:0] upload_errors,
 output wire [12:0] stored_events,output wire [31:0] stored_duration,output wire simulation_idle,
 input wire control_valid,input wire [3:0] control_part,input wire [7:0] control_source,
 input wire [31:0] control_epoch,input wire [3:0] control_parameter,input wire [13:0] control_value,
 output reg [31:0] lead_space_events,kick_follow_events,
 input wire signed [23:0] microphone_sample,
 input wire [6:0] singer_mix,
 output wire singer_gate,output wire [6:0] singer_note,
 output wire [31:0] singer_dropped,singer_stale_off
);
 wire halt=panic||stop;
 wire band_audio_valid;
 wire signed [15:0] band_left,band_right;
 wire signed [23:0] singer_left,singer_right;
 wire singer_event_ready,singer_frame_ready;
 wire [31:0] singer_rejected,singer_duplicates,singer_mix_clips,singer_vocoder_clips;
 wire [13:0] singer_master_product;
 wire [6:0] singer_effective_gain=singer_master_product[13:7];
 assign left_out=singer_left[23:8];assign right_out=singer_right[23:8];
 wire alloc_ready,release_valid,release_ready;
 wire auto_valid,auto_ready,bar_tick;wire [1:0] auto_kind;wire [3:0] auto_part;
 wire [6:0] auto_note,auto_velocity;wire [31:0] auto_serial,late_events;wire [7:0] bar_position;
 wire score_quiet;
 song_sequencer score(clk,rst,panic,sample_tick,play,stop,playing,bar_tick,auto_valid,auto_ready,
  auto_kind,auto_part,auto_note,auto_velocity,auto_serial,song_position,late_events,bar_position,
  upload_valid,upload_ready,upload_command,upload_index,upload_value,upload_aux,
  upload_pending,uploading,received_entries,expected_word,upload_errors,stored_events,stored_duration,score_quiet,tempo);
 reg was_playing,auto_end_pending;
 always @(posedge clk)begin
  if(rst||halt)begin was_playing<=0;auto_end_pending<=0;end
  else begin
   was_playing<=playing;
   if(was_playing&&!playing)auto_end_pending<=1;
   else if(auto_end_pending&&alloc_ready&&!release_valid)auto_end_pending<=0;
  end
 end
 wire any_lost=source_lost||auto_end_pending;
 wire [7:0] released_source=auto_end_pending?8'd0:lost_source;
 wire [3:0] release_part;
 wire [3:0] routed_part=manual_valid?manual_part:auto_part;
 wire [7:0] owner;wire [31:0] epoch;wire muted,pending,ownership_exhausted;wire [31:0] conflicts;
 // Status is read through a second combinational query without duplicating ownership state.
 track_ownership ownership(clk,rst,halt,bar_tick,command_valid,command_ready,command,command_part,command_source,
  release_valid,release_ready,release_part,routed_part,owner,epoch,muted,pending,conflicts,ownership_exhausted,
  control_valid?control_part:status_part,status_owner,status_epoch,source_lost&&lost_ready,lost_source);
 // Control ownership lookup, comparison and patch fanout occupy separate clocks.
 // A command/bar transition invalidates an in-flight non-conductor control.
 wire ownership_stable=command_ready&&!command_valid&&!bar_tick;
 reg control_pending,accepted_control;reg [7:0] saved_control_source,saved_control_owner,applied_control_source;
 reg [31:0] saved_control_epoch,saved_owner_epoch;
 reg [3:0] saved_control_part,saved_control_parameter,applied_control_part,applied_control_parameter;
 reg [13:0] saved_control_value,applied_control_value;
 always @(posedge clk)begin
  if(rst||halt)begin control_pending<=0;accepted_control<=0;end
  else begin
   control_pending<=control_valid;
   if(control_valid)begin
    saved_control_source<=control_source;saved_control_owner<=status_owner;
    saved_control_epoch<=control_epoch;saved_owner_epoch<=status_epoch;
    saved_control_part<=control_part;saved_control_parameter<=control_parameter;saved_control_value<=control_value;
   end
   accepted_control<=control_pending&&(saved_control_source==1||
    (saved_control_source==saved_control_owner&&saved_control_epoch==saved_owner_epoch&&ownership_stable&&!release_valid));
   applied_control_source<=saved_control_source;applied_control_part<=saved_control_part;
   applied_control_parameter<=saved_control_parameter;applied_control_value<=saved_control_value;
  end
 end
 wire event_present=manual_valid||auto_valid;
 wire auto_parameter=!manual_valid&&auto_valid&&auto_kind==2;
 wire [1:0] kind=manual_valid?manual_kind:auto_kind;
 wire [7:0] source=manual_valid?manual_source:8'd0;
 wire signed [8:0] shifted_note=$signed({2'd0,auto_note})+$signed(transpose);
 wire [6:0] pitched_auto_note=auto_part<3?auto_note:shifted_note<0?7'd0:shifted_note>127?7'd127:shifted_note[6:0];
 // Pipeline ownership lookup and identity comparison. The old path traversed a
 // track mux, 32-bit epoch compare and every allocator in one clock and failed PnR.
 reg [1:0] auth_state;reg auth_manual,auth_muted,auth_exhausted,allowed;
 reg [7:0] auth_owner,auth_source;reg [3:0] auth_part;reg [1:0] auth_kind;
 reg [31:0] auth_owner_epoch,auth_event_epoch,auth_serial;
 wire same_event=auth_manual==manual_valid&&auth_source==source&&auth_part==routed_part&&auth_kind==kind&&
  auth_serial==(manual_valid?manual_serial:auto_serial)&&(!manual_valid||auth_event_epoch==manual_epoch);
 // All producers hold a payload until ready. The full fingerprint is checked
 // in stage 1. At dispatch only the arbiter route can change: a newly-arriving
 // local seat may preempt a host or machine event, and those source IDs differ.
 // Repeating the 64-bit fingerprint compare at allocator fanout failed 50 MHz.
 wire same_route=auth_manual==manual_valid&&auth_source==source&&auth_part==routed_part&&auth_kind==kind;
 wire authorization_valid=auth_state==2&&same_route&&ownership_stable;
 assign manual_ready=!halt&&!release_valid&&!any_lost&&authorization_valid&&(allowed?alloc_ready:1'b1);
 assign auto_ready=!halt&&!release_valid&&!any_lost&&!manual_valid&&authorization_valid&&!(auto_parameter&&accepted_control)&&(allowed&&!auto_parameter?alloc_ready:1'b1);
 always @(posedge clk)begin
  if(rst||halt||release_valid||any_lost||!ownership_stable)begin auth_state<=0;allowed<=0;end
  else case(auth_state)
   0:if(event_present)begin
    auth_manual<=manual_valid;auth_owner<=owner;auth_owner_epoch<=epoch;auth_muted<=muted;auth_exhausted<=ownership_exhausted;
    auth_source<=source;auth_part<=routed_part;auth_kind<=kind;auth_event_epoch<=manual_epoch;auth_serial<=manual_valid?manual_serial:auto_serial;auth_state<=1;
   end
   1:begin
    allowed<=(auth_kind==2&&auth_manual)||(auth_source==auth_owner)&&(!auth_manual||auth_event_epoch==auth_owner_epoch)&&!(auth_muted&&auth_kind==0)&&!auth_exhausted;
    auth_state<=same_event?2:0;
   end
   2:if(!same_route||(manual_valid&&manual_ready)||(!manual_valid&&auto_valid&&auto_ready))auth_state<=0;
   default:auth_state<=0;
  endcase
 end
 assign release_ready=alloc_ready;
 assign lost_ready=alloc_ready&&!release_valid&&!auto_end_pending&&!halt;
 wire routed_valid=release_valid||any_lost||(event_present&&authorization_valid&&allowed&&!auto_parameter);
 wire [1:0] routed_kind=release_valid?2'd3:any_lost?2'd2:kind;
 wire [3:0] target_part=release_valid?release_part:routed_part;
 wire broadcast=routed_kind==2;
 wire [3:0] bank_index=target_part&(BANKS-1);
 wire [BANKS-1:0] bank_ready,bank_valid;
 wire signed [15:0] bank_sample[0:BANKS-1];
 wire [15:0] bank_voices[0:BANKS-1],bank_cycles[0:BANKS-1];
 wire [31:0] bank_rejected[0:BANKS-1],bank_deadline[0:BANKS-1],bank_clips[0:BANKS-1];
 reg collaboration_enabled;reg [6:0] last_kick_velocity;
 wire lead_present=BANKS>6?bank_voices[6]!=0:1'b0;
 wire [7:0] bass_follow={1'b0,auto_velocity>>1}+{1'b0,last_kick_velocity>>1};
 wire [6:0] automatic_velocity=collaboration_enabled&&auto_part==4&&lead_present?(auto_velocity>>1):
  collaboration_enabled&&auto_part==3?(bass_follow>127?7'd127:bass_follow[6:0]):auto_velocity;
 wire event_accepted=allowed&&((manual_valid&&manual_ready)||(!manual_valid&&auto_valid&&auto_ready));
 always @(posedge clk)begin
  if(rst)begin collaboration_enabled<=1;last_kick_velocity<=112;lead_space_events<=0;kick_follow_events<=0;end
  else begin
   if(accepted_control&&applied_control_source==1&&applied_control_parameter==3)collaboration_enabled<=applied_control_value[0];
   if(event_accepted&&kind==0&&routed_part==0)last_kick_velocity<=manual_valid?manual_velocity:auto_velocity;
   if(event_accepted&&!manual_valid&&kind==0&&collaboration_enabled)begin
    if(auto_part==4&&lead_present)lead_space_events<=lead_space_events+1'b1;
    if(auto_part==3)kick_follow_events<=kick_follow_events+1'b1;
   end
  end
 end
 // A one-entry transaction register breaks the authorization/owner lookup
 // path before the large allocator fanout. Producers are acknowledged when
 // captured, and the complete immutable identity waits for its bank(s).
 // Ownership releases use this same queue, preserving ordering with notes.
 reg dispatch_valid;reg [1:0] dispatch_kind;
 reg [7:0] dispatch_source,dispatch_contact;
 reg [3:0] dispatch_part;reg [31:0] dispatch_epoch,dispatch_serial;
 reg [6:0] dispatch_note,dispatch_velocity;
 wire dispatch_broadcast=dispatch_kind==2;
 wire [3:0] dispatch_bank=dispatch_part&(BANKS-1);
 wire dispatch_ready=dispatch_broadcast?((&bank_ready)&&singer_event_ready):dispatch_part==15?singer_event_ready:bank_ready[dispatch_bank];
 assign alloc_ready=!dispatch_valid;
 always @(posedge clk)begin
  if(rst||halt)dispatch_valid<=0;
  else if(dispatch_valid)begin
   if(dispatch_ready)dispatch_valid<=0;
  end else if(routed_valid)begin
   dispatch_valid<=1;dispatch_kind<=routed_kind;
   dispatch_source<=release_valid?8'd0:any_lost?released_source:source;
   dispatch_contact<=manual_valid?manual_contact:{1'b0,auto_note};
   dispatch_part<=target_part;dispatch_epoch<=epoch;
   dispatch_serial<=manual_valid?manual_serial:auto_serial;
   dispatch_note<=manual_valid?manual_note:pitched_auto_note;
   dispatch_velocity<=manual_valid?manual_velocity:automatic_velocity;
  end
 end
 wire [3:0] effective_control_part=accepted_control?applied_control_part:auto_part;
 reg bank_control_valid;reg [3:0] bank_control_part,bank_control_parameter;reg [13:0] bank_control_value;
 always @(posedge clk)begin
  if(rst||halt)bank_control_valid<=0;
  else begin
   bank_control_valid<=accepted_control||(auto_parameter&&auto_ready&&allowed);
   bank_control_part<=effective_control_part;
   bank_control_parameter<=accepted_control?applied_control_parameter:4'd2;
   bank_control_value<=accepted_control?applied_control_value:{7'd0,auto_note};
  end
 end
 genvar b;
 generate for(b=0;b<BANKS;b=b+1)begin:banks
  voice_bank #(.BANK_BITS(BANKS==8?3:BANKS==4?2:BANKS==2?1:0),.BANK_ID(b)) unit(clk,rst,halt,sample_tick,dispatch_valid&&(dispatch_broadcast?((&bank_ready)&&singer_event_ready):(dispatch_part!=15&&dispatch_bank==b)),bank_ready[b],
   dispatch_kind,dispatch_source,dispatch_contact,dispatch_part,
   dispatch_epoch,dispatch_serial,dispatch_note,dispatch_velocity,
   bank_valid[b],bank_sample[b],bank_voices[b],bank_cycles[b],bank_rejected[b],bank_deadline[b],bank_clips[b],
   bank_control_valid&&((bank_control_part&(BANKS-1))==b),bank_control_part,
   bank_control_parameter,bank_control_value);
 end endgenerate
 reg signed [15:0] held_sample[0:BANKS-1];
 reg [BANKS-1:0] completed;reg mixing,dry_valid,delay_pending;
 reg signed [23:0] dry,dry_right;reg [31:0] mix_deadline;
 reg [6:0] smooth_master,smooth_wet;
 assign singer_master_product=singer_mix*smooth_master;
 always @(posedge clk)begin
  if(rst)begin smooth_master<=0;smooth_wet<=0;end
  else if(sample_tick)begin
   if(smooth_master<master)smooth_master<=smooth_master+1'b1;else if(smooth_master>master)smooth_master<=smooth_master-1'b1;
   if(smooth_wet<wet)smooth_wet<=smooth_wet+1'b1;else if(smooth_wet>wet)smooth_wet<=smooth_wet-1'b1;
  end
 end
 reg frame_active;reg [15:0] frame_cycles,full_cycles;
 wire delay_ready;
 reg signed [23:0] combined,combined_right;reg [15:0] combined_voices,max_cycles;
 reg [31:0] combined_rejected,combined_deadline,renderer_clips;
 integer j,k;
 always @*begin
  combined=0;combined_right=0;combined_voices=0;max_cycles=0;combined_rejected=0;combined_deadline=0;renderer_clips=0;
  for(j=0;j<BANKS;j=j+1)begin
   // Fixed stage positions, unity maximum per side, implemented with shifts.
   // Kick/bass/lead remain centered; piano and sustained harmony separate.
   combined=combined+(j==2?($signed(held_sample[j])>>>1):j==5?($signed(held_sample[j])>>>1)+($signed(held_sample[j])>>>3):$signed(held_sample[j]));
   combined_right=combined_right+(j==4?($signed(held_sample[j])>>>1)+($signed(held_sample[j])>>>3):j==1?($signed(held_sample[j])>>>1)+($signed(held_sample[j])>>>2):$signed(held_sample[j]));
   combined_voices=combined_voices+bank_voices[j];
   if(bank_cycles[j]>max_cycles)max_cycles=bank_cycles[j];
   combined_rejected=combined_rejected+bank_rejected[j];combined_deadline=combined_deadline+bank_deadline[j];renderer_clips=renderer_clips+bank_clips[j];
  end
 end
 assign active_voices=combined_voices;assign render_cycles=full_cycles;
 assign rejected=combined_rejected+singer_rejected;assign deadline_miss=combined_deadline+mix_deadline+singer_dropped;
 always @(posedge clk)begin
  if(rst||halt)begin completed<=0;mixing<=0;dry_valid<=0;dry<=0;dry_right<=0;mix_deadline<=0;delay_pending<=0;frame_active<=0;frame_cycles<=0;full_cycles<=0;
   for(k=0;k<BANKS;k=k+1)held_sample[k]<=0;
  end else begin
   dry_valid<=0;
   if(sample_tick)begin
    if(frame_active)mix_deadline<=mix_deadline+1'b1;
    completed<=0;mixing<=1;frame_cycles<=0;frame_active<=delay_ready;
   end
   else begin
    if(frame_active)frame_cycles<=frame_cycles+1'b1;
    for(k=0;k<BANKS;k=k+1)if(bank_valid[k])begin held_sample[k]<=bank_sample[k];completed[k]<=1;end
    if(mixing&&(&completed))begin dry<=combined;dry_right<=combined_right;dry_valid<=frame_active;mixing<=0;end
   end
   if(dry_valid)delay_pending<=1;else if(band_audio_valid)delay_pending<=0;
   if(band_audio_valid)begin full_cycles<=frame_cycles;frame_active<=0;end
  end
 end
 wire [31:0] effect_clips,effect_overruns;
 wire signed [31:0] master_product=dry*$signed({1'b0,smooth_master});
 wire signed [31:0] master_product_right=dry_right*$signed({1'b0,smooth_master});
 wire signed [31:0] gained=master_product>>>5;
 wire signed [31:0] gained_right=master_product_right>>>5;
 wire signed [15:0] main_sample=gained>32767?16'sd32767:gained< -32768?-16'sd32768:gained[15:0];
 wire signed [15:0] main_sample_right=gained_right>32767?16'sd32767:gained_right< -32768?-16'sd32768:gained_right[15:0];
 reg [31:0] master_clips;
 stereo_delay effect(clk,rst,halt,dry_valid&&delay_ready,main_sample,main_sample_right,smooth_wet,delay_ready,band_audio_valid,band_left,band_right,effect_clips,effect_overruns);
 assign clips=renderer_clips+effect_clips+master_clips+singer_mix_clips+singer_vocoder_clips;
 assign simulation_idle=1'b0;
 always @(posedge clk)begin
  if(rst||halt)begin denied<=0;master_clips<=0;end
  else begin
   if(event_present&&authorization_valid&&!release_valid&&!any_lost&&!allowed)denied<=denied+1'b1;
   if(dry_valid&&(gained>32767||gained< -32768||gained_right>32767||gained_right< -32768))master_clips<=master_clips+1'b1;
  end
 end
 singer_role #(.COEFF_FILE(COEFF_FILE)) electronic_singer(
  .clk(clk),.rst(rst),.panic(halt),
  .event_valid(dispatch_valid&&(dispatch_broadcast?(&bank_ready):dispatch_part==15)),.event_ready(singer_event_ready),
  .event_kind(dispatch_kind),.event_source(dispatch_source),.event_contact(dispatch_contact),.event_part(dispatch_part),
  .event_epoch(dispatch_epoch),.event_serial(dispatch_serial),.event_note(dispatch_note),.event_velocity(dispatch_velocity),
  .sample_tick(sample_tick&&delay_ready),.frame_valid(band_audio_valid),.frame_ready(singer_frame_ready),.band_left(band_left),.band_right(band_right),
  .mic_in(microphone_sample),.voice_gain(singer_effective_gain),.left_out(singer_left),.right_out(singer_right),.audio_valid(audio_valid),
  .singer_gate(singer_gate),.singer_note(singer_note),.rejected(singer_rejected),.stale_off(singer_stale_off),
  .duplicates(singer_duplicates),.dropped_frames(singer_dropped),.mix_clips(singer_mix_clips),.vocoder_clips(singer_vocoder_clips));
endmodule
