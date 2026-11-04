"""Mathematical control tables, not recorded audio."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
lines=['// 32-bit DDS increments at 48000 samples/s; MIDI A4=440 Hz.', 'function [31:0] midi_increment;', 'input [6:0] n;','begin case(n)']
for n in range(128):lines.append(f"7'd{n}: midi_increment=32'd{round(440*2**((n-69)/12)*2**32/48000)};")
lines.extend(["default:midi_increment=0;",'endcase end','endfunction'])
(root/'rtl/midi_increment.vh').write_text('\n'.join(lines)+'\n',encoding='ascii')
tempo=['// Virtual score sample increment, Q16, reference tempo 120 BPM.','function [17:0] tempo_increment;','input [7:0] bpm;','begin case(bpm)']
for bpm in range(40,241):tempo.append(f"8'd{bpm}:tempo_increment=18'd{round(bpm*65536/120)};")
tempo.extend(["default:tempo_increment=18'd65536;",'endcase end','endfunction'])
(root/'rtl/tempo_increment.vh').write_text('\n'.join(tempo)+'\n',encoding='ascii')
