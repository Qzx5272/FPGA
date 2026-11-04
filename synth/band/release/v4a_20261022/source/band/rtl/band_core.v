// Integrated performance core. Standardized events can originate from local sensors or host.
module band_core(
 input wire clk,rst,panic,sample_tick,play,stop,
 input wire manual_valid,output wire manual_ready,input wire [1:0] manual_kind,
 input wire [7:0] manual_source,manual_contact,input wire [3:0] manual_part,
 input wire [31:0] manual_epoch,manual_serial,input wire [6:0] manual_note,manual_velocity,
 input wire command_valid,output wire command_ready,input wire [1:0] command,
 input wire [3:0] command_part,input wire [7:0] command_source,
 input wire [6:0] wet,master,
 output wire signed [15:0] left_out,right_out,output wire audio_valid,
 output wire playing,output wire [31:0] song_position,
 input wire [3:0] status_part,output wire [7:0] status_owner,output wire [31:0] status_epoch,
 output wire [15:0] active_voices,render_cycles,
 output wire [31:0] rejected,deadline_miss,clips,output reg [31:0] denied,
 input wire source_lost,output wire lost_ready,input wire [7:0] lost_source
);
 wire halt=panic||stop;
 wire auto_valid,auto_ready,bar_tick;wire [1:0] auto_kind;wire [3:0] auto_part;
 wire [6:0] auto_note,auto_velocity;wire [31:0] auto_serial,late_events;wire [7:0] bar_position;
 song_sequencer score(clk,rst,panic,sample_tick,play,stop,playing,bar_tick,auto_valid,auto_ready,
  auto_kind,auto_part,auto_note,auto_velocity,auto_serial,song_position,late_events,bar_position);
 wire release_valid,release_ready;wire [3:0] release_part;
 wire [3:0] routed_part=manual_valid?manual_part:auto_part;
 wire [7:0] owner;wire [31:0] epoch;wire muted,pending,ownership_exhausted;wire [31:0] conflicts;
 // Status is read through a second combinational query without duplicating ownership state.
 track_ownership ownership(clk,rst,halt,bar_tick,command_valid,command_ready,command,command_part,command_source,
  release_valid,release_ready,release_part,routed_part,owner,epoch,muted,pending,conflicts,ownership_exhausted,
  status_part,status_owner,status_epoch,source_lost&&lost_ready,lost_source);
 wire event_present=manual_valid||auto_valid;
 wire [1:0] kind=manual_valid?manual_kind:auto_kind;
 wire [7:0] source=manual_valid?manual_source:8'd0;
 wire allowed=(source==owner)&&(!manual_valid||manual_epoch==epoch)&&!(muted&&kind==0)&&!ownership_exhausted;
 wire alloc_ready;
 assign manual_ready=!halt&&!release_valid&&!source_lost&&(allowed?alloc_ready:1'b1);
 assign auto_ready=!halt&&!release_valid&&!source_lost&&!manual_valid&&(allowed?alloc_ready:1'b1);
 assign release_ready=alloc_ready;
 assign lost_ready=alloc_ready&&!release_valid&&!halt;
 wire [4:0] slot,retire_slot;wire query_active,query_gate,retire;
 wire [6:0] note,velocity;wire [3:0] part;wire [31:0] generation,retire_generation;
 wire alloc_done,alloc_exhausted;wire [31:0] stale,duplicates;
 note_allocator allocator(clk,rst,halt,
  release_valid||source_lost||(event_present&&allowed),alloc_ready,
  release_valid?2'd3:source_lost?2'd2:kind,release_valid?8'd0:source_lost?lost_source:source,
  manual_valid?manual_contact:{1'b0,auto_note},release_valid?release_part:routed_part,
  epoch,manual_valid?manual_serial:auto_serial,manual_valid?manual_note:auto_note,manual_valid?manual_velocity:auto_velocity,
  retire,retire_slot,retire_generation,slot,query_active,query_gate,note,velocity,part,generation,
  alloc_done,rejected,stale,duplicates,alloc_exhausted);
 wire dry_valid;wire signed [15:0] dry;wire [31:0] renderer_clips;
 band_renderer renderer(clk,rst,halt,sample_tick,slot,query_active,query_gate,note,velocity,part,generation,
  retire,retire_slot,retire_generation,dry_valid,dry,deadline_miss,renderer_clips,render_cycles,active_voices);
 wire delay_ready;wire [31:0] effect_clips,effect_overruns;
 wire signed [23:0] master_product=dry*$signed({1'b0,master});
 wire signed [23:0] gained=master_product>>>5;
 wire signed [15:0] main_sample=gained>32767?16'sd32767:gained< -32768?-16'sd32768:gained[15:0];
 reg [31:0] master_clips;
 stereo_delay effect(clk,rst,halt,dry_valid&&delay_ready,main_sample,main_sample,wet,delay_ready,audio_valid,left_out,right_out,effect_clips,effect_overruns);
 assign clips=renderer_clips+effect_clips+master_clips;
 always @(posedge clk)begin
  if(rst||halt)begin denied<=0;master_clips<=0;end
  else begin
   if(event_present&&!release_valid&&!source_lost&&!allowed)denied<=denied+1'b1;
   if(dry_valid&&(gained>32767||gained< -32768))master_clips<=master_clips+1'b1;
  end
 end
endmodule
