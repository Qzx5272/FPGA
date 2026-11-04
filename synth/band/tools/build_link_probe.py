"""Build a silent minimal UART counterexample from the frozen old serializer."""
from pathlib import Path
import json,hashlib,shutil,subprocess,re,datetime,sys
from verify_fs import verify_fs
band=Path(__file__).resolve().parents[1]
frozen=band/'release/band_6ec52a307565/source_snapshot'
variant='new' if '--new' in sys.argv else 'old'
identity=0x4c4e4b32 if variant=='new' else 0x4c4e4b31
build=band/('build/link_probe_'+variant+'_serializer');source=build/'source_snapshot';source.mkdir(parents=True,exist_ok=True)
for name in ('status_sender.v','event_receiver.v','uart.v','board.cst','board.sdc'):shutil.copy2(frozen/name,source/name)
if variant=='new':shutil.copy2(band/'rtl/status_sender.v',source/'status_sender.v')
top='''module band_top(input clk,input uart_rx_pin,output uart_tx_pin,output HP_BCK,HP_WS,HP_DIN,PA_EN);
reg [15:0] startup=0;always @(posedge clk)if(!(&startup))startup<=startup+1'b1;
reg rst=1;always @(posedge clk)rst<=!(&startup);
wire [7:0] byte_data;wire byte_valid,packet_valid,panic;wire [223:0] packet;wire [31:0] errors,overflow;
uart_rx #(.DIV(50)) receiver_uart(clk,rst,uart_rx_pin,byte_data,byte_valid);
event_receiver receiver(clk,rst,byte_data,byte_valid,packet_valid,1'b1,packet,panic,errors,overflow);
reg request;always @(posedge clk)if(rst)request<=0;else request<=packet_valid;
wire [223:0] snapshot={errors,32'd0,32'd50000000,32'd48000,32'd0,32'h4c4e4b31,8'd1,8'd0,8'ha1,8'd4};
status_sender sender(clk,rst,request,snapshot,uart_tx_pin);
assign HP_BCK=0;assign HP_WS=0;assign HP_DIN=0;assign PA_EN=0;
endmodule
'''
(source/'band_top.v').write_text(top.replace('4c4e4b31',f'{identity:08x}'))
tcl=f'cd "{build.as_posix()}"\nset_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0\nset_option -top_module band_top\nset_option -verilog_std v2001\nset_option -use_cpu_as_gpio 1\n'
tcl+=''.join('add_file "'+p.as_posix()+'"\n' for p in source.iterdir())
tcl+='set_option -output_base_name starcluster_band\nrun all\n';(build/'build.tcl').write_text(tcl)
with (build/'build.log').open('w') as log:r=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(build/'build.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=600)
if r.returncode:raise RuntimeError('Minimal build failed')
timing=(build/'impl/pnr/starcluster_band_tr_content.html').read_text()
for kind in ('Setup','Hold'):
    match=re.search('Numbers of '+kind+r' Violated Endpoints</td>\s*<td>(\d+)</td>',timing)
    if not match or int(match[1]):raise RuntimeError('Minimal timing failed')
fs=build/'impl/pnr/starcluster_band.fs';verify_fs(fs)
shutil.copy2(fs,build/'starcluster_band.fs')
record=dict(configuration='silent minimal UART only; no band/audio; '+variant+' serializer',build_id=identity,setup_violations=0,hold_violations=0,bitstream_sha256=hashlib.sha256(fs.read_bytes()).hexdigest(),snapshot_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()},frequencies=re.findall(r'\d+\.\d+\(MHz\)',timing))
(build/'manifest.json').write_text(json.dumps(record,indent=2));(band/('evidence/link_minimal_'+variant+'_build.json')).write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
