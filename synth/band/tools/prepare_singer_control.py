"""Build a singer-off control from a frozen integrated project without changing it."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

def prepare(source,out,grouped=False,no_panel_keys=False):
    manifest=json.loads((source/'manifest.json').read_text())
    optimized_parent=manifest.get('build_id')==0x20261109
    if no_panel_keys and (grouped or not optimized_parent):
        raise ValueError('The no-panel-keys control requires the frozen grouped singer baseline')
    out.mkdir(parents=True,exist_ok=False)
    hashes={Path(k).as_posix():v for k,v in manifest['source_sha256'].items()}
    def save(name,text):
        (out/name).write_text(text)
        hashes[name]=hashlib.sha256((out/name).read_bytes()).hexdigest()
    for name,expected in hashes.items():
        path=source/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError(f'Source changed: {name}')
        dest=out/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,dest)
    if grouped:
        grouped_source=Path(__file__).resolve().parents[1]/'experimental/vocoder/filterbank_grouped.sv'
        save('rtl/filterbank.sv',grouped_source.read_text())
        build_id=0x20261109
        save('rtl/build_identity.vh',"`define BAND_BUILD_ID 32'h20261109\n")
    else:
        build_id=(0x20261111 if no_panel_keys else 0x20261110) if optimized_parent else 0x20261108
        name='rtl/band_singer_core.sv'
        core=(out/name).read_text()
        start=core.index(' singer_role #(.COEFF_FILE')
        end=core.index('endmodule',start)
        save(name,core[:start]+""" // The non-singing band mix is the DAC source. Part 15 consumes events
 // silently so release/broadcast traffic cannot stall other instruments.
 assign singer_left={band_left,8'd0};assign singer_right={band_right,8'd0};
 assign audio_valid=band_audio_valid;
 assign singer_event_ready=1;assign singer_frame_ready=1;
 assign singer_gate=0;assign singer_note=0;
 assign singer_rejected=0;assign singer_stale_off=0;assign singer_duplicates=0;
 assign singer_dropped=0;assign singer_mix_clips=0;assign singer_vocoder_clips=0;
"""+core[end:])
        name='rtl/band_stage_pt8211_engine.sv'
        engine=(out/name).read_text()
        assert engine.count("32'h8000307c")==1
        save(name,engine.replace("32'h8000307c","32'h8000305c"))
        save('rtl/build_identity.vh',f"`define BAND_BUILD_ID 32'h{build_id:08x}\n")
    if no_panel_keys:
        name='rtl/board_lcd_ui_top.sv'
        top=(out/name).read_text()
        for old,new in [('input[3:0]panel_key_high,',''),('.keys_high(panel_key_high)',".keys_high(4'd0)")]:
            assert top.count(old)==1
            top=top.replace(old,new)
        save(name,top)
        for name,n in [('board.sdc',4),('board.cst',8)]:
            lines=(out/name).read_text().splitlines()
            kept=[line for line in lines if 'panel_key_high[' not in line]
            assert len(lines)-len(kept)==n
            save(name,'\n'.join(kept)+'\n')
        pins=json.loads((out/'pins.json').read_text())
        for index in range(4):del pins[f'panel_key_high[{index}]']
        save('pins.json',json.dumps(pins,indent=2))

    # Reuse the same implementation command, seed file and route options.
    shutil.copyfile(source/'incremental.tcl',out/'incremental.tcl')
    manifest.update(build_id=build_id,parent=str(source),electronic_singer=grouped,external_panel_keys=not no_panel_keys,source_sha256=hashes)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('out',type=Path)
    parser.add_argument("--grouped",action="store_true",help="Retain the singer with grouped histories")
    parser.add_argument("--no-panel-keys",action="store_true")
    args=parser.parse_args();prepare(args.source,args.out,args.grouped,args.no_panel_keys)
