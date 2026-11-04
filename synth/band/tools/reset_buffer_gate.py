"""Bind the reviewed reset-buffer source to preserved synthesized connectivity."""
from pathlib import Path
import hashlib,re
BUFFER_SOURCE_SHA256='d10232ca3fdb6ed03ee63dc4b74b38b432749d4c576fc686aff1c296e0dbd1c5'
BUFFER_SOURCES={BUFFER_SOURCE_SHA256:8,
    '07e54af00ed5cb92a59742f1b12728dc01abab5e73902effc813739cae3f547b':16}

def native_reset_report_commands():
    # SUG940-2.0.4E section5.5.1: report_timing through get_pins.
    # These request native checks; they do not override any path requirement.
    return [
        'report_timing -'+kind+' -through [get_pins {workstation/video_output/transmitter/channels['+str(lane)+'].serializer/RESET}] -max_paths 5 -max_common_paths 5'
        for kind in ('recovery','removal') for lane in range(3)]

def check_reset_buffers(build):
    build=Path(build);source=build/'rtl/gowin_dvi_tx.v'
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if digest not in BUFFER_SOURCES:return None
    stages=BUFFER_SOURCES[digest]
    vg=build/'impl/gwsynthesis/pt8211_onboard.vg';s=vg.read_text()
    for n in range(1,stages+1):
        cells=re.findall(r'\bLUT1 reset_buffer_'+str(n)+r'\s*\((.*?)\);',s,re.S)
        assert len(cells)==1, ('Missing/duplicated reset buffer',n)
        assert f'.F(reset_route_{n})' in cells[0] and f'.I0(reset_route_{n-1})' in cells[0], ('Reset chain connectivity changed',n)
        assert s.count(f"defparam reset_buffer_{n}.INIT=2'h1;")==1, ('Reset polarity changed',n)
    assert s.count(f'.RESET(reset_route_{stages})')==3, 'Serializer reset endpoints changed'
    return {'status':'passed_synthesized_connectivity_only','stages':stages,'serializer_reset_endpoints':3,
            'source_sha256':digest,'netlist_sha256':hashlib.sha256(vg.read_bytes()).hexdigest(),
            'scope':f'{stages}even LUT1 inversions preserved; not proof of physical cell retention or native recovery/removal margins'}
