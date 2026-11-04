"""Explore an exact two-read quarter-sine ROM in an isolated project.

The accepted ROM stores both segment endpoints (34 bits). A true dual-read
17-bit table may use fewer RAM blocks; only the implementation report can prove
that. Every adjacent endpoint is checked before generating the alternative.
"""
from pathlib import Path
import argparse,json,hashlib,shutil,re
root=Path(__file__).resolve().parents[3];band=root/'synth/band'
ap=argparse.ArgumentParser();ap.add_argument('destination',type=Path);ap.add_argument('--primitive',action='store_true');a=ap.parse_args()
target=a.destination.resolve()
if target.exists():raise RuntimeError('Use a fresh isolated destination')
candidate=target/'synth/band';candidate.mkdir(parents=True)
for name in ('rtl','host','tests','tools','assets'):
    shutil.copytree(band/name,candidate/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name in ('build','evidence','release'):(candidate/name).mkdir()
shutil.copytree(root/'synth/constraints',target/'synth/constraints')
legacy=target/'synth/rtl';legacy.mkdir()
for name in ('hq_sine_quarter.v','sine_quarter_init.vh','uart.v','audio_serial.v'):
    shutil.copy2(root/'synth/rtl'/name,legacy/name)
pairs={int(i):int(bits,2) for i,bits in re.findall(r"lut\[(\d+)\]=34'b([01]+);",(legacy/'sine_quarter_init.vh').read_text())}
assert set(pairs)==set(range(1024))
low=[pairs[i]&131071 for i in range(1024)]
assert all(pairs[i]>>17==low[i+1] for i in range(1023)) and pairs[1023]>>17==131071
old=(legacy/'hq_sine_quarter.v').read_text()
(candidate/'tests/hq_sine_reference.v').write_text(old.replace('module hq_sine_quarter','module hq_sine_reference').replace('"sine_quarter_init.vh"','"sine_quarter_reference.vh"'))
shutil.copy2(legacy/'sine_quarter_init.vh',candidate/'tests/sine_quarter_reference.vh')
(legacy/'sine_quarter_init.vh').write_text('\n'.join(f"lut[{i}]=17'd{value};" for i,value in enumerate(low))+'\n')
text=old.replace('reg [33:0] lut[0:1023]','reg [16:0] lut[0:1023]')
text=text.replace('pair0<=lut[address];',"pair0<={(address == 10'd1023) ? 17'd131071 : lut[(address+10'd1)&10'h3ff],lut[address]};")
assert text!=old and 'pair0<=lut[address]' not in text
if a.primitive:
    # DPX9B is a 1024 x 18 true-dual-port RAM. Each INIT_RAM holds 16 words.
    params=[f".INIT_RAM_{j:02X}(288'h{sum(low[j*16+k]<<(18*k) for k in range(16)):072x})" for j in range(64)]
    primitive='''wire [17:0] rom_low,rom_high;
    wire [9:0] next_address=address+10'd1;
    reg last0;
    wire [33:0] pair0={last0 ? 17'd131071 : rom_high[16:0],rom_low[16:0]};
    DPX9B #(.BIT_WIDTH_0(18),.BIT_WIDTH_1(18),.READ_MODE0(0),.READ_MODE1(0),
'''+',\n'.join(params)+''') endpoint_rom(
      .DOA(rom_low),.DOB(rom_high),.DIA(18'd0),.DIB(18'd0),
      .ADA({address,4'b0}),.ADB({next_address,4'b0}),
      .BLKSELA(3'b0),.BLKSELB(3'b0),.WREA(1'b0),.WREB(1'b0),
      .CLKA(clk),.CLKB(clk),.CEA(1'b1),.CEB(1'b1),
      .OCEA(1'b1),.OCEB(1'b1),.RESETA(1'b0),.RESETB(1'b0));
'''
    text=text.replace('reg [16:0] lut[0:1023];initial begin\n        `include "sine_quarter_init.vh"\n    end',primitive)
    text=text.replace('reg [33:0] pair0;','')
    address_line="    wire [9:0] address=phase[30] ? ~phase[29:20] : phase[29:20];\n"
    text=text.replace(address_line,'').replace('    wire [17:0] rom_low,rom_high;',address_line+'    wire [17:0] rom_low,rom_high;')
    text=text.replace("pair0<={(address == 10'd1023) ? 17'd131071 : lut[(address+10'd1)&10'h3ff],lut[address]};","last0 <= (address == 10'd1023);")
(legacy/'hq_sine_quarter.v').write_text('// Experimental dual-read endpoint table; bit-exactness and RAM mapping must be verified.\n'+text)
tb='''`timescale 1ns/1ps
module tb_rom_equivalence;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,valid=0;reg [31:0] phase=0,lfsr=32'h19483725;
 wire av,bv;wire signed [17:0] a,b;integer i,checked=0;
 hq_sine_quarter trial(clk,rst,valid,phase,av,a);
 hq_sine_reference reference(clk,rst,valid,phase,bv,b);
 always @(negedge clk)begin
  if(av!==bv)$fatal(1,"latency mismatch");
  if(av)begin if(a!==b)$fatal(1,"sample mismatch %d %d",a,b);checked=checked+1;end
 end
 initial begin
  repeat(8)@(posedge clk);#1;rst=0;
  for(i=0;i<1048576;i=i+1)begin
   @(posedge clk);#1;lfsr={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
   valid=(i%17)!=0;rst=(i%65536)==32768;
   if(i<16384)case(i%4)
    0:phase=(i/4)<<20;
    1:phase=((i/4)<<20)+32'h000fffff;
    2:phase=((i/4)<<20)+1;
    3:phase=((i/4)<<20)+32'h00080000;
   endcase
   else phase=lfsr;
  end
  @(posedge clk);#1;rst=0;valid=0;repeat(8)@(posedge clk);
  if(checked<900000)$fatal(1,"insufficient samples");
  $display("PASS exact ROM equivalence: checked=%0d, all segment boundaries/quadrants, random fractions, valid bubbles and reset",checked);$finish;
 end
endmodule
'''
(candidate/'tests/tb_rom_equivalence.v').write_text(tb)
if a.primitive:
    p=candidate/'tests/tb_rom_equivalence.v'
    p.write_text(tb.replace('module tb_rom_equivalence;','module tb_rom_equivalence;\n GSR GSR(.GSRI(1\'b1));'))
build=target/'rom_mapping';build.mkdir()
(build/'build.tcl').write_text(f'''cd "{build.as_posix()}"
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module hq_sine_quarter
set_option -verilog_std v2001
set_option -use_cpu_as_gpio 1
add_file "{(legacy/'hq_sine_quarter.v').as_posix()}"
set_option -output_base_name rom_mapping
run all
''')
record=dict(status='unverified experimental source',scope='No waveform formula or interpolation change; compare two-read ROM mapping',
    original_rom_sha256=hashlib.sha256((root/'synth/rtl/hq_sine_quarter.v').read_bytes()).hexdigest(),
    trial_rom_sha256=hashlib.sha256((legacy/'hq_sine_quarter.v').read_bytes()).hexdigest(),
    adjacent_endpoint_identity_verified=True,board_programming_forbidden_for_mapping_top=True)
(target/'EXPERIMENT.json').write_text(json.dumps(record,indent=2));print(target)
