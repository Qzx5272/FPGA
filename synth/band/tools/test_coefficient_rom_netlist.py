"""Compare170 coefficient words through2D and flat ROM, RTL and Gowin netlist."""
from pathlib import Path
import json,subprocess,os,hashlib,shutil,datetime,re
r=Path(__file__).resolve().parents[3];b=r/'synth/band'
target=Path('D:/StarclusterBuilds')/('coefficient_rom_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));target.mkdir()
shutil.copy2(b/'experimental/vocoder/ported/coeffs.mem',target/'coeffs.mem')
rtl='''module coefficient_rom(input clk,input[4:0]row,input[3:0]column,output reg[31:0]matrix_word,flat_word);
 reg[31:0]matrix[16:0][9:0];reg[31:0]flat[0:169];
 initial begin $readmemh("coeffs.mem",matrix);$readmemh("coeffs.mem",flat);end
 always @(posedge clk)begin matrix_word<=matrix[row][column];flat_word<=flat[row*10+column];end
endmodule
'''
(target/'coefficient_rom.sv').write_text(rtl)
(target/'build.tcl').write_text('''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module coefficient_rom
set_option -verilog_std sysv2017
add_file coefficient_rom.sv
set_option -output_base_name coefficient_rom
run syn
''')
tb='''`timescale 1ns/1ps
module tb;
 GSR GSR(.GSRI(1'b1));
 reg clk=0;always #10 clk=~clk;reg[4:0]row=0;reg[3:0]column=0;
 wire[31:0]matrix_word,flat_word;reg[31:0]expected[0:169];integer i,matrix_errors=0,flat_errors=0;
 coefficient_rom dut(.*);
 initial begin
  $readmemh("coeffs.mem",expected);repeat(5)@(negedge clk);
  for(i=0;i<170;i=i+1)begin
   row=i/10;column=i%10;repeat(3)@(negedge clk);
   if(matrix_word!==expected[i])begin matrix_errors=matrix_errors+1;$display("MATRIX_MISMATCH index=%0d got=%h expected=%h",i,matrix_word,expected[i]);end
   if(flat_word!==expected[i])begin flat_errors=flat_errors+1;$display("FLAT_MISMATCH index=%0d got=%h expected=%h",i,flat_word,expected[i]);end
  end
  $display("RESULT matrix_errors=%0d flat_errors=%0d",matrix_errors,flat_errors);$finish;
 end
endmodule
'''
(target/'tb.v').write_text(tb)
out=b/'evidence/coefficient_rom_netlist'/target.name;out.mkdir(parents=True)
record=dict(status='running',build=str(target),scope='170word ROM initialization/indexing through vendor synthesis and primitive simulation;not complete vocoder equivalence')
report=out/'result.json';report.write_text(json.dumps(record,indent=2))
binary=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
vendor=Path('D:/Gowin/Gowin_V1.9.12.03_x64/IDE/simlib/gw5a/prim_sim.v')
try:
 with (out/'synthesis.log').open('w') as f:p=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(target/'build.tcl')],stdout=f,stderr=subprocess.STDOUT,timeout=180)
 assert p.returncode==0,'synthesis failed'
 results={}
 for mode,source in [('rtl',target/'coefficient_rom.sv'),('netlist',target/'impl/gwsynthesis/coefficient_rom.vg')]:
  c=subprocess.run([str(binary/'iverilog.exe'),'-g2012','-s','tb','-o',str(target/(mode+'.vvp')),str(source),str(target/'tb.v'),str(vendor)],env=env,capture_output=True,text=True,timeout=120)
  (out/(mode+'_compile.log')).write_text(c.stdout+c.stderr);assert c.returncode==0,'compile '+mode
  p=subprocess.run([str(binary/'vvp.exe'),str(target/(mode+'.vvp'))],cwd=target,env=env,capture_output=True,text=True,timeout=60)
  (out/(mode+'.log')).write_text(p.stdout+p.stderr)
  counts=re.search(r'RESULT matrix_errors=(\d+) flat_errors=(\d+)',p.stdout)
  results[mode]=dict(returncode=p.returncode,all_words_match='RESULT matrix_errors=0 flat_errors=0' in p.stdout,
   matrix_errors=int(counts[1]) if counts else None,flat_errors=int(counts[2]) if counts else None)
 record.update(status='passed' if all(x['all_words_match'] and x['returncode']==0 for x in results.values()) else 'mismatch',results=results)
except Exception as exc:record.update(status='failed',error=str(exc));raise
finally:
 for name in ('coefficient_rom.sv','tb.v','coeffs.mem','build.tcl'):shutil.copy2(target/name,out/name)
 for p in (target/'impl/gwsynthesis').glob('*.vg'):shutil.copy2(p,out/p.name)
 record['sources']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.suffix in ('.sv','.v','.vg','.mem','.tcl')}
 report.write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2));raise SystemExit(record['status']!='passed')
