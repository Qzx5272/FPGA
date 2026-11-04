module panel_integrated #(parameter DEBOUNCE=250000,ENC_STABLE=25000,LONG_PRESS=40000000)(
 input clk,rst,input[5:0]enc_a,enc_b,enc_sw_n,input[3:0]keys_high,input joy_sw_n,
 input adc_update,adc_online,input[119:0]adc_mv,
 input observed,input[223:0]observed_packet,
 output reg valid,input ready,output reg[223:0]payload,
 output wire play,stop,panic,sustain,
 output reg[3:0]selected_part,output reg signed[3:0]octave,
 output reg[1:0]page,mic_mode,output reg record_toggle,replay_request,
 output reg song_request,output reg[2:0]song,
 output wire[3:0]fader_picked,output wire[6:0]expression_value,
 output wire[13:0]attack_value,output wire[3:0]release_value,input playing,input song_busy,output reg audition,seat,
 output wire[27:0]fader_values,output reg[6:0]vibrato);
 wire[5:0]up,down,sw,sw_rise,sw_fall;wire[3:0]key,kr,kf;wire jr,jf;
 input_filter #(.N(6),.STABLE(DEBOUNCE)) switches(clk,rst,~enc_sw_n,sw,sw_rise,sw_fall);
 input_filter #(.N(4),.STABLE(DEBOUNCE)) buttons(clk,rst,keys_high,key,kr,kf);
 input_filter #(.STABLE(DEBOUNCE)) joystick(clk,rst,~joy_sw_n,sustain,jr,jf);
 wire lesson=mic_mode==3;
 wire[15:0]score_parts=song<2?16'h0018:song==2?16'h00ff:song==3?16'h5f81:16'h3300;
 wire[3:0]lesson_part=score_parts[selected_part]?selected_part:song<3?4'd4:4'd8;
 reg local_stop;
 wire[5:0]tap,long_hit;
 assign play=kr[0]&&(playing||song_busy);assign stop=kr[1]||local_stop;assign panic=long_hit[0];
 genvar g;generate for(g=0;g<6;g=g+1)begin:enc
  wire[31:0]errors;
  encoder_press #(.HOLD(LONG_PRESS)) press(clk,rst,sw[g],tap[g],long_hit[g]);
  quadrature_encoder #(.STABLE_CYCLES(ENC_STABLE)) q(clk,rst,enc_a[g],enc_b[g],up[g],down[g],errors);
 end endgenerate
 `include "offline_patch_defaults.vh"
 reg[6:0]master,expr[0:15];reg[7:0]tempo;
 reg[13:0]attack[0:15];reg[3:0]release_rate[0:15];
 reg[53:0]dirty;reg[3:0]picked;
 reg[6:0]fader[0:3],previous[0:3];reg[3:0]seen;
 reg x_armed;
 assign fader_values={fader[3],fader[2],fader[1],fader[0]};

 assign fader_picked=picked;assign expression_value=expr[selected_part];
 assign attack_value=attack[selected_part];assign release_value=release_rate[selected_part];
 function[6:0]scaled(input[11:0]mv,input[1:0]ch);
  // Calibrated fixed-point gains for millivolts. Saturate outside the travel.
  // One gain per physical slider, with less than one MIDI unit of roundoff.
  reg[11:0]span;reg[11:0]gain;reg[23:0]scaled_product;
  begin
   span=ch==3?(mv<=85?0:mv-85):mv;
   case(ch)1:gain=1401;3:gain=1537;default:gain=1378;endcase
   scaled_product=span*gain;
   scaled=scaled_product[23:15]>127?127:scaled_product[21:15];
  end
 endfunction
 integer i,j;reg found;reg[5:0]choice;reg[223:0]next_packet;reg[6:0]fv,target;
 always @*begin
  found=0;choice=0;
  for(j=0;j<54;j=j+1)if(!found&&dirty[j])begin found=1;choice=j;end
  next_packet=0;next_packet[7:0]=4;next_packet[23:16]=1;next_packet[27:24]=selected_part;
  next_packet[15:8]=11;
  if(choice==0)begin next_packet[15:8]=10;next_packet[198:192]=master;end
  else if(choice==1)begin next_packet[15:8]=15;next_packet[199:192]=tempo;end
  else if(choice<18)begin next_packet[27:24]=choice-2;next_packet[198:192]=expr[choice-2];end
  else if(choice<34)begin next_packet[27:24]=choice-18;next_packet[59:56]=4;next_packet[205:192]=attack[choice-18];end
  else if(choice<50)begin next_packet[27:24]=choice-34;next_packet[59:56]=7;next_packet[195:192]=release_rate[choice-34];end
  else begin next_packet[15:8]=7;next_packet[198:192]=fader[3];end
 end
 always @(posedge clk)begin
  if(rst)begin
   valid<=0;payload<=0;selected_part<=8;octave<=0;page<=0;mic_mode<=0;master<=64;tempo<=120;
   dirty<=0;picked<=0;seen<=0;audition<=0;seat<=0;x_armed<=0;vibrato<=0;
   local_stop<=0;record_toggle<=0;replay_request<=0;song_request<=0;song<=0;
   for(i=0;i<16;i=i+1)begin expr[i]<=offline_parameter_0(i)>127?127:offline_parameter_0(i);attack[i]<=offline_parameter_4(i);release_rate[i]<=offline_parameter_7(i);end
   for(i=0;i<4;i=i+1)begin fader[i]<=i==3?24:64;previous[i]<=0;end
  end else begin
   local_stop<=0;record_toggle<=0;replay_request<=0;song_request<=0;
   if(valid&&ready)valid<=0;
   if((!valid||ready)&&found)begin payload<=next_packet;valid<=1;dirty[choice]<=0;end
   // Mirror received conductor changes; never generate echo commands.
   if(observed&&observed_packet[23:16]==1)begin
    if(observed_packet[15:8]==23&&observed_packet[63:56]==0&&observed_packet[194:192]<5&&!lesson)begin
      song<=observed_packet[194:192];song_request<=1;
     end
     if(observed_packet[15:8]==10)master<=observed_packet[198:192];
    if(observed_packet[15:8]==15)tempo<=observed_packet[199:192];
    if(observed_packet[15:8]==11)case(observed_packet[59:56])
     0:expr[observed_packet[27:24]]<=observed_packet[198:192];
     4:attack[observed_packet[27:24]]<=observed_packet[205:192];
     7:release_rate[observed_packet[27:24]]<=observed_packet[195:192];
    endcase
   end
   if(up[0]||down[0])begin master<=up[0]?(master==127?127:master+1'b1):(master==0?0:master-1'b1);dirty[0]<=1;end
   if(!lesson&&(up[1]||down[1]))begin tempo<=up[1]?(tempo==240?240:tempo+1'b1):(tempo<=40?40:tempo-1'b1);dirty[1]<=1;end
   if(!lesson&&(up[2]||down[2]))begin expr[selected_part]<=up[2]?(expr[selected_part]==127?127:expr[selected_part]+1'b1):(expr[selected_part]==0?0:expr[selected_part]-1'b1);dirty[2+selected_part]<=1;end
   if(!lesson&&(up[3]||down[3]))selected_part<=up[3]?selected_part+1'b1:selected_part-1'b1;
   if(!lesson&&(up[4]||down[4]))begin attack[selected_part]<=up[4]?(attack[selected_part]>=16319?16383:attack[selected_part]+64):(attack[selected_part]<=65?1:attack[selected_part]-64);dirty[18+selected_part]<=1;end
   if(!lesson&&(up[5]||down[5]))begin release_rate[selected_part]<=up[5]?(release_rate[selected_part]==15?15:release_rate[selected_part]+1'b1):(release_rate[selected_part]==0?0:release_rate[selected_part]-1'b1);dirty[34+selected_part]<=1;end
   if(!lesson&&(kr[2]&&octave>-3))octave<=octave-1'b1;
   if(!lesson&&(kr[3]&&octave<4))octave<=octave+1'b1;
   if((tap[1]||kr[0])&&!song_busy)begin
    if(playing)begin if(tap[1])local_stop<=1;end else song_request<=1;
    audition<=0;
   end
   if(long_hit[1]&&!lesson)begin tempo<=120;dirty[1]<=1;end
   if(tap[2])page<=page+1'b1;
   if(long_hit[2])page<=0;
   if(tap[3]&&!lesson&&!song_busy)begin
    if(audition&&playing)begin local_stop<=1;audition<=0;end
    else begin audition<=1;seat<=0;song_request<=1;end
   end
   if(long_hit[3])begin
    local_stop<=1;audition<=0;seat<=0;picked<=0;seen<=0;vibrato<=0;
    if(lesson)mic_mode<=0;
    else begin
     mic_mode<=3;page<=3;selected_part<=lesson_part;octave<=0;
     tempo<=120;dirty[1]<=1;
     expr[lesson_part]<=110;dirty[2+lesson_part]<=1;
     attack[lesson_part]<=offline_parameter_4(lesson_part);dirty[18+lesson_part]<=1;
     release_rate[lesson_part]<=offline_parameter_7(lesson_part);dirty[34+lesson_part]<=1;
     fader[0]<=64;fader[1]<=64;fader[2]<=64;fader[3]<=24;dirty[53]<=1;
    end
   end
   if(!lesson&&!song_busy&&(tap[4]||tap[5]))begin
    song<=tap[4]?(song==0?4:song-1'b1):(song==4?0:song+1'b1);
    local_stop<=1;audition<=0;seat<=0;page<=3;
   end
   if(long_hit[4]&&!lesson)mic_mode<=mic_mode==2?0:mic_mode+1'b1;
   if(long_hit[5]&&!lesson&&!song_busy)begin
    seat<=!seat;audition<=0;selected_part<=lesson_part;
   end
   if(tap[0]&&!lesson)begin
    if(page==3)replay_request<=1;else record_toggle<=1;
   end
   if(!adc_online||lesson)begin seen<=0;picked<=0;x_armed<=0;vibrato<=0;end
   else if(adc_update)begin
    if(adc_mv[59:48]>=1350&&adc_mv[59:48]<=1950)x_armed<=1;
    else if(x_armed&&(adc_mv[59:48]<850||adc_mv[59:48]>2450))begin
     x_armed<=0;
     if(adc_mv[59:48]<850&&octave>-3)octave<=octave-1'b1;
     if(adc_mv[59:48]>2450&&octave<4)octave<=octave+1'b1;
    end
    vibrato<=adc_mv[71:60]<1850?0:adc_mv[71:60]>=3200?127:(adc_mv[71:60]-1850)/11;
    for(i=0;i<4;i=i+1)begin
     fv=scaled(adc_mv[i*12+:12],i);target=fader[i];
     if(picked[i]||(fv<=target+2&&{1'b0,fv}+2>=target)||
       (seen[i]&&((previous[i]<target&&fv>=target)||(previous[i]>target&&fv<=target))))begin
      picked[i]<=1;
      if(fv!=fader[i])begin fader[i]<=fv;if(i==3)dirty[53]<=1;end
     end
     previous[i]<=fv;seen[i]<=1;
    end
   end
   // Phone controls may only select a built-in song and a part in that song.
   if(observed&&observed_packet[23:16]==3&&observed_packet[15:8]==23&&
      observed_packet[223:192]<5&&observed_packet[63:56]<=4&&!song_busy)begin
    song<=observed_packet[194:192];selected_part<=observed_packet[27:24];page<=3;
    audition<=observed_packet[63:56]==2;seat<=observed_packet[63:56]==4;
    mic_mode<=observed_packet[63:56]==3?3:0;
    if(observed_packet[63:56]==0)local_stop<=1;
    else song_request<=1;
    if(observed_packet[63:56]==3)begin
     octave<=0;vibrato<=0;tempo<=120;dirty[1]<=1;
     picked<=0;seen<=0;fader[0]<=64;fader[1]<=64;fader[2]<=64;fader[3]<=24;dirty[53]<=1;
     expr[observed_packet[27:24]]<=110;dirty[2+observed_packet[27:24]]<=1;
     attack[observed_packet[27:24]]<=offline_parameter_4(observed_packet[27:24]);dirty[18+observed_packet[27:24]]<=1;
     release_rate[observed_packet[27:24]]<=offline_parameter_7(observed_packet[27:24]);dirty[34+observed_packet[27:24]]<=1;
    end
   end
   if(panic)begin audition<=0;seat<=0;mic_mode<=0;valid<=0;dirty<=0;end
  end
 end
endmodule

