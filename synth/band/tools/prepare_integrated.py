"""Freeze the verified LCD/C3 sources and add the final J23 panel/audio shell.
Preparation only: never opens serial ports or programs hardware.
"""
from pathlib import Path
import hashlib,json,shutil,re,argparse
ROOT=Path(__file__).resolve().parents[3];BAND=ROOT/'synth/band'
ap=argparse.ArgumentParser();ap.add_argument('--out',default='D:/StarclusterBuilds/integrated_20261031_a');ap.add_argument('--route-option',type=int,choices=[0,1,2],default=0);a=ap.parse_args()
base=Path('D:/StarclusterBuilds/lcd_ui_20261031_c');out=Path(a.out)
assert not out.exists(),out
manifest=json.loads((base/'candidate.json').read_text())
for n,h in manifest['sources'].items():
 assert hashlib.sha256((base/n).read_bytes()).hexdigest()==h,n
 if n.startswith('rtl/') or n.endswith('.mem'):
  dest=out/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(base/n,dest)
custom=BAND/'experimental/integrated'
for p in custom.glob('*.sv'):shutil.copy2(p,out/'rtl'/p.name)
for p in (custom/'ui').glob('*.mem'):shutil.copy2(p,out/p.name)
shutil.copy2(custom/'ui/ui_glyphs.vh',out/'rtl/ui_glyphs.vh')
shutil.copy2(BAND/'experimental/panel_v6/quadrature_encoder.v',out/'rtl/quadrature_encoder.v')
shutil.copy2(BAND/'experimental/panel_v6/rom_song_loader.v',out/'rtl/rom_song_loader.v')
from rehearsal_rom import emit
emit(out)

(out/'rtl/build_identity.vh').write_text("`define BAND_BUILD_ID 32'h20261107\n")
def change(text,old,new):
 assert text.count(old)==1,(old[:120],text.count(old));return text.replace(old,new)
p=out/'rtl/band_stage_pt8211_engine.sv';s=p.read_text()
s=change(s,'wire panic=host_panic||local_panic_sync;', '''// One clock (20ns) isolates UART panic decoding from the core ready/fanout tree.
 reg panic=0;
 always @(posedge clk)if(rst)panic<=0;else panic<=host_panic||local_panic_sync;''')
s=change(s,'input wire [9:0] adc_dout,', '''input wire panel_valid,output wire panel_ready,input wire[223:0]panel_payload,
 input wire[3:0]panel_part,input wire signed[3:0]panel_octave,input wire panel_sustain,
 input wire[1:0]mic_mode,input wire mic_sd,
 output wire strip_data,input wire song_request,input wire[2:0]song_selection,output wire song_busy,song_failed,
 input wire record_toggle,replay_request,output reg[3:0]take_state,
 output wire observed,output wire[223:0]observed_packet,
 output wire microphone_ready,output wire signed[23:0]microphone_level,
 input wire [9:0] adc_dout,''')
s=change(s,' dual_uart_events receiver', '''wire library_valid,library_ready,local_ready;wire[223:0]library_payload;
 wire ingress_valid,ingress_ready;wire[223:0]ingress_packet;
 event_packet_buffer packet_stage(clk,rst||panic,ingress_valid,ingress_ready,ingress_packet,packet_valid,packet_ready,packet);
 assign panel_ready=local_ready&&!library_valid;
 assign library_ready=local_ready;
 dual_uart_events receiver''')
s=change(s,"1'b0,,224'd0,packet_valid",'library_valid||panel_valid,local_ready,library_valid?library_payload:panel_payload,packet_valid')
s=change(s,'packet_valid,packet_ready,packet,host_panic,crc_errors,overflow);',
 'ingress_valid,ingress_ready,ingress_packet,host_panic,crc_errors,overflow);')
s=change(s,'wire is_manual=kind<4;', '''wire[7:0]loaded_song;
 rom_song_loader library_loader(clk,rst,song_request,{5'd0,song_selection},
  upload_pending,uploading,upload_errors,library_valid,library_ready,library_payload,song_busy,song_failed,loaded_song);
 wire is_manual=kind<4;''')
s=change(s,'wire accepted=packet_valid&&packet_ready;', '''wire accepted=packet_valid&&packet_ready;
 assign observed=accepted;assign observed_packet=packet;''')
