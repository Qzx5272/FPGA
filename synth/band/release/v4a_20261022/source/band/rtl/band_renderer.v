// Part bank: kick/snare/hat/bass/FM piano/reed/lead/additive vowel-like choir.
// One shared interpolated sine pipeline; independent phase/envelope per voice.
module band_renderer #(parameter VOICES=32,parameter INDEX_BITS=5)(
 input wire clk,rst,panic,sample_tick,
 output reg [INDEX_BITS-1:0] query_slot,
 input wire query_active,query_gate,input wire [6:0] query_note,query_velocity,
 input wire [3:0] query_part,input wire [31:0] query_generation,
 output reg retire_valid,output reg [INDEX_BITS-1:0] retire_slot,output reg [31:0] retire_generation,
 output reg valid_out,output reg signed [15:0] sample_out,
 output reg [31:0] deadline_miss,clip_count,output reg [15:0] last_cycles,
 output reg [15:0] active_voices
);
 `include "midi_increment.vh"
 reg [31:0] phase[0:VOICES-1],seen_generation[0:VOICES-1];
 reg [15:0] envelope[0:VOICES-1];
 reg [31:0] noises[0:VOICES-1];reg signed [17:0] previous_noise[0:VOICES-1];
 reg [4:0] state;reg [15:0] cycles,count;
 reg [31:0] ph,inc,gen;reg [15:0] env;
 reg [6:0] velocity;reg held,patch;
 reg [3:0] role;reg [31:0] noise;
 reg signed [20:0] vowel_sum;
 reg osc_request;reg [31:0] osc_phase;
 wire osc_valid;wire signed [17:0] osc_sample;
 hq_sine_quarter sine(clk,rst||panic,osc_request,osc_phase,osc_valid,osc_sample);
 reg signed [17:0] mod_sample;
 reg signed [34:0] modulation;
 reg signed [19:0] wave_sample;
 reg signed [36:0] envelope_product;
 reg signed [28:0] velocity_product;
 reg signed [31:0] total;
 wire [15:0] decay=(env>>(role==0?9:role==1?8:role==2?7:13))+16'd1;
 wire [15:0] release_step=(env>>8)+16'd1;
 integer i;
 always @(posedge clk)begin
  if(rst||panic)begin
   state<=0;query_slot<=0;retire_valid<=0;valid_out<=0;sample_out<=0;
   osc_request<=0;deadline_miss<=0;clip_count<=0;last_cycles<=0;active_voices<=0;cycles<=0;total<=0;
   for(i=0;i<VOICES;i=i+1)begin phase[i]<=0;envelope[i]<=0;seen_generation[i]<=0;noises[i]<=1;previous_noise[i]<=0;end
  end else begin
   retire_valid<=0;valid_out<=0;osc_request<=0;
   if(state!=0)cycles<=cycles+1'b1;
   if(sample_tick&&state!=0)deadline_miss<=deadline_miss+1'b1;
   case(state)
    0:if(sample_tick)begin query_slot<=0;total<=0;cycles<=0;count<=0;state<=1;end
    1:begin
     if(!query_active)begin envelope[query_slot]<=0;state<=12;end
     else begin
      count<=count+1'b1;velocity<=query_velocity;held<=query_gate;patch<=query_part>=5;gen<=query_generation;role<=query_part;
      inc<=query_part==1?32'd16106127:midi_increment(query_note);
      if(seen_generation[query_slot]!=query_generation)begin
       ph<=0;env<=query_part>=5?16'd256:16'd65535;noise<=(query_generation^32'hdeadbeef)|32'd1;
      end else begin ph<=phase[query_slot];env<=envelope[query_slot];noise<=noises[query_slot];end
      state<=2;
     end
    end
    2:begin
     // High notes disable the second harmonic/FM to bound aliasing in this first patch bank.
     osc_phase<=role==7 ? (inc<32'h0ccccccc ? ph*3:32'd0):(inc<32'h20000000 ? (ph<<1):32'd0);osc_request<=1;state<=3;
    end
    3:if(osc_valid)begin mod_sample<=osc_sample;modulation<=osc_sample*$signed({1'b0,env});state<=4;end
    4:begin osc_phase<=role==7 ? (inc<32'h0ccccccc ? ph*5:32'd0):(patch||role<3?ph:ph+(modulation>>>3));osc_request<=1;state<=5;end
    5:if(osc_valid)begin
     // Convex harmonic mix retains headroom even for 32 coherent held notes.
     if(role==7)begin
      vowel_sum<=($signed(mod_sample)*21'sd2)+($signed(osc_sample)*21'sd2);
      osc_phase<=inc<32'h0ccccccc ? ph*10:32'd0;osc_request<=1;state<=9;
     end else begin
      if(role==1)wave_sample<=($signed(osc_sample)+$signed(noise[31:14])*20'sd3)>>>2;
      else if(role==2)wave_sample<=($signed(noise[31:14])-$signed(previous_noise[query_slot]))>>>1;
      else wave_sample<=patch?(($signed(osc_sample)*20'sd3+$signed(mod_sample))>>>2):$signed(osc_sample);
      state<=6;
     end
    end
    9:if(osc_valid)begin vowel_sum<=vowel_sum+$signed(osc_sample);osc_phase<=ph;osc_request<=1;state<=10;end
    10:if(osc_valid)begin wave_sample<=(vowel_sum+$signed(osc_sample)*21'sd3)>>>3;state<=6;end
    6:begin envelope_product<=wave_sample*$signed({1'b0,env});state<=7;end
    7:begin velocity_product<=(envelope_product>>>16)*$signed({1'b0,velocity});state<=8;end
    8:begin
     // Sine is 18-bit; /4 converts to 16-bit, /32 supplies fixed mix headroom.
     total<=total+(velocity_product>>>14);
     phase[query_slot]<=role==0?ph+inc+((inc>>6)*(env>>8)):ph+inc;seen_generation[query_slot]<=gen;
     noises[query_slot]<={noise[30:0],noise[31]^noise[21]^noise[1]^noise[0]};previous_noise[query_slot]<=noise[31:14];
     if(!held)begin
      if(env<=release_step)begin
       envelope[query_slot]<=0;retire_valid<=1;retire_slot<=query_slot;retire_generation<=gen;
      end else envelope[query_slot]<=env-release_step;
     end else if(patch)envelope[query_slot]<=env>65279?16'd65535:env+16'd256;
     else envelope[query_slot]<=env<=decay?16'd0:env-decay;
     state<=12;
    end
    12:if(query_slot==VOICES-1)state<=13;else begin query_slot<=query_slot+1'b1;state<=1;end
    13:begin
     if(total>32767)begin sample_out<=32767;clip_count<=clip_count+1'b1;end
     else if(total< -32768)begin sample_out<=-32768;clip_count<=clip_count+1'b1;end
     else sample_out<=total[15:0];
     last_cycles<=cycles;active_voices<=count;valid_out<=1;state<=0;
    end
    default:state<=0;
   endcase
  end
 end
endmodule
