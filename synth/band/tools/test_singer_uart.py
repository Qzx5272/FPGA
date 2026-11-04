"""Exercise singer ownership with encoded host events through actual UART RTL."""
from pathlib import Path
import sys,os,subprocess,json,hashlib
import argparse,re
ap=argparse.ArgumentParser();ap.add_argument('--microphone',action='store_true');ap.add_argument('--telemetry',action='store_true');ap.add_argument('--stage',action='store_true');ap.add_argument('--visual',action='store_true');ap.add_argument('--spectrum',action='store_true');ap.add_argument('--buffered',action='store_true');ap.add_argument('--i2s',action='store_true');ap.add_argument('--workstation',action='store_true');a=ap.parse_args()
if a.workstation:a.i2s=True;a.buffered=True
if a.i2s:
 if not a.workstation and (a.visual or a.spectrum or a.buffered):ap.error('Use --workstation for combined I2S/display fixture')
 a.stage=True
if a.buffered:a.spectrum=True
if a.visual and a.spectrum:ap.error('Select snapshot or spectrum fixture separately')
if a.visual or a.spectrum:a.stage=True
if a.stage:a.microphone=True
if a.microphone and a.telemetry:ap.error('Run microphone and telemetry scopes separately')
r=Path(__file__).resolve().parents[3];b=r/'synth/band';s=b/'experimental/vocoder';o=b/'evidence'/('workstation_chain' if a.workstation else 'i2s_stage_chain' if a.i2s else 'buffered_stage_chain' if a.buffered else 'spectrum_stage_chain' if a.spectrum else 'visual_stage_chain' if a.visual else 'stage_top_chain' if a.stage else 'microphone_top_chain' if a.microphone else 'singer_telemetry' if a.telemetry else 'singer_uart');o.mkdir(exist_ok=True)
if a.stage:subprocess.run([sys.executable,str(b/'tools/prepare_stage_integration.py')],check=True)
if a.visual:subprocess.run([sys.executable,str(b/'tools/prepare_visual_stage.py')],check=True)
if a.spectrum:subprocess.run([sys.executable,str(b/'tools/prepare_spectrum_stage.py')],check=True)
if a.buffered:subprocess.run([sys.executable,str(b/'tools/prepare_buffered_stage.py')],check=True)
if a.i2s:subprocess.run([sys.executable,str(b/'tools/prepare_i2s_stage.py')],check=True)
if a.workstation:subprocess.run([sys.executable,str(b/'tools/prepare_workstation.py')],check=True)
sys.path.insert(0,str(b/'host'));from protocol import Event
events=[Event(4,source=2,part=15),Event(0,source=2,part=15,contact=1,epoch=2,serial=1),Event(0,source=2,part=15,contact=1,epoch=2,serial=2),Event(1,source=2,part=15,contact=1,epoch=2,serial=1),Event(1,source=3,part=15,contact=1,epoch=2,serial=2),Event(1,source=2,part=15,contact=1,epoch=2,serial=2),Event(0,source=2,part=15,contact=1,epoch=2,serial=3),Event(127),Event(18)]
tb=(s/'tb_singer_uart.v').read_text()
if a.telemetry:
 events.append(Event(19,source=2,part=15))
 tb=tb.replace('bytes[0:305]','bytes[0:339]')
 tb=tb.replace(' reg[7:0]bytes', ''' wire[7:0]received;wire received_valid;integer reply_file;
 uart_rx #(.DIV(50)) capture(clk,dut.rst,tx,received,received_valid);
 initial reply_file=$fopen("REPLY_PATH","w");
 always @(posedge clk)if(received_valid)$fwrite(reply_file,"%02x\\n",received);
 reg[7:0]bytes''')
 tb=tb.replace('  send_packet(5);','  send_packet(9);\n  send_packet(5);')
 tb=tb.replace('$finish;', '$fclose(reply_file);$finish;')
 tb=tb.replace('REPLY_PATH',(o/'replies.hex').as_posix())