s=change(s,'reg [7:0] tempo;', '''reg[7:0]record_counter,replay_counter;
 always @(posedge clk)begin
  if(rst)begin record_counter<=0;replay_counter<=0;take_state<=0;end
  else begin
   if(record_toggle)record_counter<=record_counter+1'b1;
   if(replay_request)replay_counter<=replay_counter+1'b1;
   if(accepted&&source==2&&kind==21)take_state<=packet[59:56];
  end
 end
 reg config_status;reg[9:0]last_config;
 wire[9:0]current_config={mic_mode,panel_sustain,panel_octave,panel_part[2:0]};
 reg[3:0]last_part;wire config_changed=current_config!=last_config||last_part!=panel_part;
 always @(posedge clk)begin
  if(rst)begin config_status<=0;last_config<=0;last_part<=8;end
  else begin
   if(accepted)config_status<=kind==20;
   if(config_changed)begin config_status<=1;last_config<=current_config;last_part<=panel_part;end
  end
 end
 reg [7:0] tempo;''')
s=change(s,'status_request<=accepted;', 'status_request<=accepted||config_changed;')
s=change(s,'microphone_sample,singer_mix,singer_gate',"microphone_level,mic_mode==2&&microphone_ready?7'd100:7'd0,singer_gate")
start=s.index(' audio_pt8211_queue dac(');end=s.index(' assign sample_tick=',start)
s=s[:start]+''' // Complete-frame 64-BCLK I2S queue and microphone share the core timebase.
 reg signed[15:0]mixed_left,mixed_right;reg mixed_valid;
 wire signed[31:0]monitor_scaled=$signed(microphone_level)*$signed({1'b0,master});
 wire signed[31:0]monitor_sample=(mic_mode==1&&microphone_ready)?(monitor_scaled>>>13):32'sd0;
 wire signed[32:0]sum_left=$signed(left)+$signed(monitor_sample);
 wire signed[32:0]sum_right=$signed(right)+$signed(monitor_sample);
 always @(posedge clk)begin
  if(rst||panic||stop)begin mixed_left<=0;mixed_right<=0;mixed_valid<=0;end
  else begin
   mixed_valid<=audio_valid;
   mixed_left<=sum_left>32767?16'sh7fff:sum_left< -32768?16'sh8000:sum_left[15:0];
   mixed_right<=sum_right>32767?16'sh7fff:sum_right< -32768?16'sh8000:sum_right[15:0];
  end
 end
 rhythm_strip strip(clk,rst,mixed_valid,mixed_left,mixed_right,strip_data);
 wire microphone_valid;
 audio48_duplex dac(.clk(clk),.rst(rst),.halt(panic||stop),.frame_valid(mixed_valid),
  .left(mixed_left),.right(mixed_right),.mic_sd(mic_sd),.bck(HP_BCK),.ws(HP_WS),.sd(HP_DIN),
  .sample_tick(debug_tick),.microphone(microphone_level),.mic_valid(microphone_valid),
  .dropped(dac_dropped),.underruns(dac_underruns),.mic_ready(microphone_ready));
'''+s[end:]
s=change(s,'assign PA_EN=~rst;',"assign PA_EN=1'b0;")
s=change(s,' assign audio_stop=stop;', '''reg[7:0]halt_counter;reg was_panic;
 always @(posedge clk)begin
  if(rst)begin halt_counter<=0;was_panic<=0;end
  else begin was_panic<=panic;if(stop||(panic&&!was_panic))halt_counter<=halt_counter+1'b1;end
 end
 assign audio_stop=stop;''')
s=change(s,"32'h8000107c", "32'h8000307c")
s=change(s,'reg pending_status;', '''wire[223:0]config_snapshot={152'd0,halt_counter,replay_counter,record_counter,6'd0,mic_mode,7'd0,panel_sustain,
  {{4{panel_octave[3]}},panel_octave},4'd0,panel_part,8'ha3,8'd4};
 reg pending_status;''')
s=change(s,'telemetry_snapshot<=identity_status?', 'telemetry_snapshot<=config_status?config_snapshot:identity_status?')
p.write_text(s)
# Return old performance seats while transport is stopped too. Only one pulse
# every 1024 clocks; a continuously-high fake bar would starve ownership commands.
p=out/'rtl/band_singer_core.sv';s=p.read_text()
s=change(s,'track_ownership ownership(clk,rst,halt,bar_tick,', '''reg[9:0]idle_bar;
 always @(posedge clk)if(rst||playing)idle_bar<=0;else idle_bar<=idle_bar+1'b1;
 wire ownership_bar=bar_tick||(!playing&&(&idle_bar));
 track_ownership ownership(clk,rst,halt,ownership_bar,''')
