// One owner per part. 0=machine, 1..254=human seats, 255 reserved.
// Commands: 0 take, 1 return next bar, 2 mute, 3 unmute.
// Every ownership/mute transition releases the old part through a handshake.
module track_ownership(
 input wire clk,rst,panic,bar_tick,
 input wire command_valid,output wire command_ready,
 input wire [1:0] command,input wire [3:0] command_part,input wire [7:0] command_source,
 output reg release_valid,input wire release_ready,output reg [3:0] release_part,
 input wire [3:0] query_part,output wire [7:0] owner,output wire [31:0] epoch,
 output wire muted,return_pending,output reg [31:0] conflicts,output reg exhausted,
 input wire [3:0] status_part,output wire [7:0] status_owner,output wire [31:0] status_epoch,
 input wire source_lost,input wire [7:0] lost_source
);
 reg [7:0] owners[0:15];reg [31:0] epochs[0:15];reg [15:0] mutes,returns;
 localparam IDLE=0,DECODE=1,SCAN=2,READ_EPOCH=3,INCREMENT=4,COMMIT=5,RELEASE=6;
 reg [2:0]state;reg[4:0]scan;reg bar_pending,scanning;
 reg[3:0]track;reg[7:0]claimant;reg[1:0]operation;
 reg[31:0]old_epoch,new_epoch;reg full;
 integer i;
 assign command_ready=state==IDLE&&!bar_pending&&!bar_tick&&!rst&&!panic;
 assign owner=owners[query_part];assign epoch=epochs[query_part];
 assign muted=mutes[query_part];assign return_pending=returns[query_part];
 assign status_owner=owners[status_part];assign status_epoch=epochs[status_part];
 always @(posedge clk)begin
  if(rst)begin
   for(i=0;i<16;i=i+1)begin owners[i]<=0;epochs[i]<=1;end
   mutes<=0;returns<=0;state<=IDLE;release_valid<=0;conflicts<=0;exhausted<=0;bar_pending<=0;scan<=0;
   scanning<=0;track<=0;claimant<=0;old_epoch<=0;new_epoch<=0;full<=0;operation<=0;release_part<=0;
  end else if(panic)begin
   for(i=0;i<16;i=i+1)returns[i]<=owners[i]>=17&&owners[i]<=20;
   state<=IDLE;release_valid<=0;bar_pending<=0;scan<=0;scanning<=0;
  end else begin
   if(bar_tick)bar_pending<=1;
   case(state)
    IDLE:begin
     if(bar_pending||bar_tick)begin bar_pending<=0;scan<=0;scanning<=1;state<=SCAN;end
     else if(command_valid)begin track<=command_part;claimant<=command_source;operation<=command;scanning<=0;state<=DECODE;end
    end
    DECODE:begin
     state<=IDLE;
     case(operation)
      0:if(claimant==0||claimant==255||(owners[track]!=0&&owners[track]!=claimant))conflicts<=conflicts+1'b1;
        else if(owners[track]==claimant)returns[track]<=0;
        else state<=READ_EPOCH;
      1:if(owners[track]==claimant&&claimant!=0)returns[track]<=1;else conflicts<=conflicts+1'b1;
      2:begin mutes[track]<=1;release_part<=track;release_valid<=1;state<=RELEASE;end
      3:mutes[track]<=0;
     endcase
    end
    SCAN:begin
     if(scan==16)begin state<=IDLE;scanning<=0;end
     else if(returns[scan[3:0]])begin track<=scan[3:0];claimant<=0;state<=READ_EPOCH;end
     else scan<=scan+1'b1;
    end
    READ_EPOCH:begin old_epoch<=epochs[track];state<=INCREMENT;end
    INCREMENT:begin new_epoch<=old_epoch+1'b1;full<=&old_epoch;state<=COMMIT;end
    COMMIT:begin
     if(full)begin exhausted<=1;state<=scanning?SCAN:IDLE;
      if(scanning)begin returns[track]<=0;scan<=scan+1'b1;end
     end else begin
      owners[track]<=claimant;epochs[track]<=new_epoch;returns[track]<=0;
      release_part<=track;release_valid<=1;state<=RELEASE;
     end
    end
    RELEASE:if(release_ready)begin release_valid<=0;state<=scanning?SCAN:IDLE;if(scanning)scan<=scan+1'b1;end
   endcase
   if(source_lost)for(i=0;i<16;i=i+1)if(owners[i]==lost_source&&lost_source!=0)returns[i]<=1;
   if(source_lost&&!scanning&&claimant==lost_source&&lost_source!=0&&
       (state==DECODE||state==READ_EPOCH||state==INCREMENT))state<=IDLE;
   if(source_lost&&state==COMMIT&&claimant==lost_source&&lost_source!=0)returns[track]<=1;
  end
 end
endmodule
