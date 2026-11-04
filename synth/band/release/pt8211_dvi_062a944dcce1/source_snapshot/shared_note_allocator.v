// Bounded linear allocator. No hidden stealing: full pool rejects a new note.
// Event kinds 0=on, 1=off, 2=release source, 3=release part.
// Caller holds event_valid/data until ready. Panic bypasses the event path.
// Renderer retires release tails using the slot's generation token.
module shared_note_allocator #(parameter VOICES=32,parameter INDEX_BITS=5)(
 input wire clk,rst,panic,
 input wire event_valid,output wire event_ready,
 input wire [1:0] event_kind,input wire [7:0] event_source,event_contact,
 input wire [3:0] event_part,input wire [31:0] event_epoch,event_serial,
 input wire [6:0] event_note,event_velocity,
 input wire retire_valid,input wire [INDEX_BITS-1:0] retire_slot,input wire [31:0] retire_generation,
 input wire [INDEX_BITS-1:0] query_slot,
 output wire query_active,query_gate,output wire [6:0] query_note,query_velocity,
 output wire [3:0] query_part,output wire [31:0] query_generation,
 output reg done,output reg [31:0] rejected,stale_off,duplicates,
 output reg exhausted,
 input wire probe_only,output reg probe_match,probe_capacity,output wire lead_active
);
 reg [VOICES-1:0] active,gate;
 reg [3:0] part[0:VOICES-1];
 wire [VOICES-1:0] lead_slots;
 genvar lead_i;
 generate for(lead_i=0;lead_i<VOICES;lead_i=lead_i+1)begin:lead_query
  assign lead_slots[lead_i]=active[lead_i]&&(part[lead_i]==6);
 end endgenerate
 assign lead_active=|lead_slots;
 reg [7:0] source[0:VOICES-1],contact[0:VOICES-1];
 reg [31:0] epoch[0:VOICES-1],serial[0:VOICES-1],generation[0:VOICES-1];
 reg [6:0] note[0:VOICES-1],velocity[0:VOICES-1];
 reg [31:0] next_generation;
 reg [1:0] state,kind;
 reg [7:0] src,key;
 reg [3:0] track;
 reg [31:0] ep,seq;
 reg [6:0] pitch,vel;
 reg [INDEX_BITS-1:0] scan,free_slot;
 reg found_free,found_match,probing;
 wire identity=active[scan]&&source[scan]==src&&contact[scan]==key&&part[scan]==track&&epoch[scan]==ep&&serial[scan]==seq;
 assign event_ready=state==0&&!rst&&!panic;
 assign query_active=active[query_slot];assign query_gate=gate[query_slot];
 assign query_note=note[query_slot];assign query_velocity=velocity[query_slot];
 assign query_part=part[query_slot];assign query_generation=generation[query_slot];
 always @(posedge clk)begin
  if(rst)begin
   active<=0;gate<=0;state<=0;done<=0;rejected<=0;stale_off<=0;duplicates<=0;
   next_generation<=1;exhausted<=0;probing<=0;probe_match<=0;probe_capacity<=0;
  end else if(panic)begin active<=0;gate<=0;state<=0;done<=0;end
  else begin
   done<=0;
   if(retire_valid&&active[retire_slot]&&!gate[retire_slot]&&generation[retire_slot]==retire_generation)
    active[retire_slot]<=0;
   case(state)
    0:if(event_valid)begin
     probing<=probe_only;kind<=event_kind;src<=event_source;key<=event_contact;track<=event_part;
     ep<=event_epoch;seq<=event_serial;pitch<=event_note;vel<=event_velocity;
     scan<=0;found_free<=0;found_match<=0;state<=1;
    end
    1:begin
     if(!active[scan]&&!found_free)begin free_slot<=scan;found_free<=1;end
     if(identity)begin found_match<=1;if(kind==1&&!probing)gate[scan]<=0;end
     if(!probing&&active[scan]&&((kind==2&&source[scan]==src)||(kind==3&&part[scan]==track)))gate[scan]<=0;
     if(scan==VOICES-1)state<=2;else scan<=scan+1'b1;
    end
    2:begin
     if(probing)begin probe_match<=found_match;probe_capacity<=found_free&&!exhausted;end
     else if(kind==0)begin
      if(found_match)duplicates<=duplicates+1'b1;
      else if(!found_free||exhausted||vel==0)rejected<=rejected+1'b1;
      else begin
       active[free_slot]<=1;gate[free_slot]<=1;source[free_slot]<=src;contact[free_slot]<=key;
       part[free_slot]<=track;epoch[free_slot]<=ep;serial[free_slot]<=seq;
       note[free_slot]<=pitch;velocity[free_slot]<=vel;generation[free_slot]<=next_generation;
       if(next_generation==32'hffffffff)exhausted<=1;else next_generation<=next_generation+1'b1;
      end
     end else if(kind==1&&!found_match)stale_off<=stale_off+1'b1;
     done<=1;state<=0;
    end
    default:state<=0;
   endcase
  end
 end
endmodule