s=change(s,'!command_valid&&!bar_tick;', '!command_valid&&!ownership_bar;')
p.write_text(s)
# Dedicated full-board shell; preserve the proven LCD pipeline and its hierarchy.
p=out/'rtl/board_lcd_ui_top.sv';s=p.read_text()
s=change(s,"assign {lcd_r,lcd_g,lcd_b}=ui_de?{color[23:18],color[15:10],color[7:2]}:18'd0;",
 '''lcd_output_stage lcd_output(pixel,pixel_rst,ui_de,
  {color[23:18],color[15:10],color[7:2]},lcd_en,{lcd_r,lcd_g,lcd_b});''')
s=change(s,'assign lcd_clk=~pixel;assign lcd_en=ui_de;','assign lcd_clk=~pixel;')
s=change(s,'output lcd_clk,', '''input[5:0]enc_a,enc_b,enc_sw_n,input[3:0]panel_key_high,input joy_sw_n,
 input adc_rx,mic_sd,output adc_tx,mic_bck,mic_ws,
 output lcd_clk,''')
s=change(s,'wire rst,panic,audio_stop;', '''wire rst,panic,audio_stop;
 wire panel_valid,panel_ready,panel_play,panel_stop,panel_panic,sustain;
 wire[223:0]panel_payload,observed_packet;wire observed;
 wire[3:0]selected_part;wire signed[3:0]octave;wire[1:0]page,mic_mode;wire[2:0]song;wire[4:0]lesson_cue;
 wire record_toggle,replay_request,song_request;wire[3:0]fader_picked;
 wire song_busy,song_failed;wire[3:0]take_state;
 wire[6:0]expression_value;wire[13:0]attack_value;wire[3:0]release_value;
 wire[7:0]adc_data;wire adc_valid,adc_update,adc_online;wire[119:0]adc_mv;wire[31:0]adc_errors;
 wire microphone_ready;wire signed[23:0]microphone_level;
 assign adc_tx=1'b1;assign mic_bck=HP_BCK;assign mic_ws=HP_WS;
 uart_rx #(.DIV(109)) adc_uart(clk,rst,adc_rx,adc_data,adc_valid);
 adc_voltage_parser adc_parser(clk,rst,adc_data,adc_valid,adc_update,adc_mv,adc_online,adc_errors);
 panel_integrated panel(.clk(clk),.rst(rst),.enc_a(enc_a),.enc_b(enc_b),.enc_sw_n(enc_sw_n),
  .keys_high(panel_key_high),.joy_sw_n(joy_sw_n),.adc_update(adc_update),.adc_online(adc_online),.adc_mv(adc_mv),
  .observed(observed),.observed_packet(observed_packet),.valid(panel_valid),.ready(panel_ready),.payload(panel_payload),
  .play(panel_play),.stop(panel_stop),.panic(panel_panic),.sustain(sustain),.selected_part(selected_part),.octave(octave),
  .page(page),.mic_mode(mic_mode),.record_toggle(record_toggle),.replay_request(replay_request),
  .song_request(song_request),.song(song),.fader_picked(fader_picked),.expression_value(expression_value),
  .attack_value(attack_value),.release_value(release_value));''')
s=change(s,'.adc_dout(10\'d0)', '''.panel_valid(panel_valid),.panel_ready(panel_ready),.panel_payload(panel_payload),
 .panel_part(selected_part),.panel_octave(octave),.panel_sustain(sustain),.mic_mode(mic_mode),.mic_sd(mic_sd),
 .strip_data(strip_data),.song_request(song_request),.song_selection(song),.song_busy(song_busy),.song_failed(song_failed),
 .record_toggle(record_toggle),.replay_request(replay_request),.take_state(take_state),
 .observed(observed),.observed_packet(observed_packet),.microphone_ready(microphone_ready),.microphone_level(microphone_level),
 .adc_dout(10'd0)''')
s=change(s,'.local_play(~key_play_n),.local_stop(~key_stop_n),.local_panic(~key_panic_n)',
 '.local_play(~key_play_n||panel_play),.local_stop(~key_stop_n||panel_stop),.local_panic(~key_panic_n||panel_panic)')
