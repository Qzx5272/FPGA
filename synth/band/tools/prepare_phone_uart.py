"""Isolated native PT8211 candidate with a second UART on verified J23 pins.
Does not change CURRENT_RELEASE, start synthesis, or program hardware.
"""
from pathlib import Path
import json,hashlib,shutil
band=Path(__file__).resolve().parents[1]
base=band/'release/pt8211_dvi_8994dbe5e358'
out=Path('D:/StarclusterBuilds/phone_uart_20261031_a')
assert not out.exists(),'Preserve existing candidate'
rtl=out/'rtl';rtl.mkdir(parents=True)
manifest=json.loads((base/'manifest.json').read_text())
for name,h in manifest['snapshot_sha256'].items():
 p=base/'source_snapshot'/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==h,name
 shutil.copy2(p,out/name if p.suffix in ('.mem','.cst','.sdc') else rtl/name)
def change(name,old,new):
 p=rtl/name;s=p.read_text();assert s.count(old)==1,(name,old);p.write_text(s.replace(old,new))
for name,old in [('board_pt8211_controls_top.sv','input wire clk,uart_rx_pin,'),('offline_workstation_top.sv','module offline_workstation_top(input clk,uart_rx_pin,mic_bck,mic_ws,mic_sd,'),('band_workstation_pt8211_top.sv','input wire clk,uart_rx_pin,mic_bck,mic_ws,mic_sd,')]:
 change(name,old,old+'\n input wire ble_rx,output wire ble_tx,')
 change(name,'.clk(clk),.uart_rx_pin(uart_rx_pin),.uart_tx_pin(uart_tx_pin),','.clk(clk),.uart_rx_pin(uart_rx_pin),.uart_tx_pin(uart_tx_pin),.ble_rx(ble_rx),.ble_tx(ble_tx),')
change('band_stage_pt8211_engine.sv','input clk,input uart_rx_pin,output uart_tx_pin,','input clk,input uart_rx_pin,output uart_tx_pin,input wire ble_rx,output wire ble_tx,')
change('band_stage_pt8211_engine.sv','offline_started<=1;offline_play<=1;','offline_started<=1;offline_play<=0;')
change('band_stage_pt8211_engine.sv','event_receiver receiver(clk,rst,byte_data,byte_valid,packet_valid,packet_ready,packet,host_panic,crc_errors,overflow);','''wire[7:0]ble_data;wire ble_valid;
 uart_rx #(.DIV(50)) ble_uart(clk,rst,ble_rx,ble_data,ble_valid);
 assign ble_tx=uart_tx_pin;
 dual_uart_events receiver(clk,rst,byte_data,ble_data,byte_valid,ble_valid,
  1'b0,,224'd0,packet_valid,packet_ready,packet,host_panic,crc_errors,overflow);''')
change('band_stage_pt8211_engine.sv',"32'h8000007c","32'h8000107c")
(rtl/'build_identity.vh').write_text("`define BAND_BUILD_ID 32'h20261031\n")
shutil.copy2(band/'experimental/panel_v6/dual_uart_events.v',rtl/'dual_uart_events.v')
with (out/'board.cst').open('a') as f:f.write('''
// J23-1 input from C3 GPIO4, J23-2 output to C3 GPIO5.
IO_LOC "ble_rx" U16;
IO_PORT "ble_rx" IO_TYPE=LVCMOS33 PULL_MODE=UP;
IO_LOC "ble_tx" V16;
IO_PORT "ble_tx" IO_TYPE=LVCMOS33 DRIVE=8 PULL_MODE=NONE;
''')
with (out/'board.sdc').open('a') as f:f.write('''
// Async UART input: only the first synchronizer D is exempt.
set_false_path -from [get_ports {ble_rx}] -to [get_pins {workstation/band/engine/ble_uart/sync_0_s0/D}]
set_max_delay 20.000 -from [get_clocks {core_clk}] -to [get_ports {ble_tx}]
set_min_delay 0.000 -from [get_clocks {core_clk}] -to [get_ports {ble_tx}]
''')
(out/'build.tcl').write_text('''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module board_pt8211_controls_top
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
set_option -netlist_hierarchy 1
foreach f [glob rtl/*.v rtl/*.sv] {add_file $f}
add_file board.cst
add_file board.sdc
set_option -cst_warn_to_error 1
set_option -output_base_name phone_uart
set_option -route_option 0
set_option -correct_hold_violation 1
run syn
run pnr
''')
sources={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
(out/'candidate.json').write_text(json.dumps({'baseline':base.name,'build_id':0x20261031,'features':0x8000107c,'sources':sources,'status':'prepared_not_programmed'},indent=2))
print(out)
