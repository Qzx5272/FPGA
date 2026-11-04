// 50 MHz core, 48 kHz stereo PCM. Envelope sets brightness; attacks rotate hue.
module rhythm_strip #(parameter LED_COUNT=64)(
 input wire clk,rst,valid,
 input wire signed [15:0] left,right,
 output reg data
);
 wire [15:0] mag_l=left[15]?-left:left;
 wire [15:0] mag_r=right[15]?-right:right;
 wire [15:0] peak=mag_l>mag_r?mag_l:mag_r;
 reg [15:0] window_peak,envelope;
 reg [8:0] samples;
 reg [2:0] hue;
 reg [3:0] cooldown;
 wire [15:0] level=window_peak>peak?window_peak:peak;
 wire [16:0] onset_threshold={1'b0,envelope}+(envelope>>2)+17'd96;
 always @(posedge clk)begin
  if(rst)begin samples<=0;window_peak<=0;envelope<=0;cooldown<=0;hue<=0;end
  else if(valid)begin
   samples<=samples+1'b1;
   if(&samples)begin
    window_peak<=0;
    if(level>=envelope)envelope<=level;
    else envelope<=envelope-((envelope-level)>>2)-1'b1;
    if(cooldown!=0)cooldown<=cooldown-1'b1;
    else if(level>onset_threshold)begin hue<=hue==5?0:hue+1'b1;cooldown<=8;end
   end else window_peak<=level;
  end
 end
 wire [7:0] light=envelope<64?0:envelope>=8192?8'd64:envelope[12:7]+1'b1;
 reg [23:0] color;
 always @*case(hue) // GRB, MSB first
  0:color={light>>2,light,8'd0};
  1:color={light,light>>1,8'd0};
  2:color={light,8'd0,light>>1};
  3:color={light>>1,8'd0,light};
  4:color={8'd0,light>>1,light};
  default:color={8'd0,light,light>>2};
 endcase
 reg [14:0] gap;
 reg [$clog2(LED_COUNT+1)-1:0] pixel;
 reg [4:0] bit_number;
 reg [5:0] phase;
 reg [23:0] frame_color;
 reg sending;
 always @(posedge clk)begin
  if(rst)begin gap<=0;pixel<=0;bit_number<=23;phase<=0;data<=0;sending<=0;frame_color<=0;end
  else if(!sending)begin
   data<=0;
   if(gap==15999)begin gap<=0;frame_color<=color;sending<=1;end
   else gap<=gap+1'b1;
  end else begin
   data<=phase<(frame_color[bit_number]?33:16);
   if(phase==62)begin
    phase<=0;
    if(bit_number!=0)bit_number<=bit_number-1'b1;
    else begin
     bit_number<=23;
     if(pixel==LED_COUNT-1)begin pixel<=0;sending<=0;end
     else pixel<=pixel+1'b1;
    end
   end else phase<=phase+1'b1;
  end
 end
endmodule