if a.microphone:
 events.append(Event(5))
 start=tb.index(' band_singer_board_engine');end=tb.index(' reg[7:0]bytes',start)
 tb=tb[:start]+''' band_microphone_top #(.COEFF_FILE("COEFFICIENT_PATH"),.MIC_TIMEOUT(4000)) dut(
 .clk(clk),.uart_rx_pin(rx),.uart_tx_pin(tx),.HP_BCK(bck),.HP_WS(ws),.HP_DIN(din),.PA_EN(pa),
 .mic_bck(mic_bck),.mic_ws(mic_ws),.mic_sd(mic_sd),.microphone_stale(mic_stale),
 .mic_received(mic_received),.mic_repeated(),.mic_skipped(),.mic_timeouts());
'''+tb[end:]
 tb=tb.replace('dut.', 'dut.engine.').replace('bytes[0:305]','bytes[0:339]')
 pos=tb.index(' reg[7:0]bytes')
 tb=tb[:pos]+''' reg mic_bck=0,mic_ws=0,mic_sd=0,mic_run=1;
 wire mic_stale;wire[31:0]mic_received;integer before_frames=0,before_input=0,pcm_frames=0;
 assign gate=dut.engine.singer_gate;assign note=dut.engine.singer_note;
 assign drops=dut.engine.dac_dropped;assign under=dut.engine.dac_underruns;
 always #160 if(mic_run)mic_bck=~mic_bck;
 always @(posedge clk)if(dut.engine.audio_valid)pcm_frames=pcm_frames+1;
 task mic_bit(input ch,data);begin @(negedge mic_bck);mic_ws=ch;mic_sd=data;@(posedge mic_bck);#2;end endtask
 task mic_word(input ch,input[23:0]data);integer k;begin
  mic_bit(ch,0);for(k=1;k<32;k=k+1)mic_bit(ch,k<=24?data[24-k]:1'b0);
 end endtask
 initial begin wait(!dut.engine.rst);repeat(5)@(negedge mic_bck);mic_word(1,0);
  forever begin mic_word(0,noise[23:0]);mic_word(1,0);end
 end
'''+tb[pos:]
 # Declarations must precede the instance for Icarus port width inference.
 decl=' reg mic_bck=0,mic_ws=0,mic_sd=0,mic_run=1;\n wire mic_stale;wire[31:0]mic_received;integer before_frames=0,before_input=0,pcm_frames=0;\n'
 tb=tb.replace(decl,'').replace(' band_microphone_top',decl+' band_microphone_top',1)
 tb=tb.replace('  send_packet(5);', '''  send_packet(9);if(!dut.engine.playing)$fatal(1,"Band did not start");
  @(negedge mic_bck);mic_run=0;before_frames=pcm_frames;
  repeat(170*1042)@(negedge clk);
  if(!mic_stale||dut.engine.core.electronic_singer.audio.smooth_gain!=0||!gate)$fatal(1,"Mic-only fade failed");
  if(!dut.engine.playing||pcm_frames-before_frames<165||drops||under||dut.engine.deadline_miss)$fatal(1,"Mic loss interrupted band");
  before_input=mic_received;mic_run=1;repeat(12000)@(negedge clk);
  if(mic_stale||mic_received<=before_input||dut.engine.core.electronic_singer.audio.smooth_gain==0)$fatal(1,"Mic resume failed");
  send_packet(5);''')
 tb=tb.replace('if(gate||dut.engine.dac.queued_frames!=0&&dut.engine.left!=0)', 'if(gate||dut.engine.left!=0||dut.engine.right!=0||dut.engine.playing)')
 tb=tb.replace('PASS singer UART:', 'PASS microphone top I2S/CDC/singer/DAC,clockloss singer-only fade while score/PCM continue,recovery; singer UART:')
