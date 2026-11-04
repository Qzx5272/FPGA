"""Create an isolated PCM5102 song candidate from the frozen V6 release."""
from pathlib import Path
import hashlib,json,shutil,datetime
root=Path(__file__).resolve().parents[3]
base=root/'synth/band/release/pt8211_dvi_8994dbe5e358'
out=Path('D:/StarclusterBuilds/pcm5102_song_20261031')
out.mkdir(exist_ok=False)
m=json.loads((base/'manifest.json').read_text())
for name,h in m['snapshot_sha256'].items():
    p=base/'source_snapshot'/name
    assert hashlib.sha256(p.read_bytes()).hexdigest()==h,name
    shutil.copy2(p,out/name)
def replace(name,old,new):
    p=out/name;s=p.read_text();assert s.count(old)==1,(name,old)
    p.write_text(s.replace(old,new))
replace('audio_pt8211_queue.v','.MODE_I2S(0)','.MODE_I2S(1)')
replace('board_pt8211_controls_top.sv',' offline_workstation_top workstation(',' assign PA_EN=1\'b0;\n offline_workstation_top workstation(')
replace('board_pt8211_controls_top.sv','.PA_EN(PA_EN)','.PA_EN()')
for signal,old,new in [('HP_BCK','E22','W21'),('HP_WS','F24','Y21'),('HP_DIN','G24','P21')]:
    replace('board.cst',f'IO_LOC "{signal}" {old};',f'IO_LOC "{signal}" {new};')
    replace('board.cst',f'IO_PORT "{signal}" IO_TYPE=LVCMOS33 DRIVE=8',f'IO_PORT "{signal}" IO_TYPE=LVCMOS33 DRIVE=4')
replace('build_identity.vh',"32'h20261028","32'h20261031")
sources=sorted(p for p in out.iterdir() if p.suffix in ('.sv','.v') and not p.name.startswith('tb_'))
tcl='''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module board_pt8211_controls_top
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
set_option -netlist_hierarchy 1
set_option -cst_warn_to_error 1
set_option -output_base_name pcm5102_song
set_option -route_option 0
set_option -correct_hold_violation 1
'''
tcl+=''.join('add_file '+p.name+'\n' for p in sources)
tcl+='add_file board.cst\nadd_file board.sdc\nrun syn\nrun pnr\n'
(out/'build.tcl').write_text(tcl)
manifest=dict(status='prepared',base_release=base.name,build_id=0x20261031,
    created=datetime.datetime.now().isoformat(),programmed=False,
    scope='Original 96s score and V6 synthesis engine; 16-bit standard I2S at average 48kHz; microphone idle; SRAM only',
    sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()})
(out/'candidate.json').write_text(json.dumps(manifest,indent=2))
print(out)
