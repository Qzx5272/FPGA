"""Create a pin-free integration candidate from the checked native board build.

Never generates CST/programming commands. Native board release stays separate.
"""
from pathlib import Path
import argparse, shutil,sys,json,struct,zlib

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--base',type=Path,default=Path('D:/StarclusterBuilds/workstation_v6_20261027'))
ap.add_argument('--out',type=Path,default=Path('D:/StarclusterBuilds/workstation_v6_expansion'))
args=ap.parse_args();band=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(band/'host'))
from score import load as load_score
out=args.out;rtl=out/'rtl';rtl.mkdir(parents=True,exist_ok=True)
for p in (args.base/'rtl').iterdir():shutil.copy2(p,rtl/p.name)
for p in args.base.glob('*.mem'):shutil.copy2(p,out/p.name)
for p in (band/'experimental/panel_v6').glob('*.v'):shutil.copy2(p,rtl/p.name)
shutil.copy2(band/'experimental/panel_v6/workstation_v6_complete_top.sv',rtl/'workstation_v6_complete_top.sv')
library_names=['confluence_v6.json','four_families_demo.json','scale_chord_practice.json']
words=[];descriptions=[]
for name in library_names:
    song=load_score(band/'assets'/name);base=len(words);data=[]
    for e in song['events']:data.extend((e['kind']|(e['part']<<2)|(e['note']<<6)|(e['velocity']<<13),e['serial'],e['sample']))
    checksum=zlib.crc32(struct.pack('<'+'I'*len(data),*data))
    descriptions.append((base,len(data),song['duration_samples'],checksum));words.extend(data)
(out/'song_library_words.mem').write_text('\n'.join(f'{v:08x}' for v in words)+'\n',encoding='utf-8')
config=f'localparam LIBRARY_WORDS={len(words)},LIBRARY_SONGS={len(descriptions)};\nfunction[127:0]library_description;input[7:0]song;begin case(song)\n'
for i,desc in enumerate(descriptions):config+=f"{i}:library_description={{"+','.join(f"32'd{v}" for v in desc)+"};\n"
config+='default:library_description=0;endcase end endfunction\n'
(rtl/'song_library_config.vh').write_text(config,encoding='utf-8')
(out/'song_library.json').write_text(json.dumps(library_names,indent=2),encoding='utf-8')

def once(s,old,new):
    if s.count(old)!=1:raise ValueError('Source boundary changed: '+old[:100])
    return s.replace(old,new)

p=rtl/'band_stage_pt8211_engine.sv';s=p.read_text(encoding='utf-8')
s=once(s,'module band_stage_pt8211_engine #','module workstation_expansion_engine #')
s=once(s,'input clk,input uart_rx_pin,output uart_tx_pin,', '''input clk,input uart_rx_pin,output uart_tx_pin,
 input wire ble_rx,usb_rx,output wire ble_tx,usb_tx,input wire[7:0]enc_a,enc_b,input wire song_next,
 input wire transport_fault,input wire[31:0]external_drops,external_underruns,
 output wire[11:0]guide_pitch,output wire guide_bar,
 output wire[3:0]panel_part,output wire[111:0]panel_values,''')
