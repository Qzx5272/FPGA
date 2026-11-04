"""Integrate the six-switch workstation, audio controls and native LCD scanout."""
from rehearsal_rtl import edit
from score_art import make

def integrate(out):
    r=out/'rtl'
    make(out)
    from score_cues import make as make_cues
    make_cues(out)
    edit(r/'ui_state.v',[('module ui_snapshot(', 'module ui_snapshot #(parameter WIDTH=128)('),
        ('input[127:0]source_data,output reg[127:0]display_data,output reg[127:0]presented','input[WIDTH-1:0]source_data,output reg[WIDTH-1:0]display_data,output reg[WIDTH-1:0]presented'),
        ('reg[127:0]held;','reg[WIDTH-1:0]held;')])
    top=r/'board_lcd_ui_top.sv'
    edit(top,[
      ('wire rst,panic,audio_stop;', '''wire rst,panic,audio_stop,seat,audition;wire[27:0]faders;wire[6:0]vibrato,progress;
 wire[31:0]lookahead;wire[2:0]count_in;wire signed[15:0]sound_l,sound_r;wire sound_valid;
 wire[127:0]bands;wire[383:0]trace_l,trace_r;wire[5:0]level_l,level_r;
 wire[979:0]visual,visual_pixels,visual_presented;
 assign visual={lookahead,bands,trace_l,trace_r,level_l,level_r,faders,seat,audition,progress,count_in};
 score_analysis analysis(clk,rst,sound_valid,sound_l,sound_r,bands,trace_l,trace_r,level_l,level_r);
 wire[127:0]core_state;'''),
      ('wire[127:0]core_state,display_state,presented;', 'wire[127:0]display_state,presented;'),
      ('.release_value(release_value));','.release_value(release_value),.playing(core_state[0]),.song_busy(song_busy),.seat(seat),.audition(audition),.fader_values(faders),.vibrato(vibrato));'),
      ('.pcm_left(),.pcm_right(),.pcm_valid()', '.pcm_left(sound_l),.pcm_right(sound_r),.pcm_valid(sound_valid)'),
      ('.strip_data(strip_data),', '.seat(seat),.audition(audition),.faders(faders),.vibrato(vibrato),.lookahead(lookahead),.progress(progress),.count_in(count_in),.visual_presented(visual_presented),.strip_data(strip_data),'),
      ("x=in_view?h-11'd262", "x=active?h-11'd182"),
      ('ui_snapshot ui_cdc(clk,pixel,rst,pixel_rst,frame_start,panel_state,display_state,presented,frame_number);',
       'ui_snapshot #(.WIDTH(1108)) ui_cdc(clk,pixel,rst,pixel_rst,frame_start,{visual,panel_state},{visual_pixels,display_state},{visual_presented,presented},frame_number);')])
    s=top.read_text();start=s.index(' instrument_ui dashboard');end=s.index(' lcd_output_stage',start)
    s=s[:start]+''' score_display dashboard(pixel,pixel_rst,active,frame_start,x,y,display_state,
  visual_pixels[947:820],visual_pixels[819:436],visual_pixels[435:52],visual_pixels[51:46],visual_pixels[45:40],
  visual_pixels[39:12],visual_pixels[11],visual_pixels[10],visual_pixels[9:3],visual_pixels[2:0],visual_pixels[979:948],ui_rgb,ui_de);
 wire[23:0]color=ui_rgb;
'''+s[end:];top.write_text(s)
    engine=r/'band_stage_pt8211_engine.sv'
    edit(engine,[('output wire strip_data,','input wire seat,audition,input wire[27:0]faders,input wire[6:0]vibrato,output wire[6:0]progress,output reg[2:0]count_in,output wire[31:0]lookahead,input wire[979:0]visual_presented,output wire strip_data,'),
      ('assign pcm_left=left;assign pcm_right=right;assign pcm_valid=audio_valid;', 'assign pcm_left=mixed_left;assign pcm_right=mixed_right;assign pcm_valid=mixed_valid;'),
      ('reg play,stop;', '''reg play,stop;
 reg[15:0]count_ticks;reg[31:0]progress_threshold;reg[6:0]fraction;
 assign progress=fraction;
 cue_reader cues(clk,rst,playing,song_selection,panel_part,song_position,lookahead);
 wire[31:0]progress_stride=(stored_duration+127)>>7;
 always @(posedge clk)begin
  if(rst||!playing)begin fraction<=0;progress_threshold<=progress_stride;end
  else if(fraction!=127&&song_position>=progress_threshold)begin fraction<=fraction+1'b1;progress_threshold<=progress_threshold+progress_stride;end
 end
 wire play_event=(accepted&&source_ok&&kind==5&&packet[63:56]==0)||local_play_pulse||offline_play;
 reg count_done;
 always @(posedge clk)begin
  count_done<=0;
  if(rst||panic||stop||!seat)begin count_in<=0;count_ticks<=0;end
  else if(play_event&&!playing)begin count_in<=4;count_ticks<=0;end
  else if(count_in!=0&&sample_tick)begin
   if(count_ticks>=((tempo>=150)?19199:(tempo<=90)?31999:23999))begin
    count_ticks<=0;count_in<=count_in-1'b1;count_done<=count_in==1;
   end else count_ticks<=count_ticks+1'b1;
  end
 end
'''),
      ('play<=(accepted&&source_ok&&kind==5&&packet[63:56]==0)||local_play_pulse||offline_play;', 'play<=(!seat&&play_event)||count_done;'),
      ('lesson_cue,lesson_tag);','lesson_cue,lesson_tag,seat,audition,faders,vibrato);'),
      ('reg telemetry_request;', '''reg[1119:0]visual_copy;reg[15:0]visual_frame;reg[2:0]visual_chunk;reg chunk_request;
 always @(posedge clk)begin
  if(rst)begin visual_copy<=0;visual_frame<=0;chunk_request<=0;visual_chunk<=0;end
  else if(accepted)begin
   chunk_request<=source==1&&kind==20&&packet[63:59]==5'b01100;
   visual_chunk<=packet[58:56];
   if(source==1&&kind==20&&packet[63:56]==77)begin visual_copy<={140'd0,visual_presented};visual_frame<=frame_number;end
  end
 end
 reg telemetry_request;'''),
      ('telemetry_snapshot<=mirror_status?', "telemetry_snapshot<=chunk_request?{16'd0,visual_copy[visual_chunk*160+:160],visual_frame,5'd0,visual_chunk,8'd0,8'ha5,8'd4}:mirror_status?")])
    core=r/'band_singer_core.sv'
    edit(core,[
      ('output wire[15:0]guide_tag','output wire[15:0]guide_tag,input wire seat,audition,input wire[27:0]faders,input wire[6:0]vibrato'),
      ('allowed<=(guided&&!auth_manual&&auth_part==guide_part)||', '''if(!auth_manual&&playing&&(auth_owner==0||auth_owner==2))allowed<=!auth_exhausted&&!(auth_muted&&auth_kind==0)&&(!audition||auth_part==guide_part)&&(!seat||auth_part!=guide_part||guided);
    else if(auth_manual&&playing&&auth_source==2&&!seat&&!guided&&auth_kind==0)allowed<=0;
    else allowed<=(guided&&!auth_manual&&auth_part==guide_part)||'''),
      ('shared_role_controls role_controls', '''reg[13:0]phase;reg[7:0]effective_bend;
 wire signed[6:0]triangle=phase[13]?31-$signed({1'b0,phase[12:7]}):$signed({1'b0,phase[12:7]})-32;
 wire signed[15:0]vib_offset=triangle*$signed({1'b0,vibrato});
 wire signed[10:0]bend_sum=$signed({1'b0,faders[6:0],1'b0})+(vib_offset>>>8);
 always @(posedge clk)begin
  if(rst)begin phase<=0;effective_bend<=128;end
  else begin if(sample_tick)phase<=phase+2;effective_bend<=bend_sum<0?0:bend_sum>255?255:bend_sum[7:0];end
 end
 shared_role_controls role_controls'''),
      ('bank_control_parameter,bank_control_value,patches);','bank_control_parameter,bank_control_value,patches,guide_part,effective_bend,faders[13:7],faders[20:14]);')])
    edit(r/'central_voice_bank.v',[('input wire [16*59-1:0] patches','input wire [16*59-1:0] patches,input wire[3:0]selected,input wire[7:0]live_bend,input wire[6:0]brightness,pan'),
      ('expression_query,bend_query,vowel_query,\n  attack_query','expression_query,qpart==selected?live_bend:bend_query,vowel_query,\n  attack_query'),
      ('release_query,sample_right);','release_query,sample_right,qpart==selected,brightness,pan);')])
    edit(r/'shared_band_renderer.v',[('output reg signed [15:0] sample_right','output reg signed [15:0] sample_right,input wire selected,input wire[6:0]brightness,pan'),
      ('reg [7:0] expression_held;', '''reg [7:0] expression_held;
 reg live;reg[6:0]light,balance;
 wire signed[7:0]tone_delta=$signed({1'b0,light})-8'sd64;
 wire signed[26:0]harmonic_delta=$signed(mod_sample)*tone_delta;
 wire signed[20:0]tone_wave=wave_sample+(harmonic_delta>>>8);
 wire signed[31:0]balance_l=balance<=64?contribution:($signed(contribution)*$signed({1'b0,7'd127-balance}))>>>6;
 wire signed[31:0]balance_r=balance>=64?contribution:($signed(contribution)*$signed({1'b0,balance}))>>>6;'''),
      ('expression_held<=expression;', 'expression_held<=expression;live<=selected;light<=brightness;balance<=pan;'),
      ('envelope_product<=wave_sample*', 'envelope_product<=((live&&role!=7)?tone_wave:wave_sample)*'),
      ('total<=total+pan_left;total_right<=total_right+pan_right;', 'total<=total+(live?balance_l:pan_left);total_right<=total_right+(live?balance_r:pan_right);')])

    edit(engine,[('reg play,stop;', 'wire playing;wire[31:0]song_position;wire sample_tick;reg play,stop;'),('wire sample_tick,playing,audio_valid;','wire audio_valid;'),('wire [31:0] song_position,status_epoch','wire [31:0] status_epoch'),('reg[15:0]count_ticks','reg[21:0]count_ticks'),('count_ticks>=((tempo>=150)?19199:(tempo<=90)?31999:23999)','count_ticks+tempo>=2880000'),('count_ticks<=0;count_in<=count_in-1', 'count_ticks<=count_ticks+tempo-2880000;count_in<=count_in-1'),("else count_ticks<=count_ticks+1'b1", 'else count_ticks<=count_ticks+tempo')])
    edit(r/'shared_band_renderer.v',[('reg live;', 'wire signed[31:0]contribution;reg live;'),('wire signed [31:0] contribution=expression_product>>>21;', 'assign contribution=expression_product>>>21;')])


    edit(engine,[("wire signed[32:0]sum_left=", """reg[10:0]click_phase;reg[2:0]previous_count;
 always @(posedge clk)begin
  if(rst||panic||stop)begin previous_count<=0;click_phase<=0;end
  else begin previous_count<=count_in;
   if(count_in!=previous_count&&count_in!=0)click_phase<=1;
   else if(sample_tick&&click_phase!=0)click_phase<=click_phase==1151?0:click_phase+1'b1;
  end
 end
 wire signed[15:0]click_gain=$signed({1'b0,master,3'b0});
 wire signed[15:0]click_audio=click_phase==0?0:click_phase[5]?click_gain:-click_gain;
 wire signed[32:0]sum_left="""),
       ("$signed(left)+$signed(monitor_sample);","$signed(left)+$signed(monitor_sample)+$signed(click_audio);"),
       ("$signed(right)+$signed(monitor_sample);","$signed(right)+$signed(monitor_sample)+$signed(click_audio);")])


    edit(engine,[("{112'd0,4'd0,playing,song_selection", "{112'd0,2'd0,seat,audition,playing,song_selection")])

    edit(r/'shared_band_renderer.v',[
       ("wire signed[26:0]harmonic_delta=$signed(mod_sample)*tone_delta;", "reg signed[26:0]harmonic_delta;always @(posedge clk)harmonic_delta<=$signed(mod_sample)*tone_delta;"),
       ("wire signed [31:0] pan_left=", "reg signed[31:0] panned_left,panned_right;\n wire signed [31:0] pan_left="),
       ("total<=total+(live?balance_l:pan_left);total_right<=total_right+(live?balance_r:pan_right);","panned_left<=live?balance_l:pan_left;panned_right<=live?balance_r:pan_right;"),
       ("20:state<=21;", "20:begin total<=total+panned_left;total_right<=total_right+panned_right;state<=21;end")])

    # Only the quieter stereo side needs a multiplier. Post-gain samples have
    # already been scaled into the bank mix; preserve full pan resolution.
    renderer=r/'shared_band_renderer.v'
    text=renderer.read_text()
    a=text.index(' wire signed[31:0]balance_l=')
    b=text.index(';',text.index(' wire signed[31:0]balance_r=',a))+1
    text=text[:a]+""" wire[6:0]side_gain=balance<64?balance:127-balance;
 wire signed[20:0]side_product=$signed(contribution[12:0])*$signed({1'b0,side_gain});
 wire signed[31:0]quiet_side=side_product>>>6;
 wire signed[31:0]balance_l=balance<=64?contribution:quiet_side;
 wire signed[31:0]balance_r=balance>=64?contribution:quiet_side;"""+text[b:]
    renderer.write_text(text)

    # Isolate the UART ready/ownership tree from the panel's indexed patch writes.
    edit(top,[('panel_integrated panel(', """reg observed_q;reg[223:0]observed_data_q;
 always @(posedge clk)begin observed_q<=!rst&&observed;observed_data_q<=observed_packet;end
 panel_integrated panel("""),
      ('.observed(observed),.observed_packet(observed_packet),.valid(panel_valid)', '.observed(observed_q),.observed_packet(observed_data_q),.valid(panel_valid)')])
    # Phase and percussion pitch transient settle long before state 8 writes the voice RAM.
    edit(renderer,[("wire [31:0] next_phase=role==0?ph+inc+((inc>>6)*(env>>8)):ph+inc;", """reg[31:0]phase_sum,drum_delta,next_phase;
 always @(posedge clk)begin
  phase_sum<=ph+inc;drum_delta<=(inc>>6)*(env>>8);
  next_phase<=role==0?phase_sum+drum_delta:phase_sum;
 end""")])
    # The bundled payload is frozen until pixel-clock acknowledgement returns.
    # Keep the setup bound on the crossing and target only hold on that payload.
    sdc=out/'board.sdc'
    sdc.write_text(sdc.read_text()+'\nset_false_path -hold -from [get_pins {ui_cdc/held*_s0/Q}] -to [get_clocks {lcd_pixel}]\n')

    from shutil import copyfile
    from pathlib import Path
    copyfile(Path(__file__).resolve().parents[1]/'experimental/integrated/track_ownership.v',r/'track_ownership.v')
    filt=r/'filterbank.sv'
    text=filt.read_text().replace('WAITING, MODULATOR, ENVELOPE, CARRIER','WAITING, MODULATOR, RECTIFY, ENVELOPE, CARRIER')
    for name,value in [('x_n','y_n[i]'),('x_n1','modulator_past_outputs[i][0]'),('x_n2','modulator_past_outputs[i][1]')]:
        text=text.replace(f'{name}[i] <= abs({value});',f'{name}[i] <= {value};')
    a=text.index('        MODULATOR: begin');b=text.index('        ENVELOPE: begin',a)
    text=text[:a]+text[a:b].replace('filters_valid_in <= 1;', 'filters_valid_in <= 0;').replace('state <= ENVELOPE;', 'state <= RECTIFY;')+"""        RECTIFY: begin
          for(int i=0;i<N_FILTERS;i++)begin
            x_n[i]<=abs(x_n[i]);x_n1[i]<=abs(x_n1[i]);x_n2[i]<=abs(x_n2[i]);
          end
          filters_valid_in<=1;state<=ENVELOPE;
        end
"""+text[b:]
    filt.write_text(text)
    from fold_rectifier import fold_rectifier
    fold_rectifier(filt)
