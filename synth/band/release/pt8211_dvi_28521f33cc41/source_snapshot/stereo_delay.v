// Stereo cross-feedback delay. Fixed feedback 1/2 guarantees decay.
// Memories are cleared before ready; no uninitialized RAM reaches audio.
// wet: Q0.7 mix 0..127. Latency: 2 clocks after accepted valid_in.
module stereo_delay #(parameter ADDRESS_BITS=13)(
 input wire clk,rst,clear,valid_in,
 input wire signed [15:0] left_in,right_in,
 input wire [6:0] wet,
 output reg ready,valid_out,
 output reg signed [15:0] left_out,right_out,
 output reg [31:0] clip_count,overrun_count
);
 localparam DEPTH=1<<ADDRESS_BITS;
 reg signed [15:0] mem_l[0:DEPTH-1],mem_r[0:DEPTH-1];
 reg [ADDRESS_BITS-1:0] pos,clear_pos;
 reg [1:0] state;
 reg signed [15:0] dry_l,dry_r,echo_l,echo_r;
 reg [6:0] mix;
 reg signed [23:0] mixed_l,mixed_r;
 // Truncate feedback toward zero: arithmetic shift alone traps negative tails at -1.
 wire signed [16:0] half_l=($signed({echo_l[15],echo_l})+ (echo_l[15]?17'sd1:17'sd0))>>>1;
 wire signed [16:0] half_r=($signed({echo_r[15],echo_r})+ (echo_r[15]?17'sd1:17'sd0))>>>1;
 wire signed [16:0] feedback_l=$signed(dry_l)+half_r;
 wire signed [16:0] feedback_r=$signed(dry_r)+half_l;
 wire signed [8:0] dry_gain=9'sd128-$signed({2'b00,mix});
 wire signed [8:0] wet_gain=$signed({2'b00,mix});
 wire signed [24:0] dry_product_l=dry_l*dry_gain,dry_product_r=dry_r*dry_gain;
 wire signed [24:0] wet_product_l=echo_l*wet_gain,wet_product_r=echo_r*wet_gain;
 function [15:0] sat17;
 input signed [16:0] x;
 begin if(x>32767)sat17=16'h7fff;else if(x< -32768)sat17=16'h8000;else sat17=x[15:0];end
 endfunction
 always @(posedge clk) begin
  if(rst||clear)begin
   ready<=0;clear_pos<=0;pos<=0;state<=0;valid_out<=0;
   left_out<=0;right_out<=0;clip_count<=0;overrun_count<=0;
  end else begin
   valid_out<=0;
   if(!ready)begin
    mem_l[clear_pos]<=0;mem_r[clear_pos]<=0;
    if(clear_pos==DEPTH-1)begin ready<=1;pos<=0;end
    else clear_pos<=clear_pos+1'b1;
   end else begin
    if(valid_in&&state!=0)overrun_count<=overrun_count+1'b1;
    case(state)
     0:if(valid_in)begin
      dry_l<=left_in;dry_r<=right_in;mix<=wet;
      echo_l<=mem_l[pos];echo_r<=mem_r[pos];state<=1;
     end
     1:begin
      mem_l[pos]<=sat17(feedback_l);mem_r[pos]<=sat17(feedback_r);
      mixed_l<=(dry_product_l+wet_product_l)>>>7;
      mixed_r<=(dry_product_r+wet_product_r)>>>7;
      if(feedback_l>32767||feedback_l< -32768||feedback_r>32767||feedback_r< -32768)
       clip_count<=clip_count+1'b1;
      state<=2;
     end
     2:begin
      left_out<=mixed_l[15:0];right_out<=mixed_r[15:0];
      valid_out<=1;pos<=pos+1'b1;state<=0;
     end
     default:state<=0;
    endcase
   end
  end
 end
endmodule