if a.stage:
 tb=tb.replace('band_microphone_top #(', 'band_stage_top #(.PEDAL_STABLE_CYCLES(3),')
 tb=tb.replace('.mic_received(mic_received),', '''.adc_dout(adc_dout),.adc_cs_n(adc_cs),.adc_sclk(adc_sclk),.adc_din(adc_din),
 .play_button(1'b0),.stop_button(1'b0),.panic_button(1'b0),.root(4'd0),.minor_mode(1'b0),
 .pedal_raw(pedals),.pedal_down(),.seat_led(seat_led),.deferred_returns(deferred_returns),
 .mic_received(mic_received),''')
 pos=tb.index(' band_stage_top')
 tb=tb[:pos]+''' reg [9:0] adc_dout=0;wire adc_cs,adc_sclk,adc_din;wire [3:0] seat_led;
 reg [3:0] pedals=0;wire [15:0] deferred_returns;reg stage_checked=0;
 reg [11:0] lead_pressure=0,drum_pressure=0;integer edges=0,adc_i,raw;
 reg [31:0] adc_command=0;reg [2:0] selected=0;
 always @(negedge adc_cs)begin edges=0;adc_command=0;adc_dout=0;end
 always @(posedge adc_sclk)if(!adc_cs)begin edges=edges+1;adc_command={adc_command[30:0],adc_din};end
 always @(negedge adc_sclk)if(!adc_cs)begin
  if(edges==18)selected=adc_command[2:0];
  for(adc_i=0;adc_i<10;adc_i=adc_i+1)begin
   raw=selected==0?(adc_i==0?lead_pressure:adc_i==2?drum_pressure:0):0;
   adc_dout[adc_i]=(edges>=20&&edges<32)?((raw>>(31-edges))&1):0;
  end
 end
 initial begin
  wait(!dut.engine.rst);repeat(30000)@(negedge clk);
  pedals=1;lead_pressure=2500;drum_pressure=3500;wait(seat_led[1:0]==3);
  if(dut.engine.core.ownership.owners[6]!=17||dut.engine.core.ownership.owners[0]!=18)$fatal(1,"stage local ownership");
  lead_pressure=0;wait(!seat_led[0]);wait(deferred_returns[6]);
  // Local handshake precedes the core auth/allocator pipeline, bounded here.
  repeat(100)@(negedge clk);
  if(dut.engine.core.banks[6].unit.allocator.gate!=0)$fatal(1,"pedal must not hold audio gate");
  pedals=0;wait(!deferred_returns[6]);repeat(20)@(negedge clk);
  if(!dut.engine.core.ownership.returns[6])$fatal(1,"stage pedal return");
  drum_pressure=0;wait(seat_led==0);stage_checked=1;
 end
'''+tb[pos:]
 tb=tb.replace('$finish;', 'if(!stage_checked)$fatal(1,"stage scenario incomplete");$finish;')
 tb=tb.replace('PASS microphone top', 'PASS ADC two-seat/pedal plus microphone top')
