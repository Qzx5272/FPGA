// Focused hardware bring-up image. Does not replace the workstation Flash.
// S0: 1kHz test tone; S1: INMP441 monitor; S2: mute (default).
module audio_bringup_top #(
 parameter DEBOUNCE_CYCLES=250000, MIC_WARMUP_FRAMES=8192
)(
 input wire clk,key_play_n,key_stop_n,key_panic_n,mic_sd,
 output wire i2s_bck,i2s_ws,i2s_sd,PA_EN,
 output wire mic_bck,mic_ws
);
 wire audio_clk,locked;
 reg [7:0] por=0;
 always @(posedge clk) if(!(&por)) por<=por+1'b1;
 gowin_audio_clock clock_source(clk,&por,audio_clk,locked);
 (* ASYNC_REG="TRUE" *) reg [2:0] release_reset=0;
 always @(posedge audio_clk or negedge locked)
  if(!locked) release_reset<=0;else release_reset<={release_reset[1:0],1'b1};
 wire rst=!release_reset[2];
 assign PA_EN=0;
 // Separate physical output buffers/pins, coherent clocks from one master.
 assign mic_bck=i2s_bck;
 assign mic_ws=i2s_ws;
 // Debounce in the audio domain, avoiding a multi-bit mode CDC.
 (* ASYNC_REG="TRUE" *) reg [2:0] key_meta,key_sync;
 reg [2:0] stable;
 reg [19:0] key_count[0:2];
 reg [1:0] mode;
 integer k;
 always @(posedge audio_clk) begin
  if(rst) begin
   key_meta<=7;key_sync<=7;stable<=7;mode<=0;
   for(k=0;k<3;k=k+1) key_count[k]<=0;
  end else begin
   key_meta<={key_panic_n,key_stop_n,key_play_n};key_sync<=key_meta;
   for(k=0;k<3;k=k+1) begin
    if(key_sync[k]==stable[k]) key_count[k]<=0;
    else if(key_count[k]==DEBOUNCE_CYCLES-1) begin
     key_count[k]<=0;stable[k]<=key_sync[k];
     if(!key_sync[k]) begin
      if(k==0) mode<=1;
      if(k==1) mode<=2;
      if(k==2) mode<=0;
     end
    end else key_count[k]<=key_count[k]+1'b1;
   end
   if(!stable[2]) mode<=0;
  end
 end
 wire frame_tick,rx_valid;
 wire signed [23:0] microphone;
 reg [13:0] warmup;
 reg [5:0] tone_index;
 reg signed [23:0] tone_rom[0:47];
 initial $readmemh("tone_1k.mem",tone_rom);
 reg signed [23:0] mic_sample;
 reg signed [23:0] output_sample;
 // 4x microphone gain, saturating. DAC tone starts at about -30dBFS.
 wire signed [25:0] amplified = $signed(microphone) * 26'sd4;
 wire signed [23:0] limited = amplified>26'sd8388607 ? 24'sh7fffff :
                            amplified< -26'sd8388608 ? 24'sh800000 : amplified[23:0];
 always @(posedge audio_clk) begin
  if(rst) begin warmup<=0;tone_index<=0;mic_sample<=0;output_sample<=0;end
  else begin
   if(rx_valid) mic_sample<=limited;
   if(frame_tick) begin
    if(warmup<MIC_WARMUP_FRAMES) warmup<=warmup+1'b1;
    tone_index<=tone_index==6'd47 ? 6'd0 : tone_index+6'd1;
    case(mode)
     1:output_sample<=tone_rom[tone_index];
     2:output_sample<=warmup>=MIC_WARMUP_FRAMES ? mic_sample : 24'sd0;
     default:output_sample<=0;
    endcase
   end
  end
 end
 i2s_master_duplex link(audio_clk,rst,output_sample,output_sample,mic_sd,
  i2s_bck,i2s_ws,i2s_sd,frame_tick,rx_valid,microphone);
endmodule
