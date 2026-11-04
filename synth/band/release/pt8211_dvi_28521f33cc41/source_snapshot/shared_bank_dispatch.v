// Single-owner two-phase bank allocation. Probe never mutates a voice.
// Banks retain their own identities/generation tokens and release tails.
// All payload outputs stay fixed until the complete transaction finishes.
module shared_bank_dispatch #(parameter BANKS=8, parameter BANK_BITS=3)(
 input wire clk,rst,panic,
 input wire event_valid,output wire event_ready,
 input wire [1:0] event_kind,input wire [7:0] event_source,event_contact,
 input wire [3:0] event_part,input wire [31:0] event_epoch,event_serial,
 input wire [6:0] event_note,event_velocity,
 input wire [BANKS-1:0] bank_ready,bank_done,bank_match,bank_capacity,
 output wire [BANKS-1:0] bank_valid,output wire probe_only,
 output reg [1:0] kind,output reg [7:0] source,contact,
 output reg [3:0] part,output reg [31:0] epoch,serial,
 output reg [6:0] note,velocity,
 output reg done,output reg [31:0] rejected,duplicates
);
 localparam IDLE=0,PROBE=1,WAIT_PROBE=2,SELECT=3,COMMIT=4,WAIT_COMMIT=5;
 reg [2:0] state;
 reg [BANKS-1:0] pending,matched,available,selected;
 reg [BANK_BITS-1:0] cursor,chosen;
 integer i,index;
 reg found;
 reg [BANKS-1:0] choice;
 reg [BANK_BITS-1:0] choice_index;
 assign event_ready=state==IDLE&&!rst&&!panic;
 assign probe_only=state==PROBE;
 wire commit_ready=&(bank_ready|~selected);
 assign bank_valid=(rst||panic)?{BANKS{1'b0}}:
     state==PROBE&&(&bank_ready)?{BANKS{1'b1}}:
     state==COMMIT&&commit_ready?selected:{BANKS{1'b0}};
 always @* begin
  found=0;choice=0;choice_index=0;
  for(i=0;i<BANKS;i=i+1)begin
   index=cursor+i;
   if(index>=BANKS)index=index-BANKS;
   if(!found&&available[index])begin
    found=1;choice[index]=1;choice_index=index;
   end
  end
 end
 always @(posedge clk)begin
  if(rst)begin
   state<=IDLE;pending<=0;matched<=0;available<=0;selected<=0;
   cursor<=0;chosen<=0;done<=0;rejected<=0;duplicates<=0;
   kind<=0;source<=0;contact<=0;part<=0;epoch<=0;serial<=0;note<=0;velocity<=0;
  end else if(panic)begin state<=IDLE;pending<=0;selected<=0;done<=0;end
  else begin
   done<=0;
   case(state)
    IDLE:if(event_valid)begin
     kind<=event_kind;source<=event_source;contact<=event_contact;
     part<=event_part;epoch<=event_epoch;serial<=event_serial;
     note<=event_note;velocity<=event_velocity;
     matched<=0;available<=0;
     if(event_kind==0)state<=PROBE;
     else begin selected<={BANKS{1'b1}};state<=COMMIT;end
    end
    PROBE:if(&bank_ready)begin pending<={BANKS{1'b1}};state<=WAIT_PROBE;end
    WAIT_PROBE:begin
     pending<=pending&~bank_done;
     matched<=(matched&~(pending&bank_done))|(bank_match&pending&bank_done);
     available<=(available&~(pending&bank_done))|(bank_capacity&pending&bank_done);
     if((pending&~bank_done)==0)state<=SELECT;
    end
    SELECT:begin
     if(|matched)begin duplicates<=duplicates+1'b1;done<=1;state<=IDLE;end
     else if(!found||velocity==0)begin rejected<=rejected+1'b1;done<=1;state<=IDLE;end
     else begin selected<=choice;chosen<=choice_index;state<=COMMIT;end
    end
    COMMIT:if(commit_ready)begin pending<=selected;state<=WAIT_COMMIT;end
    WAIT_COMMIT:begin
     pending<=pending&~bank_done;
     if((pending&~bank_done)==0)begin
      if(kind==0)cursor<=chosen==BANKS-1?0:chosen+1'b1;
      done<=1;state<=IDLE;
     end
    end
    default:state<=IDLE;
   endcase
  end
 end
endmodule
