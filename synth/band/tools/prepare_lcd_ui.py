from pathlib import Path
import hashlib,json,shutil,re
band=Path(__file__).resolve().parents[1];root=band.parents[1]
base=Path('D:/StarclusterBuilds/hdmi_ui_20261031_b');out=Path('D:/StarclusterBuilds/lcd_ui_20261031_a');assert not out.exists()
r=json.loads((base/'candidate.json').read_text())
for name,h in r['sources'].items():
 if name=='pnr_only.tcl':continue
 p=base/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==h
 q=out/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
shutil.copy2(band/'experimental/lcd_ui/board_lcd_ui_top.sv',out/'rtl/board_lcd_ui_top.sv')
probe=Path('D:/StarclusterBuilds/lcd_probe_20261031');shutil.copy2(probe/'pll.v',out/'rtl/lcd_pll.v')
(out/'rtl/build_identity.vh').write_text("`define BAND_BUILD_ID 32'h20261051\n")
old=json.loads((band/'evidence/phone_fpga_20261031/fpga_audit.json').read_text())['pins'];pins={n:p for n,p in old.items() if not n.startswith('tmds_')};pins.update(json.loads((probe/'pins.json').read_text()))
assert len(pins)==35 and len(set(pins.values()))==35
inputs={'clk','uart_rx_pin','ble_rx','key_play_n','key_stop_n','key_panic_n'}
(out/'board.cst').write_text('\n'.join(f'IO_LOC "{n}" {p};\nIO_PORT "{n}" IO_TYPE=LVCMOS33 PULL_MODE='+('UP' if n in inputs-{'clk'} else 'NONE')+(' DRIVE=8;' if n not in inputs else ';') for n,p in pins.items()))
s=(probe/'board.sdc').read_text()+'''set_max_delay 20.000 -from [get_clocks {core_clk}] -to [get_clocks {lcd_pixel}]
set_min_delay 0.000 -from [get_clocks {core_clk}] -to [get_clocks {lcd_pixel}]
set_max_delay 20.000 -from [get_clocks {lcd_pixel}] -to [get_clocks {core_clk}]
set_min_delay 0.000 -from [get_clocks {lcd_pixel}] -to [get_clocks {core_clk}]
set_max_delay 20.000 -from [get_clocks {core_clk}] -to [get_ports {HP_BCK HP_WS HP_DIN ble_tx}]
set_min_delay 0.000 -from [get_clocks {core_clk}] -to [get_ports {HP_BCK HP_WS HP_DIN ble_tx}]
set_false_path -from [get_ports {key_play_n}] -to [get_pins {engine/local_inputs.play_button/synchronized_0_s0/D}]
set_false_path -from [get_ports {key_stop_n}] -to [get_pins {engine/local_inputs.stop_button/synchronized_0_s0/D}]
set_false_path -from [get_ports {key_panic_n}] -to [get_pins {engine/local_inputs.panic_sync_0_s0/D}]
set_false_path -from [get_ports {ble_rx}] -to [get_pins {engine/ble_uart/sync_0_s0/D}]
set_false_path -hold -to [get_pins {ui_cdc/display_data*_s0/D ui_cdc/ack1_s0/D ui_cdc/req1_s0/D}]
'''
(out/'board.sdc').write_text(s)
t=(out/'build.tcl').read_text().replace('board_pt8211_controls_top','board_lcd_ui_top');(out/'build.tcl').write_text(t)
(out/'pins.json').write_text(json.dumps(pins,indent=2))
r={'build_id':0x20261051,'features':0x8000107c,'screen':'J20 RGB666 800x480, 25MHz, user confirmed full color bars','parent':str(base),'sources':{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}}
(out/'candidate.json').write_text(json.dumps(r,indent=2));print(out)
