"""USB MIDI input; controls only, no audio synthesis on the computer.

Backend API: https://spotlightkid.github.io/python-rtmidi/rtmidi.html
"""
import json
import time
from pathlib import Path
import rtmidi
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget,QHBoxLayout,QLabel,QComboBox,QPushButton


class PadMap:
    def __init__(self,mapping=None):
        self.mapping=mapping if mapping is not None else {str(n):n-36 for n in range(36,44)}
        self.active={}

    @property
    def keys(self):
        return set(self.active.values())

    def feed(self,message):
        if len(message)<3:return None
        status,note,value=message[:3];kind=status&0xf0;channel=status&15
        if kind==0xb0 and note in (120,123):
            self.active={k:v for k,v in self.active.items() if k[0]!=channel}
            return 0
        if kind not in (0x80,0x90):return None
        owner=(channel,note)
        if kind==0x80 or value==0:
            self.active.pop(owner,None);return 0
        index=self.mapping.get(f'{channel}:{note}',self.mapping.get(str(note)))
        if index is None:return None
        self.active[owner]=index
        return value


class MidiPanel(QWidget):
    def __init__(self,changed,parent=None):
        super().__init__(parent)
        self.changed=changed;self.device=None;self.device_name='';self.mapper=PadMap()
        self.learning=None;self.last_inventory=0
        self.mapping_file=Path(__file__).with_name('midi_mapping.json')
        row=QHBoxLayout(self);row.setContentsMargins(0,0,0,0)
        row.addWidget(QLabel('MIDI 打击垫'))
        self.ports=QComboBox();self.ports.setMinimumWidth(220);row.addWidget(self.ports)
        refresh=QPushButton('刷新 MIDI');refresh.clicked.connect(self.refresh);row.addWidget(refresh)
        self.connect=QPushButton('连接 MIDI');self.connect.clicked.connect(self.toggle);row.addWidget(self.connect)
        self.learn=QPushButton('学习八个垫子');self.learn.clicked.connect(self.start_learning);row.addWidget(self.learn)
        self.status=QLabel('未连接');row.addWidget(self.status,1)
        self.timer=QTimer(self);self.timer.setInterval(5);self.timer.timeout.connect(self.poll)
        self.refresh()

    def refresh(self):
        if self.device:return
        try:
            probe=rtmidi.MidiIn();names=probe.get_ports();probe.delete()
            self.ports.clear();self.ports.addItems(names)
        except Exception as e:self.status.setText(f'MIDI 枚举失败：{e}')

    def toggle(self):
        if self.device:self.close_input();return
        name=self.ports.currentText()
        if not name:self.status.setText('未找到 MIDI 输入设备');return
        try:
            self.device=rtmidi.MidiIn(queue_size_limit=4096)
            names=self.device.get_ports()
            self.device.open_port(names.index(name));self.device_name=name
            self.mapper=PadMap()
            if self.mapping_file.exists():
                try:
                    mapping=json.loads(self.mapping_file.read_text(encoding='utf-8')).get(name)
                    if isinstance(mapping,dict) and all(isinstance(v,int) and 0<=v<8 for v in mapping.values()):
                        self.mapper=PadMap(mapping)
                except (OSError,ValueError):pass
            self.ports.setEnabled(False);self.connect.setText('断开 MIDI')
            self.status.setText('已连接 · 默认音符 36–43 / 可学习')
            if any(':' in k for k in self.mapper.mapping):self.status.setText('已连接 · 已载入学习映射')
            self.last_inventory=time.monotonic();self.timer.start()
        except Exception as e:self.close_input();self.status.setText(f'MIDI 打开失败：{e}')

    def clear(self):
        self.mapper.active.clear()

    def close_input(self):
        self.timer.stop();self.clear();self.learning=None;self.learn.setText('学习八个垫子')
        if self.device:
            try:self.device.close_port()
            finally:self.device.delete();self.device=None
        self.ports.setEnabled(True);self.connect.setText('连接 MIDI');self.status.setText('MIDI 已断开')
        self.changed(0)

    def start_learning(self):
        if not self.device:self.status.setText('请先连接 MIDI');return
        if self.learning is not None:
            self.learning=None;self.learn.setText('学习八个垫子');self.status.setText('学习取消，保留原映射');return
        self.clear();self.changed(0);self.learning=[];self.learn.setText('取消学习')
        self.status.setText('依次敲八个不同垫子：第 1 个 → C')

    def handle(self,message):
        if self.learning is not None:
            if len(message)>=3 and message[0]&0xf0==0x90 and message[2]>0:
                owner=f'{message[0]&15}:{message[1]}'
                if owner not in self.learning:self.learning.append(owner)
                if len(self.learning)==8:
                    self.mapper=PadMap({k:i for i,k in enumerate(self.learning)})
                    self.learning=None;self.learn.setText('学习八个垫子')
                    try:
                        try:all_maps=json.loads(self.mapping_file.read_text(encoding='utf-8'))
                        except (OSError,ValueError):all_maps={}
                        all_maps[self.device_name]=self.mapper.mapping
                        self.mapping_file.write_text(json.dumps(all_maps,indent=2),encoding='utf-8')
                        self.status.setText('学习完成 · 按顺序 C D E F G A B C')
                    except (OSError,TypeError):self.status.setText('映射已生效，但保存失败')
                else:self.status.setText(f'已学 {len(self.learning)}/8 · 请敲下一个不同垫子')
            return
        velocity=self.mapper.feed(message)
        if velocity is not None:
            self.status.setText(f'音符 {message[1]} · 力度 {message[2]} · 按下 {len(self.mapper.keys)} 键')
            self.changed(velocity)
        elif len(message)>=3 and message[0]&0xf0==0x90 and message[2]>0:
            self.status.setText(f'收到音符 {message[1]}，尚未映射 · 请学习八个垫子')

    def poll(self):
        if not self.device:return
        try:
            # Bounded draining keeps serial heartbeats and UI responsive.
            for _ in range(128):
                event=self.device.get_message()
                if event is None:break
                self.handle(event[0])
            if time.monotonic()-self.last_inventory>1:
                self.last_inventory=time.monotonic()
                if self.device_name not in self.device.get_ports():
                    self.close_input();self.status.setText('MIDI 设备已拔出，已释放按键')
        except Exception as e:
            self.close_input();self.status.setText(f'MIDI 连接中断：{e}')
