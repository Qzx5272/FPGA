// HDL delay / diffuse multi-tap reverb / modulated chorus.
// Bounded feedback1/4; mix is convex.16-bit PCM,48kHz. No prerecorded audio.
module stereo_space(
 input wire clk,rst,clear,valid_in,input wire signed[15:0]left_in,right_in,
 input wire[6:0]wet,input wire[1:0]mode,
 output reg ready,valid_out,output reg signed[15:0]left_out,right_out,
 output reg[31:0]clip_count,overrun_count);
 reg signed[15:0]ml[0:8191],mr[0:8191];reg[12:0]pos,clearing;
 reg[1:0]state;reg[18:0]lfo;reg[1:0]held_mode;reg[6:0]mix;
 reg signed[15:0]dry_l,dry_r,e1l,e1r,e2l,e2r,e3l,e3r;
 wire[7:0]triangle=lfo[18]?~lfo[17:10]:lfo[17:10];
 wire[12:0]tap1=mode==2?13'd480+{5'd0,triangle}:mode==1?13'd1559:13'd8191;
 wire[12:0]a1=pos-tap1,a2=pos-13'd3251,a3=pos-13'd6011;
 wire signed[18:0]sum_l=$signed(e1l)+$signed(e2r)+$signed(e3l);
 wire signed[18:0]sum_r=$signed(e1r)+$signed(e2l)+$signed(e3r);
 wire signed[18:0]echo_l=held_mode==1?sum_l/3:$signed(e1l);
 wire signed[18:0]echo_r=held_mode==1?sum_r/3:$signed(e1r);
 wire signed[19:0]fb_l=$signed(dry_l)+(echo_r/4),fb_r=$signed(dry_r)+(echo_l/4);
 wire signed[8:0]dry_gain=9'sd128-$signed({2'b0,mix}),wet_gain=$signed({2'b0,mix});
 wire signed[28:0]out_l=($signed(dry_l)*dry_gain+echo_l*wet_gain)>>>7;
 wire signed[28:0]out_r=($signed(dry_r)*dry_gain+echo_r*wet_gain)>>>7;
 function[15:0]sat;input signed[28:0]v;begin sat=v>32767?16'h7fff:v< -32768?16'h8000:v[15:0];end endfunction
 always @(posedge clk)begin
  if(rst||clear)begin ready<=0;valid_out<=0;pos<=0;clearing<=0;state<=0;lfo<=0;clip_count<=0;overrun_count<=0;left_out<=0;right_out<=0;end
  else begin
   valid_out<=0;
   if(!ready)begin ml[clearing]<=0;mr[clearing]<=0;if(&clearing)ready<=1;else clearing<=clearing+1'b1;end
   else begin
    if(valid_in&&state!=0)overrun_count<=overrun_count+1'b1;
    case(state)
    0:if(valid_in)begin
     dry_l<=left_in;dry_r<=right_in;mix<=wet;held_mode<=mode;
     e1l<=ml[a1];e1r<=mr[a1];e2l<=ml[a2];e2r<=mr[a2];e3l<=ml[a3];e3r<=mr[a3];state<=1;
    end
    1:begin
     ml[pos]<=held_mode==2?dry_l:sat(fb_l);mr[pos]<=held_mode==2?dry_r:sat(fb_r);
     left_out<=sat(out_l);right_out<=sat(out_r);valid_out<=1;pos<=pos+1'b1;lfo<=lfo+1'b1;state<=0;
     if(out_l>32767||out_l< -32768||out_r>32767||out_r< -32768||fb_l>32767||fb_l< -32768||fb_r>32767||fb_r< -32768)clip_count<=clip_count+1'b1;
    end
    default:state<=0;
    endcase
   end
  end
 end
endmodule
