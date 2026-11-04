"""Make a timing repair candidate; preserve failed build and all pin constraints."""
from pathlib import Path
import shutil
band=Path(__file__).resolve().parents[1]
base=Path('D:/StarclusterBuilds/workstation_v6_20261027')
out=Path('D:/StarclusterBuilds/workstation_v6_native_fixed')
assert not out.exists(), 'Preserve existing build'
out.mkdir();shutil.copytree(base/'rtl',out/'rtl')
for p in list(base.glob('*.mem'))+[base/'board.cst',base/'board.sdc']:
    shutil.copy2(p,out/p.name)
def once(s,old,new):
    assert s.count(old)==1, old[:120]
    return s.replace(old,new)
p=out/'rtl/band_stage_pt8211_engine.sv';s=p.read_text()
s=once(s,'parameter LOCAL_INPUTS=0,','parameter LOCAL_INPUTS=0,parameter LOCAL_ANALOG=1,')
s=once(s,'  mcp3208_scanner scanner(', '  if(LOCAL_ANALOG)begin:analog_inputs\n  mcp3208_scanner scanner(')
idle='''
 end else begin:no_analog_inputs
  assign adc_cs_n=1;assign adc_sclk=0;assign adc_din=0;assign local_held=0;
  assign pedal_down=0;assign deferred_returns=0;
  assign local_busy=0;assign local_mv=0;assign local_cv=0;assign local_kind=0;assign local_command=0;
  assign local_source=0;assign local_contact=0;assign local_command_source=0;assign local_part=0;assign local_status_part=0;assign local_command_part=0;
  assign local_epoch=0;assign local_serial=0;assign local_denied=0;assign local_note=0;assign local_velocity=0;
  assign local_xv=0;assign local_xpart=0;assign local_xparameter=0;assign local_xvalue=0;
 end
'''
s=once(s,' end else begin:no_local_inputs',idle+' end else begin:no_local_inputs')
s=once(s,'(LOCAL_INPUTS?32\'d1:', '(LOCAL_INPUTS&&LOCAL_ANALOG?32\'d1:')
p.write_text(s)
p=out/'rtl/band_workstation_pt8211_top.sv';s=p.read_text()
s=once(s,'.EXTERNAL_AUDIO(0),.LOCAL_INPUTS(1),','.EXTERNAL_AUDIO(0),.LOCAL_INPUTS(1),.LOCAL_ANALOG(0),');p.write_text(s)
p=out/'rtl/filterbank.sv';s=p.read_text();s=once(s,'reg [31:0] group_index;', 'reg [1:0] group_index;');p.write_text(s)
p=out/'rtl/band_singer_core.sv';s=p.read_text()
old=' assign rejected=combined_rejected+singer_rejected+allocation_rejected;assign deadline_miss=combined_deadline+mix_deadline+singer_dropped;'
new=''' // Telemetry has two bounded register stages; audio/event paths are unchanged.
 localparam COUNTER_PAIRS=(BANKS+1)/2;
 reg[31:0]r_pair[0:COUNTER_PAIRS-1],d_pair[0:COUNTER_PAIRS-1],c_pair[0:COUNTER_PAIRS-1];
 reg[31:0]r_sum,d_sum,c_sum;reg[31:0]r_comb,d_comb,c_comb;integer ci;
 genvar cp;generate for(cp=0;cp<COUNTER_PAIRS;cp=cp+1)begin:counter_pipeline
  always @(posedge clk)begin
   if(rst)begin r_pair[cp]<=0;d_pair[cp]<=0;c_pair[cp]<=0;end
   else begin
    r_pair[cp]<=bank_rejected[2*cp]+((2*cp+1<BANKS)?bank_rejected[2*cp+1]:32'd0);
    d_pair[cp]<=bank_deadline[2*cp]+((2*cp+1<BANKS)?bank_deadline[2*cp+1]:32'd0);
    c_pair[cp]<=bank_clips[2*cp]+((2*cp+1<BANKS)?bank_clips[2*cp+1]:32'd0);
   end
  end
 end endgenerate
 always @*begin
  r_comb=0;d_comb=0;c_comb=0;
  for(ci=0;ci<COUNTER_PAIRS;ci=ci+1)begin r_comb=r_comb+r_pair[ci];d_comb=d_comb+d_pair[ci];c_comb=c_comb+c_pair[ci];end
 end
 always @(posedge clk)if(rst)begin r_sum<=0;d_sum<=0;c_sum<=0;end else begin r_sum<=r_comb;d_sum<=d_comb;c_sum<=c_comb;end
 assign rejected=r_sum+singer_rejected+allocation_rejected;assign deadline_miss=d_sum+mix_deadline+singer_dropped;'''
s=once(s,old,new);s=once(s,'assign clips=renderer_clips+', 'assign clips=c_sum+');p.write_text(s)
tcl=(base/'build.tcl').read_text()
tcl=once(tcl,'run all','set_option -route_option 1\nset_option -correct_hold_violation 1\nrun all')
(out/'build.tcl').write_text(tcl)
snapshot=band/'experimental/workstation_v6_native';snapshot.mkdir(exist_ok=True)
for name in ('band_stage_pt8211_engine.sv','band_workstation_pt8211_top.sv','band_singer_core.sv','filterbank.sv'):
    shutil.copy2(out/'rtl'/name,snapshot/name)
print(out)
