"""Compare actual input frontend vendor netlist with the validated RTL fixture."""
from pathlib import Path
import sys,os,subprocess,hashlib,json,datetime,shutil
r=Path(__file__).resolve().parents[3];b=r/'synth/band';build=Path(sys.argv[1]).resolve()
source=build/'stage_pad_frontend.sv';vg=build/'impl/gwsynthesis/stage_pad.vg'
validated_source=b/'experimental/stage/stage_pad_frontend.sv'
candidate_proof=None
if source.read_bytes()!=validated_source.read_bytes():
 candidate=b/'experimental/stage/candidates'/(sys.argv[2] if len(sys.argv)>2 else 'serial_dirty')
 assert source.read_bytes()==(candidate/'stage_pad_frontend.sv').read_bytes()
 for proof in sorted((b/'evidence/stage_pad_candidate').glob('*/result.json')):
  data=json.loads(proof.read_text())
  if data.get('status')=='passed' and all(hashlib.sha256((candidate/name).read_bytes()).hexdigest()==h for name,h in data['sources'].items()):
   candidate_proof=str(proof)
 assert candidate_proof,'Candidate needs source-matched cycle-exact RTL proof'
prior=b/'evidence/stage_pad';reference=json.loads((prior/'result.json').read_text());assert reference['status']=='passed'
for name,h in reference['sources'].items():assert hashlib.sha256((b/name).read_bytes()).hexdigest()==h,name
out=b/'evidence/stage_pad_netlist'/(hashlib.sha256(vg.read_bytes()).hexdigest()[:12]+'_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir(parents=True)
shutil.copy2(vg,out/'stage_pad.vg')
(out/'reference.sv').write_text(validated_source.read_text().replace('module stage_pad_frontend','module stage_pad_reference',1))
tb=(prior/'tb.v').read_text().replace('stage_pad_frontend #(.CHIPS(2),.PADS(16))','stage_pad_reference')
tb=tb.replace('reg [23:0] samples','reg [119:0] samples').replace('wire [111:0] values','wire [559:0] values')
extra='''
 GSR GSR(.GSRI(1'b1));
 wire nvalid,noff,nexhausted;wire[6:0]ncontact,npressure;
 wire[31:0]nserial,noverruns;wire[559:0]nvalues;
 stage_pad_frontend netlist(clk,rst,panic,sv,ch,samples,cfg,7'd0,base,gain,inv,
  7'd24,7'd12,nvalid,ready,noff,ncontact,npressure,nserial,nvalues,noverruns,nexhausted);
 integer compared=0;
 always @(negedge clk)begin
  #1;
  if(!rst)begin
   compared=compared+1;
   if({nvalid,nvalues,noverruns,nexhausted}!=={valid,values,overruns,exhausted})
    $fatal(1,"vendor pad outputs differ cycle=%0d",compared);
   if(valid&&{noff,ncontact,npressure,nserial}!=={off,contact,pressure,serial})
    $fatal(1,"vendor pad event differs cycle=%0d",compared);
  end
 end
'''
tb=tb.replace(' task frame;',extra+'\n task frame;')
tb=tb.replace('$display("PASS pad frontend:', '$display("PASS vendor-pad equivalence:')
tb=tb.replace(' reg cfg=0,inv=0;', ' reg[6:0]cfg_address=0;integer a,l,c,expected_address;\n reg cfg=0,inv=0;')
tb=tb.replace("cfg,7'd0,base",'cfg,cfg_address,base')
address_check='''
  // Distinct values in all80 addresses exercise actual RAM address/data wiring.
  for(a=0;a<80;a=a+1)begin
   @(negedge clk);cfg=1;cfg_address=a;base=950+(a%64);gain=4096;inv=0;
  end
  @(negedge clk);cfg=0;
  for(c=0;c<8;c=c+1)begin
   @(negedge clk);ch=c;for(l=0;l<10;l=l+1)samples[l*12+:12]=1000+l*3;sv=1;
   @(negedge clk);sv=0;wait(!dut.busy);repeat(3)@(negedge clk);
   for(l=0;l<10;l=l+1)begin
    expected_address=1000+l*3-(950+((l*8+c)%64));
    if(expected_address<0)expected_address=0;
    if(expected_address>127)expected_address=127;
    if(values[(l*8+c)*7+:7]!==expected_address||nvalues[(l*8+c)*7+:7]!==expected_address)
     $fatal(1,"calibration RAM address=%0d",l*8+c);
   end
  end
  // Same-edge configuration write/lookup must read the previous generation.
  @(negedge clk);ch=0;samples=1000;sv=1;
  @(negedge clk);sv=0;cfg=1;cfg_address=0;base=999;gain=4096;inv=0;
  @(negedge clk);cfg=0;wait(!dut.busy);repeat(3)@(negedge clk);
  if(values[6:0]!=50||nvalues[6:0]!=50)$fatal(1,"RAM read/write collision changed generation");
  frame(0,1000,0);
  if(values[6:0]!=1||nvalues[6:0]!=1)$fatal(1,"RAM write missing on next batch");
  $display("PASS all80 calibration RAM addresses and same-edge old-data lookup");
'''
tb=tb.replace('  $display("PASS vendor-pad equivalence:',address_check+'\n  $display("PASS vendor-pad equivalence:')
(out/'tb.v').write_text(tb)
binary=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
vendor=Path('D:/Gowin/Gowin_V1.9.12.03_x64/IDE/simlib/gw5a/prim_sim.v')
record=dict(status='running',build=str(build),reference=reference,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),netlist_sha256=hashlib.sha256(vg.read_bytes()).hexdigest(),vendor_sha256=hashlib.sha256(vendor.read_bytes()).hexdigest(),testbench_sha256=hashlib.sha256((out/'tb.v').read_bytes()).hexdigest(),scope='Default10lane/64pad vendor-netlist outputs versus validated RTL:256numeric cases,all80 calibration RAM addresses,same-edge read/write,events,panic,reset,busy/config coherence;not timing/physical acceptance')
record['candidate_differential_proof']=candidate_proof
record['reference_source_sha256']=hashlib.sha256(validated_source.read_bytes()).hexdigest()
report=out/'result.json';report.write_text(json.dumps(record,indent=2));print(out,flush=True)
try:
 c=subprocess.run([str(binary/'iverilog.exe'),'-g2012','-s','tb_pads','-o',str(out/'test.vvp'),str(out/'tb.v'),str(out/'reference.sv'),str(vg),str(vendor)],env=env,capture_output=True,text=True,timeout=120)
 (out/'compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,'compile failed'
 with (out/'simulation.log').open('w') as log:
  p=subprocess.run([str(binary/'vvp.exe'),'-i',str(out/'test.vvp')],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 record.update(returncode=p.returncode,log=(out/'simulation.log').read_text())
 record['status']='passed' if p.returncode==0 and 'PASS vendor-pad equivalence' in record['log'] else 'failed'
except Exception as error:
 record.update(status='failed',error=str(error));raise
finally:report.write_text(json.dumps(record,indent=2))
print(record['status'],record.get('log',''));raise SystemExit(record['status']!='passed')