if a.visual:
 tb=tb.replace('band_stage_top #(', 'band_stage_visual_top #(')
 pos=tb.index(' band_stage_visual_top')
 tb=tb[:pos]+''' reg display_clk=0,display_run=1,display_read=0,display_release=0;reg[8:0]display_address=0;
 always #7 if(display_run)display_clk=~display_clk;
 wire display_available,display_valid;wire signed[15:0]display_left,display_right;
 wire[16:0]display_peak_left,display_peak_right;wire[31:0]display_last,display_frame,display_skipped;
 reg[31:0]expected_pcm[0:511];integer expected_count=0,expected_peak_l=0,expected_peak_r=0,vm,vi,visual_before,visual_nonzero=0;
 reg visual_checked=0;
 always @(posedge clk)begin
  if(dut.engine.rst||dut.engine.panic)begin expected_count=0;expected_peak_l=0;expected_peak_r=0;end
  else if(dut.engine.pcm_valid&&expected_count<512)begin
   expected_pcm[expected_count]={dut.engine.pcm_left,dut.engine.pcm_right};expected_count=expected_count+1;
   vm=$signed(dut.engine.pcm_left);if(vm<0)vm=-vm;if(vm>expected_peak_l)expected_peak_l=vm;
   vm=$signed(dut.engine.pcm_right);if(vm<0)vm=-vm;if(vm>expected_peak_r)expected_peak_r=vm;
  end
 end
 initial begin
  wait(display_available);#1;
  if(expected_count!=512||display_last!=511||display_frame!=1||display_peak_left!=expected_peak_l||display_peak_right!=expected_peak_r)$fatal(1,"visual snapshot metadata");
  @(negedge display_clk);display_run=0;visual_before=pcm_frames;
  repeat(40*1042)@(negedge clk);
  if(pcm_frames-visual_before<39||display_skipped<39||drops||under||dut.engine.deadline_miss)$fatal(1,"stopped display clock interrupted audio");
  display_run=1;
  for(vi=0;vi<512;vi=vi+1)begin
   @(negedge display_clk);display_read=1;display_address=vi;@(negedge display_clk);
   if(!display_valid||{display_left,display_right}!==expected_pcm[vi])$fatal(1,"visual PCM mismatch %0d",vi);
   if(display_left||display_right)visual_nonzero=visual_nonzero+1;display_read=0;
  end
  if(!visual_nonzero)$fatal(1,"visual snapshot only silence");
  @(negedge display_clk);display_release=1;@(negedge display_clk);display_release=0;
  if(display_available||display_valid)$fatal(1,"visual release");
  visual_checked=1;
 end
'''+tb[pos:]
 tb=tb.replace('.mic_received(mic_received),', '''.display_clk(display_clk),.display_read(display_read),.display_release(display_release),.display_address(display_address),
 .display_available(display_available),.display_valid(display_valid),.display_left(display_left),.display_right(display_right),
 .display_peak_left(display_peak_left),.display_peak_right(display_peak_right),.display_last_sample(display_last),.display_frame(display_frame),.display_skipped(display_skipped),
 .mic_received(mic_received),''')
 tb=tb.replace('  send_packet(7);','  wait(visual_checked);send_packet(7);')
 tb=tb.replace('  send_packet(8);','  if(display_available||display_valid)$fatal(1,"panic did not clear display");send_packet(8);')
 tb=tb.replace('$finish;','if(!visual_checked)$fatal(1,"visual scenario incomplete");$display("PASS512 actual synthesized stereo PCM samples,exact peaks,display clock stopped40frames with audio continuing,release andpanic invalidate snapshot");$finish;')
