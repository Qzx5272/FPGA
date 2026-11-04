// Universal32-slot bank: all16 role parameter sets and full choir support.
module central_voice_bank(
 input wire clk,rst,panic,sample_tick,event_valid,output wire event_ready,
 input wire [1:0] kind,input wire [7:0] source,contact,input wire [3:0] part,
 input wire [31:0] epoch,serial,input wire [6:0] note,velocity,
 output wire valid_out,output wire signed [15:0] sample_out,
 output wire [15:0] voices,cycles,output wire [31:0] rejected,deadline,clips,
 input wire probe_only,output wire done,probe_match,probe_capacity,lead_active,
 output wire signed [15:0] sample_right,
 input wire control_valid,input wire [3:0] control_part,input wire [3:0] control_parameter,input wire [13:0] control_value,input wire [16*70-1:0] patches
);
 wire [4:0] query,retire_slot;wire active,gate,retire;wire [6:0] qnote,qvelocity;
 wire[3:0]algorithm;wire[6:0]pan;wire [3:0] qpart;wire [31:0] generation,retire_generation,stale,duplicates;wire exhausted;
 wire [7:0] expression_query,bend_query;wire [2:0] vowel_query;
 wire [15:0] attack_query,sustain_query;wire [3:0] decay_query,release_query;
 assign {pan,algorithm,expression_query,bend_query,vowel_query,attack_query,sustain_query,decay_query,release_query}=patches[qpart*70+:70];
 shared_note_allocator allocator(clk,rst,panic,event_valid,event_ready,kind,source,contact,part,epoch,serial,note,velocity,
  retire,retire_slot,retire_generation,query,active,gate,qnote,qvelocity,qpart,generation,done,rejected,stale,duplicates,exhausted,probe_only,probe_match,probe_capacity,lead_active);
 shared_band_renderer #(.ENABLE_CHOIR(1)) renderer(clk,rst,panic,sample_tick,query,active,gate,qnote,qvelocity,algorithm,generation,
  retire,retire_slot,retire_generation,valid_out,sample_out,deadline,clips,cycles,voices,expression_query,bend_query,vowel_query,
  attack_query,decay_query,sustain_query,release_query,sample_right,pan);
endmodule
