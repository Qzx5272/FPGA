"""Remove unrelated HDMI/FFT logic after failed display-reset timing audit."""
from pathlib import Path
import shutil,json,hashlib
old=Path('D:/StarclusterBuilds/pcm5102_song_20261031');b=Path('D:/StarclusterBuilds/pcm5102_song_audio_20261031')
b.mkdir(exist_ok=False)
m=json.loads((old/'candidate.json').read_text())
for n,h in m['sources'].items():
    p=old/n;assert hashlib.sha256(p.read_bytes()).hexdigest()==h,n
    shutil.copy2(p,b/n)
(b/'board_pt8211_controls_top.sv').write_text('''// Audio-only audition: original song engine, standard I2S, no HDMI/FFT.
module board_pt8211_controls_top(
 input wire clk,uart_rx_pin,key_play_n,key_stop_n,key_panic_n,
 output wire uart_tx_pin,HP_BCK,HP_WS,HP_DIN,PA_EN);
 assign PA_EN=1'b0;
 band_stage_pt8211_engine #(.LOCAL_INPUTS(1),.LOCAL_ANALOG(0),.EXTERNAL_AUDIO(0)) engine(
 .clk(clk),.uart_rx_pin(uart_rx_pin),.uart_tx_pin(uart_tx_pin),
 .HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(),
 .adc_dout(10'd0),.adc_cs_n(),.adc_sclk(),.adc_din(),
 .local_play(~key_play_n),.local_stop(~key_stop_n),.local_panic(~key_panic_n),
 .local_root(4'd0),.local_minor(1'b0),.local_held(),.external_sample_tick(1'b0),
 .pcm_left(),.pcm_right(),.pcm_valid(),.reset_out(),.panic_out(),
 .microphone_sample(24'sd0),.singer_mix(7'd0),.dac_dropped(),.dac_underruns(),
 .singer_gate(),.singer_note(),.transport_sample_tick(),.audio_stop(),
 .pedal_raw(4'd0),.pedal_down(),.deferred_returns());
endmodule
''')
p=b/'band_stage_pt8211_engine.sv';s=p.read_text();assert s.count('offline_play<=1;')==1
s=s.replace('offline_play<=1;','offline_play<=0;') # explicit play only
s=s.replace('master<=64;','master<=32;');p.write_text(s)
(b/'build_identity.vh').write_text("`define BAND_BUILD_ID 32'h50353132\n")
p=b/'board.cst';s=p.read_text();p.write_text('\n'.join(l for l in s.splitlines() if 'tmds_' not in l)+'\n')
p=b/'board.sdc';s=p.read_text();p.write_text('\n'.join(l.replace('workstation/band/engine/','engine/') for l in s.splitlines() if l.startswith('create_clock ') or ('HP_BCK' in l) or ('key_' in l))+'\n')
m.update(build_id=0x50353132,status='prepared',scope='Audio-only default 96s V6 song, PCM5102; HDMI/FFT and microphone disabled; starts stopped')
m['sources']={n:hashlib.sha256((b/n).read_bytes()).hexdigest() for n in m['sources']}
(b/'candidate.json').write_text(json.dumps(m,indent=2));print(b)
