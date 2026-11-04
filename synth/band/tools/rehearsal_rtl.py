"""Attach the guided transport to the existing singer and LCD interfaces."""
def edit(path, changes):
    text=path.read_text()
    for old,new in changes:
        assert text.count(old)==1,(path.name,old,text.count(old))
        text=text.replace(old,new)
    path.write_text(text)

def integrate(out):
    rtl=out/"rtl"
    edit(rtl/"band_singer_core.sv", [
      ("output wire [31:0] singer_dropped,singer_stale_off","output wire [31:0] singer_dropped,singer_stale_off,\n input wire guided,input wire[3:0]guide_part,input wire guide_hit,input wire[3:0]hit_pad,input wire[15:0]hit_tag,\n output wire[4:0]guide_cue,output wire[15:0]guide_tag"),
      ("wire score_quiet;", """wire score_quiet,score_valid;
 reg released;
 wire guided_onset=guided&&score_valid&&auto_part==guide_part&&auto_kind==0&&auto_serial[31];
 wire waiting=guided_onset&&!released;
 assign guide_cue={waiting,auto_serial[30:27]};
 assign guide_tag=auto_serial[15:0];
 always @(posedge clk)begin
  if(rst||halt||!guided_onset||auto_ready)released<=0;
  else if(guide_hit&&waiting&&hit_pad==auto_serial[30:27]&&hit_tag==guide_tag)released<=1;
 end
 assign auto_valid=score_valid&&!waiting;"""),
      ("score(clk,rst,panic,sample_tick,play,stop,playing,bar_tick,auto_valid,auto_ready","score(clk,rst,panic,sample_tick&&!waiting,play,stop,playing,bar_tick,score_valid,auto_ready"),
      ("allowed<=(auth_kind==2&&auth_manual)||","allowed<=(guided&&!auth_manual&&auth_part==guide_part)||(auth_kind==2&&auth_manual)||")])
    edit(rtl/"band_stage_pt8211_engine.sv",[
      ("input wire song_request,input wire[2:0]song_selection","output wire[4:0]lesson_cue,input wire song_request,input wire[2:0]song_selection"),
      ("reg mirror_status,config_status;", """wire[15:0]lesson_tag;reg[20:0]previous_lesson;
 wire[20:0]lesson_state=lesson_cue[4]?{lesson_tag,lesson_cue}:21'd0;
 always @(posedge clk)previous_lesson<=lesson_state;
 reg mirror_status,config_status;"""),
      ("wire config_changed=current_config","wire config_changed=previous_lesson!=lesson_state||current_config"),
      ("singer_drop_count,singer_stale_count);","singer_drop_count,singer_stale_count,mic_mode==3,panel_part,accepted&&kind==22&&source==2,packet[35:32],packet[111:96],lesson_cue,lesson_tag);"),
      ("{152'd0,halt_counter","{112'd0,4'd0,playing,song_selection,lesson_tag,3'd0,lesson_cue,8'hb5,halt_counter")])
    edit(rtl/"board_lcd_ui_top.sv",[(".song_selection(song),",".lesson_cue(lesson_cue),.song_selection(song),")])
    edit(rtl/"instrument_ui.v",[("if(c==5)glyph=48+state[86];","if(c==5)glyph=48+state[86];"),
      ("end end else case(state[108:107])","""end else if(state[97]&&(c==30||c==31))glyph=digit({12'd0,state[96:93]}+16'd1,31-c);
   end else case(state[108:107])""")])


    from pathlib import Path
    from shutil import copyfile
    copyfile(Path(__file__).resolve().parents[1]/"experimental/integrated/ui/song_titles.vh",rtl/"song_titles.vh")
    edit(rtl/"instrument_ui.v",[
      ('reg[319:0]panel_label;', '`include "song_titles.vh"\n wire[63:0]current_title=song_title({state[98],state[125:124]});\n reg[319:0]panel_label;'),
      ('if(r==7&&c>=7', "if(r==3&&c>=9&&c<17)glyph=current_title[(16-c)*8+:8];\n  if(r==7&&c>=7"),
      ('rr=10+(k/4)*3','rr=10+(3-k/4)*3'),
      ('if(x1==cc*16', "if(state[97]&&state[110:109]==3&&state[96:93]==k)begin background=24'hf4c451;foreground=24'h201a11;end\n    if(x1==cc*16")])