s=s.replace('offline_play<=1;', 'offline_play<=0;') # Expansion powers up silent.
s=once(s,'wire panic=host_panic||local_panic_sync;', 'wire panic=host_panic||local_panic_sync||transport_fault;')
s=once(s,'event_receiver receiver(clk,rst,byte_data,byte_valid,packet_valid,packet_ready,packet,host_panic,crc_errors,overflow);', '''wire[7:0]ble_data,usb_data;wire ble_valid,usb_valid,panel_valid,panel_ready,packet_remote;wire[1:0]packet_route;wire[223:0]panel_payload;
 uart_rx #(.DIV(50)) ble_uart(clk,rst,ble_rx,ble_data,ble_valid);
 uart_rx #(.DIV(50)) usb_uart(clk,rst,usb_rx,usb_data,usb_valid);
 assign ble_tx=uart_tx_pin;assign usb_tx=uart_tx_pin;
 wire raw_valid,raw_ready,library_valid,library_ready,library_busy,library_failed,next_song;
 wire[223:0]raw_payload,library_payload;wire[7:0]library_current;
 panel_controls controls(clk,rst||panic,enc_a,enc_b,raw_valid,raw_ready,raw_payload,panel_part,panel_values);
 button_pulse song_selector(clk,rst,song_next,next_song);
 wire library_request=(accepted&&(source==1||source==3)&&kind==20)||next_song;
 wire[7:0]library_selection=next_song?(library_current>=2?8'd0:library_current+1'b1):packet[199:192];
 rom_song_loader library_loader(clk,rst||panic,library_request,library_selection,upload_pending,uploading,upload_errors,
 library_valid,library_ready,library_payload,library_busy,library_failed,library_current);
 reg panel_lock,panel_grant;wire panel_choose=panel_lock?panel_grant:library_valid;
 always @(posedge clk)begin
  if(rst||panic)begin panel_lock<=0;panel_grant<=0;end
  else if(panel_valid)begin
   if(panel_ready)panel_lock<=0;else begin panel_lock<=1;panel_grant<=panel_choose;end
  end
 end
 assign panel_valid=panel_choose?library_valid:raw_valid;
 assign panel_payload=panel_choose?library_payload:raw_payload;
 assign raw_ready=panel_ready&&!panel_choose;assign library_ready=panel_ready&&panel_choose;
 three_uart_events ingress(clk,rst,byte_data,ble_data,usb_data,byte_valid,ble_valid,usb_valid,
  panel_valid,panel_ready,panel_payload,packet_valid,packet_ready,packet,host_panic,crc_errors,overflow,packet_remote,packet_route);''')
start=s.index(' wire raw_valid,raw_ready,library_valid,library_ready,library_busy,library_failed,next_song;')
end=s.index(' three_uart_events ingress',start)
library_logic=s[start:end];s=s[:start]+s[end:]
s=once(s,' wire [31:0] singer_drop_count,singer_stale_count;', ' wire [31:0] singer_drop_count,singer_stale_count;\n'+library_logic)
s=once(s,'singer_note,singer_drop_count,singer_stale_count);','singer_note,singer_drop_count,singer_stale_count,guide_pitch,guide_bar);')
start=s.index(' audio_pt8211_queue dac(');end=s.index(' assign sample_tick=',start)
s=s[:start]+''' assign debug_tick=0;assign HP_BCK=0;assign HP_WS=0;assign HP_DIN=0;
 assign dac_ready=1;assign dac_queued=0;assign dac_dropped=external_drops;assign dac_underruns=external_underruns;
'''+s[end:]
s=s.replace('assign PA_EN=~rst;', 'assign PA_EN=0;')
s=once(s,'assign local_panic_sync=0;assign local_play_pulse=0;assign local_stop_pulse=0;', '''reg[1:0]panel_panic_sync;
 always @(posedge clk)if(rst)panel_panic_sync<=0;else panel_panic_sync<={panel_panic_sync[0],local_panic};
 assign local_panic_sync=panel_panic_sync[1];
 button_pulse panel_play(clk,rst,local_play,local_play_pulse);
 button_pulse panel_stop(clk,rst,local_stop,local_stop_pulse);''')