# button_pulse would discard already-debounced one-cycle pulses; stretch locally.
s=s.replace('~key_play_n||panel_play','~key_play_n||panel_play_hold').replace('~key_stop_n||panel_stop','~key_stop_n||panel_stop_hold')
s=change(s,'wire panel_valid,panel_ready,panel_play,panel_stop', '''wire panel_play,panel_stop;
 reg[19:0]play_stretch,stop_stretch;
 always @(posedge clk)begin
  if(rst)begin play_stretch<=0;stop_stretch<=0;end
  else begin
   if(panel_play)play_stretch<=1000000;else if(play_stretch!=0)play_stretch<=play_stretch-1'b1;
   if(panel_stop)stop_stretch<=1000000;else if(stop_stretch!=0)stop_stretch<=stop_stretch-1'b1;
  end
 end
 wire panel_play_hold=play_stretch!=0,panel_stop_hold=stop_stretch!=0;
 wire panel_valid,panel_ready''')
p.write_text(s)
# Pack extra panel state into the unused/undisplayed portion of the existing CDC.
s=change(s,'frame_start,core_state,display_state);', '''frame_start,panel_state,display_state);''')
s=change(s,' ui_snapshot ui_cdc', '''wire[127:0]panel_state={song_failed,song_busy,song[1:0],expression_value,fader_picked,sustain,adc_online,
  mic_mode,page,octave,selected_part,song[2],lesson_cue,3'd0,take_state,microphone_ready,release_value,attack_value,core_state[66:50],selected_part,core_state[45:0]};
 ui_snapshot ui_cdc''')
p.write_text(s)
p=out/'rtl/instrument_ui.v';s=p.read_text()
s=change(s,' integer k,rr,cc;', '''reg[319:0]panel_label;
 wire[3:0]octave_magnitude=state[106]?4'd0-state[106:103]:state[106:103];
 integer k,rr,cc;''')
s=change(s,"  if(r==29)foreground=24'hf2b768;", '''  if(r==29)foreground=24'hf2b768;
  panel_label="                                        ";
  if(r==23)panel_label=" PART 00  OCT +0  SUS 0  ADC 0   PAGE 0   ";
  if(r==25)case(state[108:107])
   0:panel_label=" EXPR 000  ATTACK 00000   RELEASE 00     ";
   1:panel_label=" FADER PICKUP  0 0 0 0                   ";
   2:panel_label=" MIC MODE 0   READY 0   OFF/MON/VOCODER   ";
   3:panel_label=" SONG 0   LOADING 0   ERROR 0             ";
  endcase
  if(r==27)panel_label=" REC 0   REPLAY 0   FULL 0   TAKE 0        ";
  if(r==23||r==25||r==27)begin
   glyph=panel_label[(39-c)*8+:8];background=24'h101f31;foreground=24'h58dcc5;
   if(r==23)begin
    if(c==6||c==7)glyph=digit({12'd0,state[102:99]},7-c);
    if(c==14)glyph=state[106]?45:43;
    if(c==15)glyph=48+octave_magnitude;
    if(c==22)glyph=48+state[112];if(c==29)glyph=48+state[111];if(c==38)glyph=48+state[108:107];
   end else if(r==27)begin
    if(c==5)glyph=48+state[86];if(c==16)glyph=48+state[87];
    if(c==25)glyph=48+state[88];if(c==34)glyph=48+state[89];
   end else case(state[108:107])
    0:begin
     if(c>=6&&c<=8)glyph=digit({9'd0,state[123:117]},8-c);
     if(c>=18&&c<=22)begin
      case(c)18:glyph=48+state[80:67]/10000;19:glyph=48+(state[80:67]/1000)%10;
       20:glyph=48+(state[80:67]/100)%10;21:glyph=48+(state[80:67]/10)%10;22:glyph=48+state[80:67]%10;endcase
     end
     if(c==34||c==35)glyph=digit({12'd0,state[84:81]},35-c);
    end
    1:begin if(c==15)glyph=48+state[113];if(c==17)glyph=48+state[114];if(c==19)glyph=48+state[115];if(c==21)glyph=48+state[116];end
    2:begin if(c==10)glyph=48+state[110:109];if(c==20)glyph=48+state[85];end
    3:begin if(c==6)glyph=49+{state[98],state[125:124]};if(c==18)glyph=48+state[126];if(c==28)glyph=48+state[127];end
   endcase
  end''')