if a.spectrum:
 visual=b/'experimental/audio_visual'
 tb=tb.replace('band_stage_top #(', 'band_stage_spectrum_top #(.TWIDDLE_FILE("'+(visual/'fft_twiddle_2048.mem').as_posix()+'"),.WINDOW_FILE("'+(visual/'hann_2048.mem').as_posix()+'"),')
 pos=tb.index(' band_stage_spectrum_top')
 tb=tb[:pos]+''' reg analysis_clk=0,analysis_run=1,spectrum_ready=0;always #13 if(analysis_run)analysis_clk=~analysis_clk;
 wire spectrum_valid;wire[10:0]spectrum_bin;wire signed[15:0]spectrum_real,spectrum_imag;
 wire[31:0]spectrum_frame,spectrum_last,visual_skipped,fft_clips;wire[16:0]peak_left,peak_right;
 integer captured=0,spectrum_checked=0,vi,pcm_file,bin_file;reg signed[15:0]hold_re,hold_im;
 initial begin pcm_file=$fopen("PCM_PATH","w");bin_file=$fopen("BIN_PATH","w");end
 always @(posedge clk)if(!dut.rst&&!dut.panic&&dut.visual_valid&&captured<2048)begin
  $fwrite(pcm_file,"%0d\\n",$signed(dut.visual_left));captured=captured+1;
 end
 initial begin
  wait(spectrum_valid);@(negedge analysis_clk);
  if(captured!=2048||spectrum_frame!=1||spectrum_last!=2047)$fatal(1,"spectrum window identity");
  for(vi=0;vi<2048;vi=vi+1)begin
   while(!spectrum_valid)@(negedge analysis_clk);
   if(spectrum_bin!=vi)$fatal(1,"spectrum bin order");hold_re=spectrum_real;hold_im=spectrum_imag;
   if(vi%31==0)repeat(20)begin
    @(negedge analysis_clk);if(!spectrum_valid||spectrum_bin!=vi||spectrum_real!==hold_re||spectrum_imag!==hold_im)$fatal(1,"spectrum stall");
   end
   $fwrite(bin_file,"%0d %0d %0d\\n",vi,$signed(spectrum_real),$signed(spectrum_imag));
   spectrum_ready=1;@(negedge analysis_clk);spectrum_ready=0;
  end
  if(fft_clips||drops||under||dut.engine.deadline_miss)$fatal(1,"FFT/audio errors");
  $fclose(pcm_file);$fclose(bin_file);spectrum_checked=1;
 end
'''+tb[pos:]
 tb=tb.replace('PCM_PATH',(o/'pcm.txt').as_posix()).replace('BIN_PATH',(o/'bins.txt').as_posix())
 tb=tb.replace('.mic_received(mic_received),', '''.analysis_clk(analysis_clk),.spectrum_ready(spectrum_ready),.spectrum_valid(spectrum_valid),
 .spectrum_bin(spectrum_bin),.spectrum_real(spectrum_real),.spectrum_imag(spectrum_imag),
 .spectrum_frame(spectrum_frame),.spectrum_last_sample(spectrum_last),.visualization_skipped(visual_skipped),.fft_clips(fft_clips),
 .spectrum_peak_left(peak_left),.spectrum_peak_right(peak_right),.mic_received(mic_received),''')
 tb=tb.replace('  send_packet(7);','  wait(spectrum_checked);@(negedge analysis_clk);analysis_run=0;send_packet(7);')
 tb=tb.replace('  send_packet(8);','  if(spectrum_valid)$fatal(1,"panic while analysis clock stopped");analysis_run=1;send_packet(8);')
 tb=tb.replace('$finish;', 'if(!spectrum_checked)$fatal(1,"spectrum incomplete");$display("PASS2048 actual band PCM -> Hann -> FFT,output stalls,zero audio errors");$finish;')
 tb=tb.replace('#30000000;', '#100000000;')
if a.buffered:
 tb=tb.replace('band_stage_spectrum_top #(', 'band_stage_buffered_top #(')
 tb=tb.replace('wire[10:0]spectrum_bin;', 'reg[10:0]spectrum_bin=0;')
 tb=tb.replace(' wire spectrum_valid;', ''' reg display_clk=0,display_run=1,display_release=0;
 always #17 if(display_run)display_clk=~display_clk;
 wire display_available;wire[31:0]rejected_bins;integer frames_before;
 wire spectrum_valid;''')
 start=tb.index(' initial begin\n  wait(spectrum_valid)');end=tb.index(' end\n',tb.index('spectrum_checked=1;',start))+5
 tb=tb[:start]+''' initial begin
  wait(display_available);@(negedge display_clk);
  if(captured!=2048||spectrum_frame!=1||spectrum_last!=2047)$fatal(1,"buffered window identity");
  display_run=0;frames_before=pcm_frames;repeat(40*1042)@(negedge clk);
  if(pcm_frames-frames_before<39||drops||under||dut.engine.deadline_miss)$fatal(1,"stopped display interrupted audio");
  display_run=1;
  for(vi=0;vi<2048;vi=vi+1)begin
   @(negedge display_clk);spectrum_bin=vi;spectrum_ready=1;@(negedge display_clk);
   if(!spectrum_valid||spectrum_frame!=1||spectrum_last!=2047)$fatal(1,"buffered read identity");
   $fwrite(bin_file,"%0d %0d %0d\\n",vi,$signed(spectrum_real),$signed(spectrum_imag));spectrum_ready=0;
  end
  display_release=1;@(negedge display_clk);display_release=0;
  if(display_available||spectrum_valid||rejected_bins||fft_clips||drops||under||dut.engine.deadline_miss)$fatal(1,"buffered release/errors");
  $fclose(pcm_file);$fclose(bin_file);spectrum_checked=1;
 end
'''+tb[end:]
 tb=tb.replace('.spectrum_ready(spectrum_ready),','.display_clk(display_clk),.display_read(spectrum_ready),.display_release(display_release),.display_available(display_available),.rejected_bins(rejected_bins),')
 tb=tb.replace('.spectrum_bin(spectrum_bin),','.display_address(spectrum_bin),')
 tb=tb.replace('analysis_run=0;send_packet(7);','analysis_run=0;@(negedge display_clk);display_run=0;send_packet(7);')
 tb=tb.replace('analysis_run=1;send_packet(8);','if(display_available)$fatal(1,"panic retained frozen frame");analysis_run=1;display_run=1;send_packet(8);')
 tb=tb.replace('PASS2048 actual band PCM -> Hann -> FFT,output stalls,zero audio errors','PASS2048 actual band PCM -> Hann -> FFT -> frozen display,stopped display40frames,release,panic,zero audio errors')