s=s.replace("32'h8000007c", "32'h80000ffc")
s=once(s,'reg [6:0] wet,master;', 'reg library_status;reg[1:0]effect_mode;reg [6:0] wet,master;')
s=once(s,'if(rst)begin singer_status<=0;', 'if(rst)begin library_status<=0;effect_mode<=0;singer_status<=0;')
s=once(s,'if(accepted)begin upload_status<=kind==13||kind==14;', 'if(accepted)begin library_status<=kind==20||kind==21;upload_status<=kind==13||kind==14;')
s=once(s,'wire [223:0] singer_snapshot=', "wire[223:0]library_snapshot={192'd0,library_current,{6'd0,library_busy,library_failed},8'ha3,8'd4};\n wire [223:0] singer_snapshot=")
s=once(s,'telemetry_snapshot<=identity_status?', 'telemetry_snapshot<=library_status?library_snapshot:identity_status?')
s=once(s,'if(kind==7&&source==1)wet<=packet[198:192];', "if(kind==7&&source==1)begin wet<=packet[198:192];if(packet[63:56]<3)effect_mode<=packet[57:56];end")
s=once(s,'singer_stale_count,guide_pitch,guide_bar);','singer_stale_count,guide_pitch,guide_bar,effect_mode);')
# Only expansion changes the sender: real ready/valid avoids silently dropping captured events.
sender=(rtl/'status_sender.v').read_text(encoding='utf-8')
sender=once(sender,'module status_sender #','module event_status_sender #')
sender=once(sender,'output wire tx','output wire tx,output wire ready')
sender=once(sender,' reg [2:0] state;reg tx_start;', ' reg [2:0] state;assign ready=state==0&&!rst;reg tx_start;')
(rtl/'event_status_sender.v').write_text(sender,encoding='utf-8')
s=once(s,'status_sender telemetry(clk,rst,telemetry_request,telemetry_snapshot,uart_tx_pin);', '''wire event_capture_valid,event_capture_ready,sender_ready;
 wire[223:0]event_capture_data;wire[31:0]capture_overflows;
 wire capture_remote=accepted&&packet_remote&&(kind==0||kind==1||kind==2||kind==7||kind==10||kind==11||kind==15||kind==16);
 wire capture_local=local_mv&&core_manual_ready&&(local_kind==0||local_kind==1);
 wire[223:0]local_capture={32'd0,64'd0,local_serial,local_epoch,8'd0,{1'b0,local_velocity},{1'b0,local_note},local_contact,{4'd0,local_part},local_source,{6'd0,local_kind},8'd4};
 wire capture_x=local_xv&&local_xready;
 wire[223:0]x_capture={18'd0,local_xvalue,64'd0,32'd0,32'd0,{4'd0,local_xparameter},8'd100,8'd60,8'd0,{4'd0,local_xpart},8'd1,8'd11,8'd4};
 reg capture_panic_held;always @(posedge clk)if(rst)capture_panic_held<=0;else capture_panic_held<=panic;
 wire capture_panic=capture_panic_held&&!panic;
 wire[223:0]panic_capture={200'd0,8'd1,8'd127,8'd4};
 wire[2:0]capture_count={2'd0,capture_remote}+{2'd0,capture_local}+{2'd0,capture_x}+{2'd0,capture_panic};
 wire[1:0]capture_collision=capture_count>0?capture_count-1'b1:2'd0;
 event_capture_fifo capture_events(clk,rst,panic,sample_tick,capture_remote||capture_local||capture_x||capture_panic,
 capture_panic?panic_capture:capture_local?local_capture:capture_x?x_capture:packet,event_capture_valid,event_capture_ready,event_capture_data,capture_overflows,capture_collision);
 reg[31:0]reported_overflows;reg capture_turn;reg status_pending;reg[223:0]status_held;
 wire overflow_notice=capture_overflows!=reported_overflows;
 wire send_capture=event_capture_valid&&(!status_pending||capture_turn);
 wire[223:0]overflow_snapshot={capture_overflows,176'd0,8'hdf,8'd4};
 assign event_capture_ready=sender_ready&&!overflow_notice&&send_capture;
 always @(posedge clk)begin
  if(rst)begin reported_overflows<=0;capture_turn<=0;status_pending<=0;status_held<=0;end
  else begin
   if(telemetry_request)begin status_pending<=1;status_held<=telemetry_snapshot;end
   if(sender_ready)begin
   if(!overflow_notice&&!send_capture&&status_pending&&!telemetry_request)status_pending<=0;
   if(overflow_notice)reported_overflows<=capture_overflows;
   if(send_capture||status_pending)capture_turn<=!capture_turn;
   end
  end
 end
 event_status_sender telemetry(clk,rst,overflow_notice||send_capture||status_pending,
 overflow_notice?overflow_snapshot:send_capture?event_capture_data:status_held,uart_tx_pin,sender_ready);''')
