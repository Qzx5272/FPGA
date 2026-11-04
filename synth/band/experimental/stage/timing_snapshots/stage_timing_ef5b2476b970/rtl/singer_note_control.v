// Monophonic last-note priority over32 held notes, using existing identity checks.
// Connect ONLY after band_core ownership authorization, not directly to raw UART.
// Part15 is the proposed electronic singer; part7 remains polyphonic choir.
module singer_note_control #(parameter PART=15)(
 input wire clk,rst,panic,event_valid,output wire event_ready,
 input wire [1:0] event_kind,input wire [7:0] event_source,event_contact,
 input wire [3:0] event_part,input wire [31:0] event_epoch,event_serial,
 input wire [6:0] event_note,event_velocity,
 output reg gate,output reg [6:0] note,velocity,
 output wire [31:0] rejected,stale_off,duplicates
);
 wire relevant=event_kind==2||event_part==PART;
 wire allocator_ready,done,exhausted,active,held;
 wire [6:0] qnote,qvelocity;wire [3:0] qpart;wire [31:0] generation;
 reg scanning;reg [4:0] query;
 reg found;reg [31:0] newest;reg [6:0] selected_note,selected_velocity;
 wire choose=active&&held&&(!found||generation>newest);
 assign event_ready=relevant ? allocator_ready&&!scanning&&!done&&!rst&&!panic : !rst&&!panic;
 note_allocator allocator(clk,rst,panic,event_valid&&event_ready&&relevant,allocator_ready,
  event_kind,event_source,event_contact,event_part,event_epoch,event_serial,event_note,event_velocity,
  scanning&&active&&!held,query,generation,query,active,held,qnote,qvelocity,qpart,generation,
  done,rejected,stale_off,duplicates,exhausted);
 always @(posedge clk)begin
  if(rst||panic)begin gate<=0;note<=60;velocity<=0;scanning<=0;query<=0;found<=0;newest<=0;selected_note<=60;selected_velocity<=0;end
  else if(done)begin scanning<=1;query<=0;found<=0;newest<=0;end
  else if(scanning)begin
   if(choose)begin found<=1;newest<=generation;selected_note<=qnote;selected_velocity<=qvelocity;end
   if(query==31)begin
    scanning<=0;gate<=found||choose;
    if(choose)begin note<=qnote;velocity<=qvelocity;end
    else if(found)begin note<=selected_note;velocity<=selected_velocity;end
   end else query<=query+1'b1;
  end
 end
endmodule