s=re.sub(r'panel_label="([^"]*)"',lambda m:'panel_label="'+m[1][:40].ljust(40)+'"',s)
labels=iter(json.loads((custom/'ui/label_rom.json').read_text()))
s=re.sub(r'panel_label="([^"]*)"',lambda m:"panel_label=320'h"+next(labels) if m[1].strip() else m[0],s)
learn_label=next(labels)
s=s.replace('if(r==23||r==25||r==27)begin', "if(r==27&&state[110:109]==3)panel_label=320'h"+learn_label+";\n  if(r==23||r==25||r==27)begin")
s=s.replace('else if(r==27)begin','else if(r==27)begin if(state[110:109]!=3)begin').replace(' end else case(state[108:107])',' end end else case(state[108:107])')
p.write_text(s)
# Echo the exact bundle accepted at a display frame boundary. The source
# handshake keeps held stable until the two-flop acknowledgement returns.
p=out/'rtl/ui_state.v';s=p.read_text()
s=change(s,'output reg[127:0]display_data);','output reg[127:0]display_data,output reg[127:0]presented,output reg[15:0]frame_number);')
s=change(s,'if(source_rst)begin held<=0;', 'if(source_rst)begin presented<=0;frame_number<=0;held<=0;')
s=change(s,'if(ack2==request)begin held<=source_data;', "if(ack2==request)begin presented<=held;frame_number<=frame_number+1'b1;held<=source_data;")
p.write_text(s)
p=out/'rtl/board_lcd_ui_top.sv';s=p.read_text()
s=change(s,'wire[127:0]core_state,display_state;', 'wire[127:0]core_state,display_state,presented;wire[15:0]frame_number;')
s=change(s,'frame_start,panel_state,display_state);','frame_start,panel_state,display_state,presented,frame_number);')
s=change(s,'.ui_snapshot_data(core_state),','.ui_snapshot_data(core_state),.presented(presented),.frame_number(frame_number),.slider_mv(adc_mv[47:0]),')
p.write_text(s)
p=out/'rtl/band_stage_pt8211_engine.sv';s=p.read_text()
s=change(s,'output wire[127:0]ui_snapshot_data,','output wire[127:0]ui_snapshot_data,input wire[127:0]presented,input wire[15:0]frame_number,input wire[47:0]slider_mv,')
s=change(s,'reg config_status;', 'reg mirror_status,config_status;')
s=change(s,'if(rst)begin config_status<=0;', 'if(rst)begin mirror_status<=0;config_status<=0;')
s=change(s,'if(accepted)config_status<=kind==20;', "if(accepted)begin config_status<=kind==20;mirror_status<=source==1&&kind==20&&packet[63:56]==8'h4d;end")
s=change(s,'telemetry_snapshot<=config_status?', "telemetry_snapshot<=mirror_status?{16'd0,slider_mv,presented,frame_number,8'ha4,8'd4}:config_status?")
p.write_text(s)
# Allow a quiet interval between consecutive UART bytes/frames.
p=out/'rtl/status_sender.v';s=p.read_text()
# The shift register zero-fills after the 34 CRC-framed bytes. Send four trailing idle bytes.
s=change(s,'bytes_left<=34;', 'bytes_left<=38;')
s=change(s,'reg [2:0] state;', 'reg [6:0] idle_clocks;reg [2:0] state;')
s=change(s,'if(rst)begin state<=0;', 'if(rst)begin idle_clocks<=0;state<=0;')
s=change(s,'if(bytes_left==1)state<=0;', "idle_clocks<=UART_DIV;if(bytes_left==1)state<=7;")
s=change(s,"bytes_left<=bytes_left-1'b1;state<=3;", "bytes_left<=bytes_left-1'b1;state<=6;")
s=change(s,'    default:state<=0;', "    6,7:if(idle_clocks==0)state<=state==6?3:0;else idle_clocks<=idle_clocks-1'b1;\n    default:state<=0;")
p.write_text(s)
pins=json.loads((base/'pins.json').read_text());pins.update({'strip_data':'Y20','HP_BCK':'W21','HP_WS':'Y21','HP_DIN':'P21','mic_sd':'U17','mic_bck':'V19','mic_ws':'W19','adc_rx':'U15','adc_tx':'V17','joy_sw_n':'W20'})
for i,(aa,bb) in enumerate([('AB25','AB26'),('T23','R23'),('R25','T25'),('W23','P25'),('U24','V23'),('AC26','U25')]):pins[f'enc_a[{i}]']=aa;pins[f'enc_b[{i}]']=bb
for i,b in enumerate(['P23','P24','AA25','AA24','Y26','Y25']):pins[f'enc_sw_n[{i}]']=b
for i,b in enumerate(['W26','W25','U26','V26']):pins[f'panel_key_high[{i}]']=b
assert len(set(pins.values()))==len(pins)
inputs={'clk','uart_rx_pin','ble_rx','key_play_n','key_stop_n','key_panic_n','mic_sd','adc_rx','joy_sw_n'}|{n for n in pins if n.startswith(('enc_','panel_key_high'))}
port_info={}
for n,b in pins.items():
 pull='DOWN' if n=='mic_sd' or n.startswith('panel_key_high') else 'UP' if n in inputs-{'clk'} else 'NONE'
 port_info[n]={'ball':b,'direction':'in' if n in inputs else 'out','pull':pull,'drive':None if n in inputs else 8 if n.startswith('lcd_') else 4}