(rtl/'workstation_expansion_engine.sv').write_text(s,encoding='utf-8')
# Additional output ports are appended, preserving positional legacy callers.
p=rtl/'band_singer_core.sv';s=p.read_text(encoding='utf-8')
s=once(s,'output wire [31:0] singer_dropped,singer_stale_off','output wire [31:0] singer_dropped,singer_stale_off,output wire[11:0]guide_pitch,output wire guide_bar')
s=once(s,'output wire guide_bar', 'output wire guide_bar,input wire[1:0]effect_mode')
s=once(s,'stereo_delay effect(', 'stereo_space effect(')
s=once(s,'smooth_wet,delay_ready,band_audio_valid', 'smooth_wet,effect_mode,delay_ready,band_audio_valid')
s=once(s,'endmodule', ' guide_leds guide(clk,rst,panic,sample_tick,playing,\n auto_valid&&auto_ready&&allowed&&!auto_parameter&&auto_kind==0,pitched_auto_note,\n guide_pitch,guide_bar,bar_tick);\nendmodule')
p.write_text(s,encoding='utf-8')
# Extension-only per-track instrument/pan. Existing native candidate stays frozen.
s=s.replace('16*59','16*70');p.write_text(s,encoding='utf-8')
p=rtl/'shared_role_controls.v';s=p.read_text(encoding='utf-8')
s=s.replace('16*59','16*70').replace('p*59+:59','p*70+:70')
s=once(s,' reg [2:0] vowel[0:15];',' reg[3:0]instrument[0:15];reg[6:0]pan[0:15],target_pan[0:15];\n reg [2:0] vowel[0:15];')
s=once(s,'={expression[p],bend[p]', '={pan[p],instrument[p],expression[p],bend[p]')
s=once(s,'if(rst)for(i=0;i<16;i=i+1)begin','if(rst)for(i=0;i<16;i=i+1)begin instrument[i]<=i;pan[i]<=64;target_pan[i]<=64;')
s=once(s,'if(sample_tick)for(i=0;i<16;i=i+1)begin', "if(sample_tick)for(i=0;i<16;i=i+1)begin if(pan[i]<target_pan[i])pan[i]<=pan[i]+1'b1;else if(pan[i]>target_pan[i])pan[i]<=pan[i]-1'b1;")
s=once(s,'    7:release_rate[control_part]<=control_value[3:0];', '    7:release_rate[control_part]<=control_value[3:0];\n    8:if(control_value<15)instrument[control_part]<=control_value[3:0];\n    9:if(control_value<128)target_pan[control_part]<=control_value[6:0];')
p.write_text(s,encoding='utf-8')
p=rtl/'central_voice_bank.v';s=p.read_text(encoding='utf-8').replace('16*59','16*70').replace('qpart*59+:59','qpart*70+:70')
s=once(s,' wire [3:0] qpart;', ' wire[3:0]algorithm;wire[6:0]pan;wire [3:0] qpart;')
s=once(s,'assign {expression_query,bend_query', 'assign {pan,algorithm,expression_query,bend_query')
s=once(s,'query,active,gate,qnote,qvelocity,qpart,generation,\n  retire,', 'query,active,gate,qnote,qvelocity,algorithm,generation,\n  retire,')
s=once(s,'release_query,sample_right);','release_query,sample_right,pan);')
p.write_text(s,encoding='utf-8')
p=rtl/'shared_band_renderer.v';s=p.read_text(encoding='utf-8')
s=once(s,'output reg signed [15:0] sample_right', 'output reg signed [15:0] sample_right,input wire[6:0]query_pan')
s=once(s,' reg [3:0] role;', ' reg[6:0]pan_held;wire[3:0]voice_algorithm=same_generation?prior_state[156:153]:query_part;\n reg [3:0] role;')
s=once(s,"{7'd0,harmonics,next_stage", "{3'd0,role,harmonics,next_stage")
s=s.replace('patch<=query_part>=5;gen<=query_generation;role<=query_part;', 'patch<=voice_algorithm>=5;gen<=query_generation;role<=voice_algorithm;pan_held<=query_pan;')
s=s.replace('query_part==1?','voice_algorithm==1?').replace('ratio<=query_part<3?', 'ratio<=voice_algorithm<3?').replace('env<=query_part>=3?', 'env<=voice_algorithm>=3?').replace('(query_part==10||query_part==11)', '(voice_algorithm==10||voice_algorithm==11)')
start=s.index(' wire signed [31:0] pan_left=');end=s.index(' wire [15:0] decay=',start)
s=s[:start]+''' wire signed[8:0]pan_l_gain=pan_held<=64?9'sd128:pan_held>=127?9'sd0:9'sd128-$signed({1'b0,(pan_held-7'd64),1'b0});
 wire signed[8:0]pan_r_gain=pan_held>=64?9'sd128:$signed({1'b0,pan_held,1'b0});
 wire signed[40:0]pan_l_product=contribution*pan_l_gain,pan_r_product=contribution*pan_r_gain;
 wire signed[31:0]pan_left=pan_l_product>>>7,pan_right=pan_r_product>>>7;
'''+s[end:]
p.write_text(s,encoding='utf-8')
(rtl/'workstation_expansion_top.sv').write_text('''// No physical pins assigned. Needs a verified24.576MHz audio clock.
module workstation_expansion_top #(parameter SHARED_MIC_CLOCK=1)(
 input wire clk,audio_clk,pc_rx,ble_rx,usb_rx,output wire pc_tx,ble_tx,usb_tx,
 input wire[7:0]enc_a,enc_b,input wire[3:0]pedal_raw,input wire[9:0]adc_dout,output wire adc_cs_n,adc_sclk,adc_din,
 input wire mic_bck,mic_ws,mic_sd,input wire play_button,stop_button,panic_button,song_next,
 output wire i2s_bck,i2s_ws,i2s_sd,output wire[11:0]guide_pitch,output wire guide_bar,
 output wire[3:0]panel_part,output wire[111:0]panel_values,
 output wire clock_fault,microphone_stale,output wire[31:0]drops,underruns,
 output wire signed[15:0]monitor_left,monitor_right,output wire monitor_valid,monitor_reset,monitor_stop);
 wire rst,panic,tick,pcm_valid,stop_audio;wire signed[15:0]left,right;wire signed[23:0]mic;
 assign monitor_left=left;assign monitor_right=right;assign monitor_valid=pcm_valid;
 assign monitor_reset=rst||panic;assign monitor_stop=stop_audio;
 wire[31:0]clock_losses;
 audio_clock_watchdog watch_clock(clk,audio_clk,rst,clock_fault,clock_losses);
 microphone_capture capture(.core_clk(clk),.rst(rst),.panic(panic),.bck(SHARED_MIC_CLOCK?i2s_bck:mic_bck),.ws(SHARED_MIC_CLOCK?i2s_ws:mic_ws),.sd(mic_sd),
 .sample_tick(tick),.microphone_sample(mic),.input_stale(microphone_stale),.received_frames(),
 .repeated_frames(),.skipped_frames(),.timeouts(),.framing_errors_bck(),.overruns_bck());
 workstation_expansion_engine #(.EXTERNAL_AUDIO(1),.LOCAL_INPUTS(1)) engine(
 .clk(clk),.uart_rx_pin(pc_rx),.uart_tx_pin(pc_tx),.ble_rx(ble_rx),.ble_tx(ble_tx),.usb_rx(usb_rx),.usb_tx(usb_tx),
 .enc_a(enc_a),.enc_b(enc_b),.transport_fault(clock_fault),.external_drops(drops),.external_underruns(underruns),
 .song_next(song_next),
 .guide_pitch(guide_pitch),.guide_bar(guide_bar),.panel_part(panel_part),.panel_values(panel_values),
 .HP_BCK(),.HP_WS(),.HP_DIN(),.PA_EN(),.adc_dout(adc_dout),.adc_cs_n(adc_cs_n),.adc_sclk(adc_sclk),.adc_din(adc_din),
 .local_play(play_button),.local_stop(stop_button),.local_panic(panic_button),.local_root(4'd0),.local_minor(1'b0),
 .local_held(),.external_sample_tick(tick),.pcm_left(left),.pcm_right(right),.pcm_valid(pcm_valid),
 .reset_out(rst),.panic_out(panic),.microphone_sample(mic),.singer_mix(7'd80),.dac_dropped(),.dac_underruns(),
 .singer_gate(),.singer_note(),.transport_sample_tick(),.audio_stop(stop_audio),
 .pedal_raw(pedal_raw),.pedal_down(),.deferred_returns());
 i2s24_queue_bridge dac(.core_clk(clk),.audio_clk(audio_clk),.rst(rst),.panic(panic||stop_audio),
 .frame_valid(pcm_valid),.left_in({left,8'd0}),.right_in({right,8'd0}),.frame_ready(),.sample_tick(tick),
 .bck(i2s_bck),.ws(i2s_ws),.sd(i2s_sd),.dropped_frames(drops),
 .underruns_audio_domain(),.underruns_core_domain(underruns));
endmodule
''',encoding='utf-8')
print(out)
