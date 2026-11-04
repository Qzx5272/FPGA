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
 reg [1:0] state;reg [4:0] scan;reg bar_pending;
 integer i;
 assign command_ready=state==0&&!bar_pending&&!bar_tick&&!rst&&!panic;
 assign owner=owners[query_part];assign epoch=epochs[query_part];
 assign muted=mutes[query_part];assign return_pending=returns[query_part];
 assign status_owner=owners[status_part];assign status_epoch=epochs[status_part];
 always @(posedge clk)begin
  if(rst)begin
   for(i=0;i<16;i=i+1)begin owners[i]<=0;epochs[i]<=1;end
   mutes<=0;returns<=0;state<=0;release_valid<=0;conflicts<=0;exhausted<=0;bar_pending<=0;scan<=0;
  end else if(panic)begin
   // Keep epochs and owners: panic stops audio without silently granting another seat control.
   returns<=0;state<=0;release_valid<=0;bar_pending<=0;
  end else begin
   if(bar_tick)bar_pending<=1;
   case(state)
    0:begin
     if(bar_pending||bar_tick)begin bar_pending<=0;scan<=0;state<=2;end
     else if(command_valid)begin
      case(command)
       0:if(command_source==0||command_source==255||(owners[command_part]!=0&&owners[command_part]!=command_source))conflicts<=conflicts+1'b1;
         else if(owners[command_part]!=command_source)begin
          if(epochs[command_part]==32'hffffffff)exhausted<=1;
          else begin owners[command_part]<=command_source;epochs[command_part]<=epochs[command_part]+1'b1;
           returns[command_part]<=0;release_part<=command_part;release_valid<=1;state<=1;end
         end
       1:if(owners[command_part]==command_source&&command_source!=0)returns[command_part]<=1;
         else conflicts<=conflicts+1'b1;
       2:begin mutes[command_part]<=1;release_part<=command_part;release_valid<=1;state<=1;end
       3:mutes[command_part]<=0;
      endcase
     end
    end
    1:if(release_ready)begin release_valid<=0;state<=0;end
    2:begin
     if(scan==16)state<=0;
     else if(returns[scan[3:0]])begin
      if(epochs[scan[3:0]]==32'hffffffff)begin exhausted<=1;returns[scan[3:0]]<=0;scan<=scan+1'b1;end
      else begin
       owners[scan[3:0]]<=0;epochs[scan[3:0]]<=epochs[scan[3:0]]+1'b1;returns[scan[3:0]]<=0;
       release_part<=scan[3:0];release_valid<=1;state<=3;
      end
     end else scan<=scan+1'b1;
    end
    3:if(release_ready)begin release_valid<=0;scan<=scan+1'b1;state<=2;end
   endcase
   if(source_lost)for(i=0;i<16;i=i+1)if(owners[i]==lost_source&&lost_source!=0)returns[i]<=1;
  end
 end
endmodule
