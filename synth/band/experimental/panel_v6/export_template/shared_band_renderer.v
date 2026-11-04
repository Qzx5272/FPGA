// Part bank: kick/snare/hat/bass/FM piano/reed/lead/additive vowel-like choir.
// One shared interpolated sine pipeline; independent phase/envelope per voice.
module shared_band_renderer #(parameter VOICES=32,parameter INDEX_BITS=5,parameter ENABLE_CHOIR=1)(
 input wire clk,rst,panic,sample_tick,
 output reg [INDEX_BITS-1:0] query_slot,
 input wire query_active,query_gate,input wire [6:0] query_note,query_velocity,
 input wire [3:0] query_part,input wire [31:0] query_generation,
 output reg retire_valid,output reg [INDEX_BITS-1:0] retire_slot,output reg [31:0] retire_generation,
 output reg valid_out,output reg signed [15:0] sample_out,
 output reg [31:0] deadline_miss,clip_count,output reg [15:0] last_cycles,
 output reg [15:0] active_voices,
 input wire [7:0] expression,bend,input wire [2:0] vowel,
 input wire [15:0] attack_step,input wire [3:0] decay_shift,input wire [15:0] sustain_level,input wire [3:0] release_shift,
 output reg signed [15:0] sample_right,input wire[6:0]query_pan
);
 `include "midi_increment.vh"
 `include "bend_ratio.vh"
 `include "vowel_harmonics.vh"
 // Three synchronous 64-bit words per voice avoid the former 160-bit-wide
 // asynchronous memory mapping. A validity mask makes stale RAM unreachable.
 reg [63:0] state_memory[0:VOICES*3-1];reg [63:0] state_read_data;
 reg [159:0] prior_state;reg [1:0] read_issue,read_receive;
 reg [VOICES-1:0] state_valid;
 wire [INDEX_BITS+1:0] state_base=({2'd0,query_slot}<<1)+query_slot;
 wire [INDEX_BITS+1:0] state_read_address=state_base+read_issue;
 always @(posedge clk)state_read_data<=state_memory[state_read_address];
 wire same_generation=state_valid[query_slot]&&prior_state[63:32]==query_generation;
 wire signed [17:0] previous_noise=state_valid[query_slot]?prior_state[129:112]:18'd0;
 reg [31:0] ph,inc,gen;reg [15:0] env;
 reg [1:0] current_stage;
 reg [15:0] attack_held,sustain_held;reg [3:0] decay_held,release_held;
 wire [16:0] attack_next={1'b0,env}+{1'b0,attack_held};
 wire [16:0] musical_decay={1'b0,(env>>decay_held)}+17'd1;
 reg [4:0] state;reg [15:0] cycles,count;
 reg [6:0] velocity;reg held,patch;
 reg[6:0]pan_held;wire[3:0]voice_algorithm=same_generation?prior_state[156:153]:query_part;
 reg [3:0] role;reg [31:0] noise;
 reg [3:0] vowel_issue,vowel_receive;reg signed [23:0] vowel_accumulator;
 reg osc_request;reg [31:0] osc_phase;
 wire osc_valid;wire signed [17:0] osc_sample;
 hq_sine_quarter sine(clk,rst||panic,osc_request,osc_phase,osc_valid,osc_sample);
 reg signed [17:0] mod_sample;
 reg signed [34:0] modulation;
 reg signed [19:0] wave_sample;
 reg signed [36:0] envelope_product;
 reg signed [28:0] velocity_product;
 reg signed [37:0] expression_product;
 reg [7:0] expression_held;
 reg [31:0] base_increment;reg [20:0] ratio,harmonics;
 reg [7:0] choir_harmonic;
 always @*case(vowel_issue)
  0:choir_harmonic=1;
  1:choir_harmonic={1'b0,harmonics[6:0]}-1'b1;
  2:choir_harmonic={1'b0,harmonics[6:0]};
  3:choir_harmonic={1'b0,harmonics[6:0]}+1'b1;
  4:choir_harmonic={1'b0,harmonics[13:7]}-1'b1;
  5:choir_harmonic={1'b0,harmonics[13:7]};
  6:choir_harmonic={1'b0,harmonics[13:7]}+1'b1;
  7:choir_harmonic={1'b0,harmonics[20:14]}-1'b1;
  8:choir_harmonic={1'b0,harmonics[20:14]};
  9:choir_harmonic={1'b0,harmonics[20:14]}+1'b1;
  default:choir_harmonic=0;
 endcase
 wire [39:0] choir_frequency=ENABLE_CHOIR?inc*choir_harmonic:40'd0;
 wire signed [23:0] extended_osc={{6{osc_sample[17]}},osc_sample};
 wire signed [23:0] weighted_choir=(vowel_receive==0||vowel_receive==2||vowel_receive==5)?extended_osc<<<2:
  (vowel_receive==7||vowel_receive==9)?extended_osc:extended_osc<<<1;
 wire [52:0] bent_increment=base_increment*ratio;
 wire [38:0] harmonic1_increment=inc*harmonics[6:0];
 wire [38:0] harmonic2_increment=inc*harmonics[13:7];
 wire [38:0] harmonic3_increment=inc*harmonics[20:14];
 reg signed [31:0] total,total_right;
 wire signed [31:0] contribution=expression_product>>>21;
 wire signed[8:0]pan_l_gain=pan_held<=64?9'sd128:pan_held>=127?9'sd0:9'sd128-$signed({1'b0,(pan_held-7'd64),1'b0});
 wire signed[8:0]pan_r_gain=pan_held>=64?9'sd128:$signed({1'b0,pan_held,1'b0});
 wire signed[40:0]pan_l_product=contribution*pan_l_gain,pan_r_product=contribution*pan_r_gain;
 wire signed[31:0]pan_left=pan_l_product>>>7,pan_right=pan_r_product>>>7;
 wire [15:0] decay=(env>>(role==0?9:role==1?8:role==2?7:13))+16'd1;
 wire [16:0] release_step={1'b0,(env>>release_held)}+17'd1;
 reg [15:0] next_envelope;reg [1:0] next_stage;
 wire [31:0] next_phase=role==0?ph+inc+((inc>>6)*(env>>8)):ph+inc;
 always @*begin
  next_envelope=env;next_stage=current_stage;
  if(!held)next_envelope=env<=release_step?16'd0:env-release_step;
  else if(role<3)next_envelope=env<=decay?16'd0:env-decay;
  else if(current_stage==0)begin next_envelope=attack_next>=65535?16'd65535:attack_next[15:0];next_stage=attack_next>=65535?1:0;end
  else if(current_stage==1)begin
   if(env<=sustain_held||env-sustain_held<=musical_decay)begin next_envelope=sustain_held;next_stage=2;end
   else next_envelope=env-musical_decay;
  end else begin
   if(env<sustain_held)next_envelope=sustain_held-env<=256?sustain_held:env+16'd256;
   else if(env>sustain_held)next_envelope=env-sustain_held<=256?sustain_held:env-16'd256;
  end
 end
 wire [33:0] wide_inc={2'b0,inc};
 wire [33:0] secondary_increment=role==10?(wide_inc<<1)+(wide_inc>>1)+(wide_inc>>2):role==11?(wide_inc<<1)+wide_inc+(wide_inc>>1):wide_inc;
 wire [31:0] next_noise=(role==10||role==11)?noise+secondary_increment:{noise[30:0],noise[31]^noise[21]^noise[1]^noise[0]};
 wire [159:0] next_voice_state={3'd0,role,harmonics,next_stage,noise[31:14],next_noise,next_envelope,gen,next_phase};
 wire state_write=state==8||state==20||state==21;
 wire [INDEX_BITS+1:0] state_write_address=state_base+(state==8?0:state==20?1:2);
 wire [63:0] state_write_data=state==8?next_voice_state[63:0]:state==20?next_voice_state[127:64]:{32'd0,next_voice_state[159:128]};
 always @(posedge clk)if(!rst&&!panic&&state_write)state_memory[state_write_address]<=state_write_data;
 integer i;
 always @(posedge clk)begin
  if(rst||panic)begin
   state<=0;query_slot<=0;retire_valid<=0;valid_out<=0;sample_out<=0;sample_right<=0;
   osc_request<=0;deadline_miss<=0;clip_count<=0;last_cycles<=0;active_voices<=0;cycles<=0;total<=0;total_right<=0;
   state_valid<=0;read_issue<=0;read_receive<=0;prior_state<=0;
  end else begin
   retire_valid<=0;valid_out<=0;osc_request<=0;
   if(state!=0)cycles<=cycles+1'b1;
   if(sample_tick&&state!=0)deadline_miss<=deadline_miss+1'b1;
   case(state)
    0:if(sample_tick)begin query_slot<=0;total<=0;total_right<=0;cycles<=0;count<=0;state<=17;end
    17:begin
     if(!query_active)begin state_valid[query_slot]<=0;state<=12;end
     else begin read_issue<=0;read_receive<=0;state<=18;end
    end
    18:begin read_issue<=1;state<=19;end
    19:begin
     if(read_issue<2)read_issue<=read_issue+1'b1;
     case(read_receive)0:prior_state[63:0]<=state_read_data;1:prior_state[127:64]<=state_read_data;2:prior_state[159:128]<=state_read_data[31:0];endcase
     if(read_receive==2)state<=1;else read_receive<=read_receive+1'b1;
    end
    1:begin
     if(!query_active)begin state_valid[query_slot]<=0;state<=12;end
     else begin
      count<=count+1'b1;velocity<=query_velocity;held<=query_gate;patch<=voice_algorithm>=5;gen<=query_generation;role<=voice_algorithm;pan_held<=query_pan;
      base_increment<=voice_algorithm==1?32'd16106127:midi_increment(query_note);ratio<=voice_algorithm<3?21'd1048576:bend_ratio(bend);expression_held<=expression;
      attack_held<=attack_step;sustain_held<=sustain_level;decay_held<=decay_shift;release_held<=release_shift;
      current_stage<=same_generation?prior_state[131:130]:0;
      harmonics<=ENABLE_CHOIR?(same_generation?prior_state[152:132]:vowel_harmonics(query_note,vowel)):21'd0;
      if(!same_generation)begin
       ph<=0;env<=voice_algorithm>=3?16'd0:16'd65535;noise<=(voice_algorithm==10||voice_algorithm==11)?32'd0:(query_generation^32'hdeadbeef)|32'd1;
      end else begin ph<=prior_state[31:0];env<=prior_state[79:64];noise<=prior_state[111:80];end
      state<=14;
     end
    end
    14:begin inc<=bent_increment[51:20];state<=ENABLE_CHOIR&&role==7?15:2;end
    15:begin vowel_issue<=0;vowel_receive<=0;vowel_accumulator<=0;state<=16;end
    16:begin
     // Ten harmonics are issued on consecutive clocks through the existing sine
     // pipeline: fundamental plus three triangular formant clusters. Sum weights
     // are 24, normalized by 32, with every out-of-band harmonic suppressed.
     if(vowel_issue<10)begin osc_phase<=choir_frequency<40'h0080000000 ? ph*choir_harmonic:32'd0;osc_request<=1;vowel_issue<=vowel_issue+1'b1;end
     if(osc_valid)begin
      vowel_accumulator<=vowel_accumulator+weighted_choir;vowel_receive<=vowel_receive+1'b1;
      if(vowel_receive==9)begin wave_sample<=(vowel_accumulator+weighted_choir)>>>5;state<=6;end
     end
    end
    2:begin
     // High notes disable the second harmonic/FM to bound aliasing in this first patch bank.
     osc_phase<=role==10||role==11?noise:role==12?(ph<<1)+ph:inc<32'h20000000 ?(ph<<1):32'd0;osc_request<=1;state<=3;
    end
    3:if(osc_valid)begin
     mod_sample<=((role==10||role==11)?secondary_increment>=32'h80000000:role==12?inc>=32'h2aaaaaaa:inc>=32'h40000000)?18'sd0:osc_sample;
     modulation<=osc_sample*$signed({1'b0,env});state<=4;end
    4:begin osc_phase<=role==14?ph+(modulation>>>4):patch||role<3?ph:ph+(modulation>>>3);osc_request<=1;state<=5;end
    5:if(osc_valid)begin
     // Convex harmonic mix retains headroom even for 32 coherent held notes.
      if(role==1)wave_sample<=($signed(osc_sample)+$signed(noise[31:14])*20'sd3)>>>2;
      else if(role==2)wave_sample<=($signed(noise[31:14])-previous_noise)>>>1;
      else if(role==8)wave_sample<=($signed(osc_sample)*20'sd2+$signed(mod_sample))>>>2;
      else if(role==9)wave_sample<=($signed(osc_sample)*20'sd7+$signed(mod_sample)+($signed(noise[31:14])>>>5))>>>3;
      else if(role==10)wave_sample<=($signed(osc_sample)*20'sd2+$signed(mod_sample))>>>2;
      else if(role==11)wave_sample<=($signed(osc_sample)*20'sd3+$signed(mod_sample))>>>2;
      else if(role==12)wave_sample<=($signed(osc_sample)*20'sd3+$signed(mod_sample))>>>2;
      else if(role==13)wave_sample<=($signed(osc_sample)*20'sd2+$signed(mod_sample))>>>2;
      else if(role==14)wave_sample<=$signed(osc_sample);
      else wave_sample<=patch?(($signed(osc_sample)*20'sd3+$signed(mod_sample))>>>2):$signed(osc_sample);
      state<=6;
    end
    6:begin envelope_product<=wave_sample*$signed({1'b0,env});state<=7;end
    7:begin velocity_product<=(envelope_product>>>16)*$signed({1'b0,velocity});state<=11;end
    11:begin expression_product<=velocity_product*$signed({1'b0,expression_held});state<=8;end
    8:begin
     // Sine is 18-bit; /4 converts to 16-bit, /32 supplies fixed mix headroom.
     total<=total+pan_left;total_right<=total_right+pan_right;
     state_valid[query_slot]<=1;
     if(!held&&env<=release_step)begin retire_valid<=1;retire_slot<=query_slot;retire_generation<=gen;end
     state<=20;
    end
    20:state<=21;
    21:state<=12;
    12:if(query_slot==VOICES-1)state<=13;else begin query_slot<=query_slot+1'b1;state<=17;end
    13:begin
     sample_out<=total>32767?16'sd32767:total< -32768?-16'sd32768:total[15:0];
     sample_right<=total_right>32767?16'sd32767:total_right< -32768?-16'sd32768:total_right[15:0];
     if(total>32767||total< -32768||total_right>32767||total_right< -32768)clip_count<=clip_count+1'b1;
     last_cycles<=cycles;active_voices<=count;valid_out<=1;state<=0;
    end
    default:state<=0;
   endcase
  end
 end
endmodule