(out/'board.cst').write_text('\n'.join(f'IO_LOC "{n}" {x["ball"]};\nIO_PORT "{n}" IO_TYPE=LVCMOS33 PULL_MODE={x["pull"]}'+(';' if x['drive'] is None else f' DRIVE={x["drive"]};') for n,x in port_info.items()))
s=(base/'board.sdc').read_text()
s=s.replace('HP_BCK HP_WS HP_DIN ble_tx','HP_BCK HP_WS HP_DIN ble_tx mic_bck mic_ws uart_tx_pin')
s+='\nset_false_path -from [get_ports {uart_rx_pin}] -to [get_pins {engine/rx/sync_0_s0/D}]\n'
s+='set_false_path -from [get_ports {adc_rx}] -to [get_pins {adc_uart/sync_0_s0/D}]\n'
s+='set_false_path -from [get_ports {mic_sd}] -to [get_pins {engine/dac/mic_meta_s0/D}]\n'
for port,instance,n in [('enc_sw_n','switches',6),('panel_key_high','buttons',4)]:
 for i in range(n):s+=f'set_false_path -from [get_ports {{{port}[{i}]}}] -to [get_pins {{panel/{instance}/meta_{i}_s0/D}}]\n'
s+='set_false_path -from [get_ports {joy_sw_n}] -to [get_pins {panel/joystick/meta_0_s0/D}]\n'
for i in range(6):
 for port,reg in [('enc_a','a_sync'),('enc_b','b_sync')]:s+=f'set_false_path -from [get_ports {{{port}[{i}]}}] -to [get_pins {{panel/enc[{i}].q/{reg}_0_s0/D}}]\n'
(out/'board.sdc').write_text(s)
(out/'pins.json').write_text(json.dumps(port_info,indent=2))
t='''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module board_lcd_ui_top
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
set_option -netlist_hierarchy 1
set_option -cst_warn_to_error 1
set_option -output_base_name integrated
set_option -place_option 1
set_option -replicate_resources 1
set_option -route_option 0
set_option -correct_hold_violation 1
set_option -oreg_in_iob 0
set_option -co-place_io_registers 1
'''
t=t.replace('set_option -route_option 0',f'set_option -route_option {a.route_option}')
for p in sorted((out/'rtl').iterdir()):
 if p.suffix in ('.v','.sv') and not p.name.startswith('tb_'):t+='add_file rtl/'+p.name+'\n'
t+='add_file board.cst\nadd_file board.sdc\nrun syn\nrun pnr\n';(out/'build.tcl').write_text(t)
from rehearsal_rtl import integrate
integrate(out)
top=out/'rtl/board_lcd_ui_top.sv'
top.write_text(change(top.read_text(),'output uart_tx_pin,ble_tx,','output strip_data,uart_tx_pin,ble_tx,'))
from workstation_ui import integrate as integrate_workstation
integrate_workstation(out)
record={'build_id':0x20261107,'parent':str(base),'status':'prepared_not_programmed','source_sha256':{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}}
(out/'manifest.json').write_text(json.dumps(record,indent=2));print(out)
