"""Create an explicit experimental core from the unchanged production baseline."""
from pathlib import Path
import re,hashlib,json
B=Path(__file__).resolve().parents[1];source=B/'rtl/band_core.v'
out=B/'experimental/vocoder/integration';out.mkdir(parents=True,exist_ok=True)
s=source.read_text()
def replace(old,new):
 global s
 if s.count(old)!=1:raise RuntimeError('Baseline anchor changed: '+old[:70])
 s=s.replace(old,new)
replace('module band_core #(parameter BANKS=8)(', 'module band_singer_core #(parameter BANKS=8,parameter COEFF_FILE="coeffs.mem")(')
replace(' output reg [31:0] lead_space_events,kick_follow_events\n', ''' output reg [31:0] lead_space_events,kick_follow_events,
 input wire signed [23:0] microphone_sample,
 input wire [6:0] singer_mix,
 output wire singer_gate,output wire [6:0] singer_note,
 output wire [31:0] singer_dropped,singer_stale_off
''')
# Original scheduling/accounting stays on band completion, not delayed output.
header,body=s.split(' wire halt=',1)
body=re.sub(r'\baudio_valid\b','band_audio_valid',body)
s=header+' wire halt='+body
replace(' wire alloc_ready,release_valid,release_ready;', ''' wire band_audio_valid;
 wire signed [15:0] band_left,band_right;
 wire signed [23:0] singer_left,singer_right;
 wire singer_event_ready,singer_frame_ready;
 wire [31:0] singer_rejected,singer_duplicates,singer_mix_clips,singer_vocoder_clips;
 wire [13:0] singer_master_product;
 reg [6:0] singer_expression,singer_scaled_mix;
 wire [13:0] singer_expression_product=singer_mix*singer_expression;
 wire [6:0] singer_effective_gain=singer_master_product[13:7];
 assign left_out=singer_left[23:8];assign right_out=singer_right[23:8];
 wire alloc_ready,release_valid,release_ready;''')
replace('wire dispatch_ready=dispatch_broadcast?(&bank_ready):bank_ready[dispatch_bank];',
 'wire dispatch_ready=dispatch_broadcast?((&bank_ready)&&singer_event_ready):dispatch_part==15?singer_event_ready:bank_ready[dispatch_bank];')
replace('dispatch_valid&&(dispatch_broadcast?(&bank_ready):(dispatch_bank==b))',
 'dispatch_valid&&(dispatch_broadcast?((&bank_ready)&&singer_event_ready):(dispatch_part!=15&&dispatch_bank==b))')
replace('assign rejected=combined_rejected;assign deadline_miss=combined_deadline+mix_deadline;',
 'assign rejected=combined_rejected+singer_rejected;assign deadline_miss=combined_deadline+mix_deadline+singer_dropped;')
replace('delay_ready,band_audio_valid,left_out,right_out,effect_clips,effect_overruns);',
 'delay_ready,band_audio_valid,band_left,band_right,effect_clips,effect_overruns);')
replace('assign clips=renderer_clips+effect_clips+master_clips;',
 'assign clips=renderer_clips+effect_clips+master_clips+singer_mix_clips+singer_vocoder_clips;')
replace('reg [6:0] smooth_master,smooth_wet;', '''reg [6:0] smooth_master,smooth_wet;
 assign singer_master_product=singer_scaled_mix*smooth_master;
 always @(posedge clk)begin
  if(rst)begin singer_expression<=127;singer_scaled_mix<=0;end
  else begin
   // Existing authenticated host expression parameter, dedicated to part15.
   // Parameter127 preserves the previous gain exactly. Other values use Q7.
   if(accepted_control&&applied_control_part==15&&applied_control_parameter==0)
    singer_expression<=applied_control_value>127?7'd127:applied_control_value[6:0];
   singer_scaled_mix<=singer_expression==127?singer_mix:singer_expression_product[13:7];
  end
 end''')
replace('bank_control_valid<=accepted_control||(auto_parameter&&auto_ready&&allowed);',
 'bank_control_valid<=effective_control_part!=15&&(accepted_control||(auto_parameter&&auto_ready&&allowed));')
replace('dry_valid<=1;mixing<=0;', 'dry_valid<=frame_active;mixing<=0;')
# Fast skipping is disabled until singer release-state observability is exposed.
s=re.sub(r' assign simulation_idle=.*?;', ' assign simulation_idle=1\'b0;',s)
s=s.replace('\nendmodule','''
 singer_role #(.COEFF_FILE(COEFF_FILE)) electronic_singer(
  .clk(clk),.rst(rst),.panic(halt),
  .event_valid(dispatch_valid&&(dispatch_broadcast?(&bank_ready):dispatch_part==15)),.event_ready(singer_event_ready),
  .event_kind(dispatch_kind),.event_source(dispatch_source),.event_contact(dispatch_contact),.event_part(dispatch_part),
  .event_epoch(dispatch_epoch),.event_serial(dispatch_serial),.event_note(dispatch_note),.event_velocity(dispatch_velocity),
  .sample_tick(sample_tick&&delay_ready),.frame_valid(band_audio_valid),.frame_ready(singer_frame_ready),.band_left(band_left),.band_right(band_right),
  .mic_in(microphone_sample),.voice_gain(singer_effective_gain),.left_out(singer_left),.right_out(singer_right),.audio_valid(audio_valid),
  .singer_gate(singer_gate),.singer_note(singer_note),.rejected(singer_rejected),.stale_off(singer_stale_off),
  .duplicates(singer_duplicates),.dropped_frames(singer_dropped),.mix_clips(singer_mix_clips),.vocoder_clips(singer_vocoder_clips));
endmodule''')
target=out/'band_singer_core.sv'
target.write_text('// GENERATED experimental integration; do not substitute for released band_core.\n'+s,encoding='utf-8')
(out/'manifest.json').write_text(json.dumps(dict(scope='Experimental authorized part15 singer routing; delayed audio; not production board acceptance',baseline_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),generated_sha256=hashlib.sha256(target.read_bytes()).hexdigest()),indent=2))
print(target)
