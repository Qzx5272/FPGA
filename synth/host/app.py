"""Aurora 138 • hardware synthesizer control surface."""
import math
import sys
import time
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QEvent, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QPainterPath
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QDial, QFrame, QProgressBar, QSizePolicy)
import serial
from serial.tools import list_ports
from protocol import Controls, TelemetryParser, BAUD
from midi_input import MidiPanel

BG = '#10141b'
PANEL = '#191f29'
ACCENT = '#65ead0'
MUTED = '#8593a6'
KEYS = 'ASDFGHJK'
NAMES = ['C', 'D', 'E', 'F', 'G', 'A', 'B', 'C']


class Knob(QDial):
    def __init__(self, lo, hi, value):
        super().__init__()
        self.setRange(lo, hi)
        self.setValue(value)
        self.setFixedSize(118, 112)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setNotchesVisible(True)
        self.setWrapping(False)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(16, 10, 86, 86)
        f = (self.value()-self.minimum()) / max(1, self.maximum()-self.minimum())
        p.setPen(QPen(QColor('#303a48'), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(r, -135*16, -270*16)
        p.setPen(QPen(QColor(ACCENT), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(r, -135*16, int(-270*16*f))
        p.setBrush(QColor('#252f3d'))
        p.setPen(QPen(QColor('#475366'), 1))
        p.drawEllipse(QRectF(25, 19, 68, 68))
        angle = math.radians(135+270*f)
        p.setPen(QPen(QColor('#edfff9'), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(59+17*math.cos(angle),53+17*math.sin(angle)),
                   QPointF(59+28*math.cos(angle),53+28*math.sin(angle)))


class Envelope(QWidget):
    def __init__(self, controls):
        super().__init__()
        self.c = controls
        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def paintEvent(self, event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height()
        p.setPen(QPen(QColor('#283241'),1))
        for x in range(14,w,38): p.drawLine(x,15,x,h-25)
        for y in range(20,h-24,25): p.drawLine(14,y,w-12,y)
        a=.08+.22*self.c.attack_ms/1000
        r=.12+.20*self.c.release_ms/1300
        sustain=0 if self.c.tone==2 else (.61 if self.c.tone==1 else .75)
        pts=[QPointF(14,h-26),QPointF(14+(w-30)*a,22),
             QPointF(14+(w-30)*(a+.17),h-26-(h-48)*sustain),
             QPointF(w-16-(w-30)*r,h-26-(h-48)*sustain),QPointF(w-16,h-26)]
        path=QPainterPath(pts[0])
        for pt in pts[1:]:path.lineTo(pt)
        p.setPen(QPen(QColor(ACCENT),2.5)); p.drawPath(path)
        p.setPen(QColor(MUTED)); p.setFont(QFont('Microsoft YaHei',8))
        p.drawText(14,h-6,'ADSR 参数示意 · 非采集波形')


def label(text, size=12, color='#e4edf6'):
    q=QLabel(text)
    q.setStyleSheet(f'font-size:{size}px; color:{color};')
    return q


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('星群 STARCLUSTER · FPGA 演奏台')
        self.resize(1180,920)
        self.setMinimumSize(1100,870)
        self.controls=Controls()
        self.port=None
        self.parser=TelemetryParser()
        self.seq=0
        self.last_ack=0
        self.last_send=0
        self.opened_at=0
        self.sent={}
        self.keyboard=set()
        self.mouse=set()
        self.confirmed=False
        self.voice_events=[]
        self.voice_timer=QTimer(self); self.voice_timer.setSingleShot(True)
        self.voice_timer.timeout.connect(self.next_voice_event)
        root=QWidget(); self.setCentralWidget(root)
        layout=QVBoxLayout(root); layout.setContentsMargins(30,20,30,18); layout.setSpacing(14)
        head=QHBoxLayout(); layout.addLayout(head)
        title=QVBoxLayout(); title.addWidget(label('星 群   /   S T A R C L U S T E R',24)); title.addWidget(label('硬件合成 · 自动伴奏 · 人声实验   /   Tang Mega 138K Pro',12,MUTED))
        head.addLayout(title); head.addStretch()
        self.status=label('●  未连接',13,'#eeb96f'); head.addWidget(self.status)
        self.ports=QComboBox(); self.ports.setMinimumWidth(180); head.addWidget(self.ports)
        refresh=QPushButton('刷新'); refresh.clicked.connect(self.refresh); head.addWidget(refresh)
        self.connect_button=QPushButton('连接设备'); self.connect_button.setObjectName('primary')
        self.connect_button.clicked.connect(self.toggle_connection); head.addWidget(self.connect_button)
        self.midi=MidiPanel(self.midi_changed,self);layout.addWidget(self.midi)
        strip=QHBoxLayout(); layout.addLayout(strip)
        strip.addWidget(label('01   音色',12,MUTED))
        self.presets=[]
        for i,name in enumerate(['柔和 / SOFT','明亮 / BRIGHT','拨弦 / PLUCK']):
            b=QPushButton(name); b.setCheckable(True); b.clicked.connect(lambda checked=False,i=i:self.preset(i)); strip.addWidget(b); self.presets.append(b)
        self.presets[0].setChecked(True)
        strip.addStretch(); strip.addWidget(label('八度',12,MUTED))
        minus=QPushButton('−'); minus.setFixedWidth(38); minus.clicked.connect(lambda:self.octave(-1)); strip.addWidget(minus)
        self.octave_label=label('C4 — C5',16); strip.addWidget(self.octave_label)
        plus=QPushButton('+'); plus.setFixedWidth(38); plus.clicked.connect(lambda:self.octave(1)); strip.addWidget(plus)
        transport=QHBoxLayout(); layout.addLayout(transport)
        transport.addWidget(label('FPGA 自动伴奏',12,MUTED))
        self.play_button=QPushButton('▶  开始伴奏'); self.play_button.setCheckable(True)
        self.play_button.clicked.connect(self.toggle_play); transport.addWidget(self.play_button)
        transport.addWidget(label('速度',12,MUTED))
        self.tempo=QSlider(Qt.Orientation.Horizontal); self.tempo.setRange(20,83)
        self.tempo.setValue(48); self.tempo.setFixedWidth(170); self.tempo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tempo.valueChanged.connect(self.set_tempo); transport.addWidget(self.tempo)
        self.tempo_value=label('96 BPM',14,ACCENT); transport.addWidget(self.tempo_value)
        transport.addStretch();transport.addWidget(label('C 大调 · 16 步循环 · 板端计拍，可叠加手奏 / 人声',11,MUTED))
        voice_row=QHBoxLayout(); layout.addLayout(voice_row)
        voice_row.addWidget(label('人声实验 · 单声部',12,MUTED))
        self.voice_units=QComboBox()
        self.voice_units.addItems(['啊 / a','衣 / i','乌 / u','喔 / o','鹅 / e','迂 / ü','鼻音 / n','气流 / h'])
        voice_row.addWidget(self.voice_units)
        self.voice_units.currentIndexChanged.connect(self.select_voice)
        vowel_button=QPushButton('键盘演奏人声'); vowel_button.clicked.connect(lambda:self.select_voice(self.voice_units.currentIndex())); voice_row.addWidget(vowel_button)
        hello_button=QPushButton('试听“你好”'); hello_button.clicked.connect(self.sing_hello); voice_row.addWidget(hello_button)
        slow_button=QPushButton('慢速对比'); slow_button.clicked.connect(lambda:self.sing_hello(True));voice_row.addWidget(slow_button)
        voice_row.addStretch();voice_row.addWidget(label('合成原型 · 清晰度待试听',11,MUTED))
        panel=QFrame(); panel.setObjectName('panel'); panel.setMinimumHeight(245); middle=QHBoxLayout(panel); middle.setContentsMargins(20,20,20,15); middle.setSpacing(12); layout.addWidget(panel)
        knobcol=QVBoxLayout(); knobcol.addWidget(label('02   音色与包络',12,MUTED)); row=QHBoxLayout(); knobcol.addLayout(row)
        self.knobs={}
        for field,title,lo,hi,value,unit in [('brightness','明亮度',0,255,80,'%'),('attack_ms','起音 ATTACK',1,1000,15,'ms'),('release_ms','释放 RELEASE',10,1300,350,'ms')]:
            col=QVBoxLayout(); row.addLayout(col)
            t=label(title,12); t.setAlignment(Qt.AlignmentFlag.AlignCenter); col.addWidget(t)
            knob=Knob(lo,hi,value); col.addWidget(knob,alignment=Qt.AlignmentFlag.AlignCenter)
            val=label('',16,ACCENT); val.setAlignment(Qt.AlignmentFlag.AlignCenter); col.addWidget(val)
            def changed(v,field=field,val=val,unit=unit):
                setattr(self.controls,field,v)
                val.setText(f'{round(v/255*100)} %' if field=='brightness' else f'{v} ms')
                if hasattr(self,'envelope'): self.envelope.update()
                self.schedule_send()
            knob.valueChanged.connect(changed); self.knobs[field]=knob; changed(value)
        middle.addLayout(knobcol)
        visual=QVBoxLayout(); visual.addWidget(label('声音轮廓',12,MUTED)); self.envelope=Envelope(self.controls); visual.addWidget(self.envelope); middle.addLayout(visual,1)
        volume_col=QVBoxLayout(); volume_col.addWidget(label('主音量',12,MUTED))
        self.volume=QSlider(Qt.Orientation.Vertical); self.volume.setRange(0,127); self.volume.setValue(self.controls.volume); self.volume.setMinimumHeight(100); self.volume.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        volume_col.addWidget(self.volume,alignment=Qt.AlignmentFlag.AlignHCenter)
        self.volume_value=label(f'{round(self.controls.volume/127*100)} %',16,ACCENT); volume_col.addWidget(self.volume_value)
        self.volume.valueChanged.connect(self.set_volume); middle.addLayout(volume_col)
        performance=QHBoxLayout(); layout.addLayout(performance)
        performance.addWidget(label('03   键盘 / C 大调 · 八键复音',12,MUTED)); performance.addStretch()
        performance.addWidget(label('触发力度 · MIDI ×1.5',12,MUTED))
        self.velocity=QSlider(Qt.Orientation.Horizontal); self.velocity.setRange(1,127); self.velocity.setValue(100); self.velocity.setFixedWidth(145); self.velocity.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        performance.addWidget(self.velocity); self.velocity_value=label('100',13); performance.addWidget(self.velocity_value)
        self.velocity.valueChanged.connect(self.set_velocity)
        pads=QHBoxLayout(); pads.setSpacing(3); layout.addLayout(pads)
        self.pads=[]
        for i in range(8):
            b=QPushButton(); b.setObjectName('pad'); b.setMinimumHeight(148); b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.pressed.connect(lambda i=i:self.mouse_note(i,True)); b.released.connect(lambda i=i:self.mouse_note(i,False)); pads.addWidget(b); self.pads.append(b)
        self.update_pads()
        layout.addWidget(label('键盘 A S D F G H J K 演奏  ·  鼠标拖动旋钮 / 滑块调节  ·  空格全部停止',12,MUTED))
        bottom=QFrame(); bottom.setObjectName('panel'); foot=QHBoxLayout(bottom); foot.setContentsMargins(18,14,18,14); layout.addWidget(bottom)
        self.voices=label('活跃声部  — / 9',14); foot.addWidget(self.voices)
        self.rtt=label('通信往返  —',12,MUTED); foot.addWidget(self.rtt); foot.addStretch()
        foot.addWidget(label('FPGA 峰值',12,MUTED)); self.meter=QProgressBar(); self.meter.setRange(0,32768); self.meter.setValue(0); self.meter.setTextVisible(False); self.meter.setFixedSize(140,9); foot.addWidget(self.meter)
        panic=QPushButton('■  全部停止'); panic.setObjectName('panic'); panic.clicked.connect(self.panic); foot.addWidget(panic)
        self.message=label('接入 JTAG/UART 后选择串口。收到 FPGA 回传后才会显示“已连接”。',11,MUTED); layout.addWidget(self.message)
        self.flush_timer=QTimer(self); self.flush_timer.setSingleShot(True); self.flush_timer.timeout.connect(self.send)
        self.timer=QTimer(self); self.timer.setInterval(5); self.timer.timeout.connect(self.poll); self.timer.start()
        QApplication.instance().installEventFilter(self)
        self.refresh()

    def refresh(self):
        if self.port: return
        self.ports.clear()
        ports=list(list_ports.comports())
        ports.sort(key=lambda p:(p.vid!=0x0403, not (p.serial_number or '').endswith('B'),p.device))
        for p in ports:self.ports.addItem(f'{p.device} · {p.description}',p.device)

    def toggle_connection(self):
        if self.port:self.disconnect(); return
        name=self.ports.currentData()
        if not name:self.message.setText('未找到串口，请连接开发板后刷新。'); return
        try:
            self.port=serial.Serial(name,BAUD,timeout=0,write_timeout=.05)
            self.port.reset_input_buffer(); self.parser=TelemetryParser(); self.sent={}
            self.confirmed=False; self.last_ack=0; self.opened_at=time.monotonic()
            self.ports.setEnabled(False); self.connect_button.setText('断开')
            self.status.setText('●  等待 FPGA'); self.message.setText('串口已打开，正在验证 FPGA 固件协议…')
            self.panic()
        except (serial.SerialException,OSError) as e:self.disconnect(str(e))

    def disconnect(self,error=None):
        self.midi.clear()
        self.voice_timer.stop();self.voice_events=[]
        if self.port:
            try:self.port.write(self.controls.packet(self.seq,True))
            except (serial.SerialException,OSError):pass
            finally:self.port.close()
        self.controls.auto_play=False; self.play_button.setChecked(False); self.play_button.setText('▶  开始伴奏')
        self.port=None; self.confirmed=False; self.keyboard.clear(); self.mouse.clear(); self.controls.keys=0; self.update_pads()
        self.status.setText('●  未连接'); self.status.setStyleSheet('color:#eeb96f; font-size:13px;')
        self.ports.setEnabled(True); self.connect_button.setText('连接设备'); self.voices.setText('活跃声部  — / 9'); self.meter.setValue(0); self.rtt.setText('通信往返  —')
        self.message.setText(error or '设备已断开。')

    def schedule_send(self):
        if hasattr(self,'flush_timer') and not self.flush_timer.isActive():self.flush_timer.start(8)

    def send(self,panic=False):
        if not self.port:return
        try:
            packet=self.controls.packet(self.seq,panic)
            if self.port.write(packet)!=len(packet):raise serial.SerialTimeoutException('指令未完整发送')
            now=time.monotonic(); self.sent[self.seq]=now; self.seq=(self.seq+1)&255; self.last_send=now
        except (serial.SerialException,OSError) as e:self.disconnect(str(e))

    def poll(self):
        if not self.port:return
        now=time.monotonic()
        try:
            data=self.port.read(min(self.port.in_waiting,4096))
            for reply in self.parser.feed(data):
                if reply['version']!=2:continue
                self.last_ack=now; self.confirmed=True
                self.status.setText('●  FPGA 已连接'); self.status.setStyleSheet(f'color:{ACCENT};font-size:13px;')
                self.voices.setText(f"活跃声部  {reply['voices']} / 9"); self.meter.setValue(reply['peak'])
                sent=self.sent.pop(reply['sequence'],None)
                if sent:self.rtt.setText(f'通信往返  {(now-sent)*1000:.1f} ms')
                self.message.setText('FPGA 回传正常  ·  固件 v2 · 48 kHz / 16 bit · 板载 DAC  ·  通信往返不等于音频延迟')
            if now-(self.last_ack or self.opened_at)>1.5:
                self.disconnect('未收到有效 FPGA 回传。请确认已加载合成器固件，并尝试另一个 USB 串口。');return
            if now-self.last_send>.10:self.send()
        except (serial.SerialException,OSError) as e:self.disconnect(str(e))

    def toggle_play(self,checked):
        if checked and not self.confirmed:
            self.play_button.setChecked(False)
            self.message.setText('请先连接固件 v2，再启动 FPGA 自动伴奏。');return
        self.controls.auto_play=checked
        self.play_button.setText('■  停止伴奏' if checked else '▶  开始伴奏')
        self.send()

    def set_tempo(self,v):
        self.controls.bpm=v*2; self.tempo_value.setText(f'{v*2} BPM'); self.schedule_send()

    def mode_panic(self):
        # A mode change releases the manual voice without stopping accompaniment.
        playing=self.controls.auto_play
        self.panic()
        self.controls.auto_play=playing
        self.play_button.setChecked(playing)
        self.play_button.setText('■  停止伴奏' if playing else '▶  开始伴奏')

    def set_volume(self,v):
        self.controls.volume=v; self.volume_value.setText(f'{round(v/127*100)} %'); self.schedule_send()

    def set_velocity(self,v):
        self.controls.velocity=v; self.velocity_value.setText(str(v)); self.schedule_send()

    def preset(self,i):
        self.mode_panic();self.knobs['brightness'].setEnabled(True)
        self.controls.tone=i
        for j,b in enumerate(self.presets):b.setChecked(j==i)
        values=[(80,15,350),(210,8,220),(165,2,180)][i]
        for field,v in zip(['brightness','attack_ms','release_ms'],values):self.knobs[field].setValue(v)
        self.envelope.update(); self.send()

    def select_voice(self,index):
        self.mode_panic()
        self.controls.tone=3;self.controls.brightness=index
        self.knobs['brightness'].setEnabled(False)
        for b in self.presets:b.setChecked(False)
        self.knobs['attack_ms'].setValue(12);self.knobs['release_ms'].setValue(70)
        self.send()

    def sing_hello(self,slow=False):
        if not self.confirmed:
            self.message.setText('请先连接已更新的人声固件。');return
        self.select_voice(6)
        # One trigger: the FPGA owns every phoneme frame and the pitch contour.
        self.voice_events=[(9 if slow else 8,1,2050 if slow else 1400)]
        self.next_voice_event()

    def next_voice_event(self):
        if not self.voice_events:
            self.controls.keys=0;self.controls.brightness=self.voice_units.currentIndex()
            self.update_pads();self.send();return
        unit,keys,duration=self.voice_events.pop(0)
        self.controls.brightness=unit;self.controls.keys=keys
        if unit<8:
            self.voice_units.blockSignals(True);self.voice_units.setCurrentIndex(unit);self.voice_units.blockSignals(False)
        self.update_pads();self.send();self.voice_timer.start(duration)

    def octave(self,delta):
        # Release current notes before changing key mapping.
        self.panic(); self.controls.octave=max(2,min(6,self.controls.octave+delta)); self.update_pads(); self.send()

    def update_pads(self):
        for i,b in enumerate(self.pads):
            n=f'{NAMES[i]}{self.controls.octave+(i==7)}'
            b.setText(f'{n}\n\n{KEYS[i]}')
            b.setProperty('active',bool(self.controls.keys&(1<<i)))
            b.style().unpolish(b);b.style().polish(b)
        self.octave_label.setText(f'C{self.controls.octave} — C{self.controls.octave+1}')

    def update_keys(self):
        if self.controls.tone==3 and self.controls.brightness>=8:
            self.controls.brightness=self.voice_units.currentIndex()
        self.voice_timer.stop();self.voice_events=[]
        self.controls.keys=sum(1<<i for i in self.keyboard|self.mouse|self.midi.mapper.keys); self.update_pads(); self.send()

    def midi_changed(self,velocity):
        if not self.confirmed:
            self.midi.clear();return
        if velocity>0:self.velocity.setValue(min(127,round(velocity*1.5)))
        self.update_keys()

    def mouse_note(self,i,on):
        if on:self.mouse.add(i)
        else:self.mouse.discard(i)
        self.update_keys()

    def panic(self):
        if hasattr(self,'midi'):self.midi.clear()
        self.controls.auto_play=False
        if hasattr(self,'play_button'):
            self.play_button.setChecked(False); self.play_button.setText('▶  开始伴奏')
        self.voice_timer.stop();self.voice_events=[]
        if self.controls.tone==3 and self.controls.brightness>=8:
            self.controls.brightness=self.voice_units.currentIndex()
        self.keyboard.clear(); self.mouse.clear(); self.controls.keys=0
        if hasattr(self,'pads'):self.update_pads()
        self.send(True)

    def eventFilter(self,obj,event):
        if event.type()==QEvent.Type.ApplicationDeactivate:
            self.panic()
        if event.type() in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease) and self.isActiveWindow():
            if event.isAutoRepeat():return True
            key=event.key()
            if key==Qt.Key.Key_Space:
                if event.type()==QEvent.Type.KeyPress:self.panic()
                return True
            chars={ord(k):i for i,k in enumerate(KEYS)}
            if key in chars:
                i=chars[key]
                if event.type()==QEvent.Type.KeyPress:self.keyboard.add(i)
                else:self.keyboard.discard(i)
                self.update_keys();return True
        return super().eventFilter(obj,event)

    def closeEvent(self,event):
        self.timer.stop();self.flush_timer.stop();self.voice_timer.stop()
        self.midi.close_input()
        QApplication.instance().removeEventFilter(self)
        self.disconnect(); event.accept()


STYLE='''
QWidget { background:#10141b; color:#e4edf6; font-family:"Microsoft YaHei UI"; font-size:13px; }
QFrame#panel { background:#191f29; border:1px solid #293342; border-radius:14px; }
QFrame#panel QWidget { background:transparent; }
QPushButton { background:#232c39; border:1px solid #344253; border-radius:7px; padding:9px 14px; }
QPushButton:hover { border-color:#65ead0; background:#2a3946; }
QPushButton:checked { background:#214b45; border-color:#65ead0; color:#8cf6df; }
QPushButton#primary { background:#65ead0; color:#102921; border:0; font-weight:600; }
QPushButton#panic { background:#3b282e; color:#ffb2ae; border-color:#654148; }
QPushButton#pad { background:#e8edea; color:#25342f; border:1px solid #b3c6bd; border-bottom:8px solid #91a89e; border-radius:5px; font-size:21px; padding-top:48px; }
QPushButton#pad[active="true"] { background:#3b8c7c; color:#ffffff; border-color:#8cf6df; border-bottom:5px solid #65ead0; }
QComboBox { background:#1c2531; padding:8px; border:1px solid #344253; border-radius:6px; }
QComboBox QAbstractItemView { background:#1c2531; color:#e4edf6; selection-background-color:#34554e; }
QSlider::groove:vertical { background:#303c4b; width:6px; border-radius:3px; }
QSlider::handle:vertical { background:#65ead0; border:1px solid #9affea; height:15px; margin:0 -9px; border-radius:4px; }
QSlider::groove:horizontal { background:#303c4b; height:5px; }
QSlider::handle:horizontal { background:#65ead0; width:13px; margin:-5px 0; border-radius:6px; }
QProgressBar { border:0; background:#303c4b; border-radius:4px; }
QProgressBar::chunk { background:#65ead0; border-radius:4px; }
'''


def main():
    app=QApplication(sys.argv); app.setStyle('Fusion'); app.setStyleSheet(STYLE)
    window=MainWindow(); window.show()
    if window.midi.ports.count():QTimer.singleShot(250,window.midi.toggle)
    if '--connect' in sys.argv:
        port=sys.argv[sys.argv.index('--connect')+1]
        index=window.ports.findData(port)
        if index>=0:
            window.ports.setCurrentIndex(index)
            QTimer.singleShot(100,window.toggle_connection)
    if '--screenshot' in sys.argv:
        dest=Path(sys.argv[sys.argv.index('--screenshot')+1]); dest.parent.mkdir(parents=True,exist_ok=True)
        def capture():window.grab().save(str(dest)); app.quit()
        QTimer.singleShot(900,capture)
    return app.exec()


if __name__=='__main__':sys.exit(main())