if a.i2s:
 tb=tb.replace('band_stage_top #(', 'band_stage_i2s_top #(')
 if a.workstation:
  tb=tb.replace('band_stage_buffered_top #(', 'band_workstation_top #(').replace('dut.visual_valid','dut.pcm_valid').replace('dut.visual_left','dut.pcm_left')
 tb=tb.replace('.HP_BCK(bck),.HP_WS(ws),.HP_DIN(din),.PA_EN(pa),', '.audio_clk(audio_clk),.i2s_bck(bck),.i2s_ws(ws),.i2s_sd(din),.i2s_dropped(),.i2s_underruns(),')
 pos=tb.index(' band_workstation_top' if a.workstation else ' band_stage_i2s_top')
 tb=tb[:pos]+''' reg audio_clk=0,audio_run=1;always #20.345052 if(audio_run)audio_clk=~audio_clk;
 reg[47:0]expected_frames[0:4095];reg[47:0]expected_wire;reg[23:0]word=0;
 integer written=0,read_index=0,decoded=0,bit_slot=0;reg previous_ws=1,wire_active=0;
 always @(posedge clk)begin
  if(dut.rst||dut.panic||dut.audio_stop)written=0;
  else if(dut.pcm_valid)begin expected_frames[written]={dut.pcm_left,8'd0,dut.pcm_right,8'd0};written=written+1;end
 end
 always @(posedge audio_clk)begin
  if(dut.output_audio.audio_reset[1])begin read_index=0;wire_active=0;previous_ws=1;bit_slot=0;end
  else if(dut.output_audio.pop)begin
   if(read_index>=written)$fatal(1,"I2S played an unproduced frame");
   expected_wire=expected_frames[read_index];read_index=read_index+1;wire_active=1;
  end
 end
 always @(posedge bck)if(!dut.rst&&!dut.panic&&!dut.audio_stop)begin
  if(ws!=previous_ws)begin bit_slot=0;previous_ws=ws;end else bit_slot=bit_slot+1;
  if(bit_slot>=1&&bit_slot<=24)word={word[22:0],din};
  else if(din!==0)$fatal(1,"I2S padding");
  if(bit_slot==24&&wire_active)begin
   if(word!==(ws?expected_wire[23:0]:expected_wire[47:24]))$fatal(1,"I2S fullstage frame mismatch");
   decoded=decoded+1;
  end
 end
'''+tb[pos:]
 tb=tb.replace('$finish;', 'if(decoded<100)$fatal(1,"too few I2S words");$display("PASS queued I2S fullstage actual PCM decoded words=%0d",decoded);$finish;')
 tb=tb.replace('send_packet(7);','''  @(negedge audio_clk);audio_run=0;repeat(51000)@(negedge clk);
  if(!dut.audio_clock_fault||dut.audio_clock_losses!=1||gate||dut.engine.playing||bck||ws||din)$fatal(1,"audio clock loss did not stop band/output");
  audio_run=1;wait(!dut.audio_clock_fault);repeat(8000)@(negedge clk);
  if(gate||dut.engine.playing||drops||under)$fatal(1,"old performance resumed after clock recovery");
  send_packet(9);if(!dut.engine.playing||drops||under)$fatal(1,"explicit restart after clock recovery failed");
  send_packet(7);''')
