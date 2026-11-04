"""Replay captured RTL UART replies into the real Qt UI; no serial hardware."""
from pathlib import Path
import os,sys,json,hashlib
os.environ['QT_QPA_PLATFORM']='offscreen'
b=Path(__file__).resolve().parents[1];sys.path.insert(0,str(b/'host'))
from app import QApplication,Desk,QScrollArea
from protocol import Decoder
from stage import StageView
capture=b/'evidence/singer_telemetry/replies.hex'
decoder=Decoder();packets=decoder.feed(bytes.fromhex(capture.read_text()))
assert not decoder.bad_crc
identity=next(p for p in reversed(packets) if p[1]==161)
singer=next(p for p in packets if p[1]==162)
class Replay:
 def __init__(self):self.data=b'\xb4\x4b'+identity+b'\xb4\x4b'+singer
 @property
 def in_waiting(self):return len(self.data)
 def read(self,n):x=self.data[:n];self.data=self.data[n:];return x
 def write(self,x):return len(x)
 def close(self):pass
app=QApplication([]);desk=Desk();desk.pump_timer.stop();desk.beat_timer.stop();desk.port=Replay();desk.pump()
desk.identity_label.setText('回放 RTL 仿真回包（未连接硬件） · '+desk.identity_label.text())
desk.info.setText('界面验证：仅回放仿真数据，不连接串口。');desk.part.setCurrentIndex(15)
desk.show();app.processEvents();scroll=desk.findChild(QScrollArea)
scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum());app.processEvents()
out=b/'evidence/ui';out.mkdir(exist_ok=True);desk.grab().save(str(out/'singer_preview.png'))
from app import ROLES
stage=StageView(desk,ROLES);stage.timer.stop();stage.health.setText('RTL 仿真回包预览（未连接硬件）');stage.show();app.processEvents()
stage.grab().save(str(out/'singer_stage_preview.png'))
record=dict(scope='Real Qt UI replay of CRC-validated RTL capture, not board connection',horizontal_scroll_max=scroll.horizontalScrollBar().maximum(),bend_enabled=desk.bend.isEnabled(),vowel_enabled=desk.vowel.isEnabled(),patch_enabled=desk.patch_button.isEnabled(),source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [b/'host/app.py',b/'host/stage.py',capture]})
(b/'evidence/host_singer_telemetry/preview.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
stage.close();desk.close()