(o/'fixture.hex').write_text('\n'.join(f'{v:02x}' for e in events for v in e.encode()))
(o/'tb.v').write_text(tb.replace('COEFFICIENT_PATH',(s/'ported/coeffs.mem').as_posix()).replace('FIXTURE_PATH',(o/'fixture.hex').as_posix()))
t=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(t)+os.pathsep+str(t.parent/'lib')+os.pathsep+env['PATH']
files=list((b/'rtl').glob('*.v'))+list((s/'ported').glob('*.sv'))+list((s/'integration').glob('*.sv'))+[s/'ported/singer_note_control.v',s/'integration/audio_pt8211_queue.v']+[r/'synth/rtl'/n for n in ('hq_sine_quarter.v','uart.v','audio_serial.v')]+[o/'tb.v']
hashes={str(f.relative_to(r)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
if a.microphone:
 files+=list((b/'experimental/audio_input').glob('*.v'))
 hashes.update({str(f.relative_to(r)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
if a.stage:
 files+=list((b/'experimental/stage').glob('*.sv'))+[b/'experimental/local_pedal'/n for n in ('local_pedal_performer.v','pedal_command_gate.v')]
 hashes.update({str(f.relative_to(r)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
if a.visual:files += [b/'experimental/audio_visual'/n for n in ('pcm_snapshot.v','band_stage_visual_top.sv')]
if a.spectrum:files += [b/'experimental/audio_visual'/n for n in ('pcm_snapshot.v','pcm_spectrum.v','fft_fixed.v','band_stage_spectrum_top.sv')]
if a.buffered:files += [b/'experimental/audio_visual'/n for n in ('spectrum_snapshot.v','pcm_spectrum_buffered.v','band_stage_buffered_top.sv')]
dependencies=files+list((b/'rtl').glob('*.vh'))+list((s/'ported').glob('*.mem'))+[r/'synth/rtl/sine_quarter_init.vh']
if a.i2s:
 extra=[b/'experimental/audio_input'/n for n in ('band_stage_i2s_engine.sv','band_stage_i2s_top.sv')];files+=extra;dependencies+=extra
if a.workstation:
 extra=[b/'experimental/audio_visual/band_workstation_top.sv'];files+=extra;dependencies+=extra
if a.spectrum:dependencies += [b/'experimental/audio_visual'/n for n in ('fft_twiddle_2048.mem','hann_2048.mem')]
hashes={str(f.relative_to(r)):hashlib.sha256(f.read_bytes()).hexdigest() for f in dependencies}
report=o/'result.json'
if report.exists():
 previous=report.read_bytes();history=o/'history';history.mkdir(exist_ok=True)
 (history/(hashlib.sha256(previous).hexdigest()[:16]+'.json')).write_bytes(previous)
report.write_text(json.dumps(dict(status='running',scope='RTL fixture in progress;not acceptance',sha256=hashes),indent=2))
c=subprocess.run([str(t/'iverilog.exe'),'-g2012','-I',str(b/'rtl'),'-I',str(s/'ported'),'-I',str(r/'synth/rtl'),'-s','tb_singer_uart','-o',str(o/'test.vvp')]+list(map(str,files)),env=env,capture_output=True,text=True)
if c.returncode:
 report.write_text(json.dumps(dict(status='failed_compile',sha256=hashes,log=c.stdout+c.stderr),indent=2));raise RuntimeError(c.stderr)
try:p=subprocess.run([str(t/'vvp.exe'),str(o/'test.vvp')],env=env,capture_output=True,text=True,timeout=300)
except subprocess.TimeoutExpired:
 report.write_text(json.dumps(dict(status='failed_timeout',sha256=hashes,timeout_seconds=300),indent=2));raise
d=dict(status='passed' if not p.returncode else 'failed',scope='UART->singer->DAC RTL, synthetic microphone, not physical validation',sha256=hashes,log=p.stdout+p.stderr)
if any(hashlib.sha256((r/name).read_bytes()).hexdigest()!=h for name,h in hashes.items()):
 d.update(status='failed',log=d['log']+'\nFAIL source changed during test');p.returncode=98
if a.stage:d['scope']='ADC serial model -> two local seats/pedal + UART singer + I2S microphone + queued DAC; simulation only, no fulltop timing/physical claim'
if a.visual:d['scope']='Fullstage plus actual synthesized PCM snapshot:512stereo samples,peak metadata,display clock stall,audio continuity,panic; simulation only,no HDMI/FFT/physical claim'
if a.spectrum:
 d['scope']='Fullstage final PCM -> async snapshot/Hann/2048FFT RTL; no HDMI,integrated PnR or physical claim'
 if not p.returncode:
  import cmath,math
  pcm=[int(x) for x in (o/'pcm.txt').read_text().split()]
  window=[int(x,16) for x in (b/'experimental/audio_visual/hann_2048.mem').read_text().split()]
  rows=[list(map(int,x.split())) for x in (o/'bins.txt').read_text().splitlines()]
  assert len(pcm)==len(rows)==2048 and max(map(abs,pcm))>0
  def fft(x):
   if len(x)==1:return x
   e,u=fft(x[::2]),fft(x[1::2]);h=len(x)//2;t=[cmath.exp(-2j*math.pi*k/len(x))*u[k] for k in range(h)]
   return [e[k]+t[k] for k in range(h)]+[e[k]-t[k] for k in range(h)]
  ref=[x/2048 for x in fft([complex((v*w)//32768) for v,w in zip(pcm,window)])]
  error=max(max(abs(re-ref[k].real),abs(im-ref[k].imag)) for k,re,im in rows)
  d['max_component_error_lsb']=error
  if error>24:d.update(status='failed',log=d['log']+'\nNumerical spectrum mismatch');p.returncode=99
if a.buffered:d['scope']='Fullstage final PCM -> Hann/2048FFT -> frozen display RAM,all bins compared,stopped display/audio continuity; no pixel output,HDMI,PnR or physical claim'
if a.i2s:d['scope']='Fullstage externally paced queued I2S output:actual PCM pin decoding plus UART/ADC/pedal/mic-loss; no PLL,DAC,pins,timing or physical acceptance'
if a.workstation:d['scope']='Combined workstation RTL:local seats/pedal,mic/singer,externally paced I2S pin decode,actual PCM Hann/FFT frozen display,display stalls,audio clock loss/recovery/panic. No whole-song/full-load/PnR/physical acceptance for this combined top.'
if a.telemetry and not p.returncode:
 from protocol import Decoder,singer_status
 decoder=Decoder();replies=decoder.feed(bytes.fromhex((o/'replies.hex').read_text()))
 singers=[singer_status(x) for x in replies if x[1]==162]
 identities=[x for x in replies if x[1]==161]
 assert decoder.bad_crc==0 and len(singers)==1 and singers[0]['gate'] and singers[0]['note']==60
 assert singers[0]['dropped']==singers[0]['dac_dropped']==singers[0]['dac_underruns']==0
 assert identities and int.from_bytes(identities[-1][20:24],'little')&32
 d['decoded_singer']=singers[0];d['crc_errors']=decoder.bad_crc
(o/'result.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(d['status'],d['log']);raise SystemExit(p.returncode)
