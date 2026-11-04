"""V4 band desk. FPGA generates all audio; this app only sends events."""
import sys,time,json
from pathlib import Path
from collections import deque
import serial
from serial.tools import list_ports
from PySide6.QtCore import Qt,QTimer,Signal,QObject,QSignalBlocker
from PySide6.QtGui import QFont,QFontDatabase,QShortcut,QKeySequence
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QComboBox,QSlider,QSpinBox,QGroupBox,QCheckBox,QScrollArea
from protocol import Event,Decoder,status,singer_status,UART_BATCH_SIZE
from editor import ScoreEditor
from patch_editor import PatchEditor
from score import upload_events,validate_target
from pad_mapping import read_maps,save_maps,normalize_mapping,normalize_seats
from stage import StageState,StageView
try:import rtmidi
except ImportError:rtmidi=None
ROLES=['底鼓','军鼓','踩镲','贝斯','电钢琴','持续簧音','主奏','元音式合唱']+[f'扩展轨 {i+1}' for i in range(8,16)]
class MidiBridge(QObject):
    message=Signal(object)
class Desk(QMainWindow):
    def __init__(self):
        for font_file in ('C:/Windows/Fonts/msyh.ttc','C:/Windows/Fonts/msyhbd.ttc'):
            if Path(font_file).exists():QFontDatabase.addApplicationFont(font_file)
        QApplication.instance().setFont(QFont('Microsoft YaHei',10))
        super().__init__();self.setWindowTitle('星群 · FPGA 乐队演奏台 V4');self.resize(1180,780)
        self.port=None;self.decoder=Decoder();self.queue=deque();self.held={};self.next_serial=1;self.states={};self.midi=None;self.last_rx=0
        self.upload_generator=None;self.await_upload=False;self.upload_errors=0;self.upload_error_baseline=0;self.editor=None
        self.midi_generations={};self.midis={};self.midi_contacts={};self.seat_parts={1:6,2:0,3:4,4:7}
        self.midi_sustain=set();self.midi_deferred=set()
        self.patch_values={}
        self.pad_calibration={}
        self.stage_state=StageState();self.stage_view=None;self.stage_poll_part=0;self.board_identity=None;self.identity_requested=0
        self.singer_snapshot=None;self.singer_received=0;self.vision_control=None
        self.bridge=MidiBridge();self.bridge.message.connect(self.on_midi)
        self.mapping={48:0,49:1,50:2,51:3,44:4,45:5,46:6,47:7};self.learning=None
        mapping=Path(__file__).with_name('pad_mapping.json')
        self.seat_mappings={};self.mapping_warning=None
        if mapping.exists():
            try:self.mapping,self.seat_mappings=read_maps(mapping)
            except (OSError,ValueError,KeyError) as error:self.mapping_warning=f'垫子映射未载入，使用默认映射：{error}'
        shell=QWidget();self.setCentralWidget(shell);outer=QVBoxLayout(shell)
        scroll=QScrollArea();scroll.setWidgetResizable(True);base=QWidget();scroll.setWidget(base);outer.addWidget(scroll);layout=QVBoxLayout(base)
        emergency=QPushButton('总停音 · Ctrl + 空格');emergency.setStyleSheet('background:#813844;color:white;padding:10px');emergency.clicked.connect(self.panic);outer.addWidget(emergency)
        self.panic_shortcut=QShortcut(QKeySequence('Ctrl+Space'),self);self.panic_shortcut.activated.connect(self.panic)
        title=QLabel('星群 / ORCHESTRA-138');title.setStyleSheet('font-size:26px;font-weight:700;color:#7de2d1');layout.addWidget(title)
        layout.addWidget(QLabel('六类乐手 · 人机接管 · 板端演出    |    音频由 FPGA 实时生成'))
        connection=QHBoxLayout();self.ports=QComboBox();self.ports.addItems([p.device for p in list_ports.comports()]);self.ports.setCurrentText('COM12')
        self.connect_button=QPushButton('连接 FPGA');self.connect_button.clicked.connect(self.connect_port)
        connection.addWidget(self.ports);connection.addWidget(self.connect_button)
        connection.addWidget(QLabel('演奏席'));self.seat=QSpinBox();self.seat.setRange(1,4);connection.addWidget(self.seat)
        self.midi_ports=QComboBox()
        if rtmidi:
            probe=rtmidi.MidiIn();self.midi_ports.addItems(probe.get_ports());del probe
        connection.addWidget(self.midi_ports,1);mb=QPushButton('连接 MIDI');mb.clicked.connect(self.connect_midi);connection.addWidget(mb)
        refresh=QPushButton('刷新设备');refresh.clicked.connect(self.refresh_devices);connection.addWidget(refresh)
        layout.addLayout(connection)
        transport=QHBoxLayout()
        for name,action in [('开始 / 重新开始演出',self.start_performance),('停止演出',lambda:self.enqueue(Event(5,flags=1))),('总停音 · 空格',self.panic)]:
            b=QPushButton(name);b.clicked.connect(action);transport.addWidget(b)
        layout.addLayout(transport)
        edit_button=QPushButton('编辑 / 保存 / 上传作品');edit_button.clicked.connect(self.open_editor);layout.addWidget(edit_button)
        stage_button=QPushButton('舞台实时状态 / 投屏');stage_button.clicked.connect(self.open_stage);layout.addWidget(stage_button)
        vision_button=QPushButton('视觉指挥 · 红色标记选择角色（实验）');vision_button.clicked.connect(self.open_vision);layout.addWidget(vision_button)
        tracks=QGroupBox('乐队成员与控制归属');grid=QGridLayout(tracks);self.track_labels=[]
        for i,name in enumerate(ROLES):
            row=i%8;col=(i//8)*4
            label=QLabel(f'{i+1:02d}  {name}');self.track_labels.append(label);grid.addWidget(label,row,col)
            for j,(text,cmd) in enumerate([('接管',0),('下小节归还',1),('静音',2)]):
                b=QPushButton(text)
                if cmd==2:
                    b.setCheckable(True);b.toggled.connect(lambda checked,p=i:self.command(p,2 if checked else 3))
                else:b.clicked.connect(lambda checked=False,p=i,c=cmd:self.command(p,c))
                grid.addWidget(b,row,col+j+1)
        layout.addWidget(tracks)
        controls=QHBoxLayout();self.part=QComboBox();self.part.addItems(ROLES);self.part.setCurrentIndex(6);controls.addWidget(QLabel('演奏角色'));controls.addWidget(self.part)
        self.root=QComboBox();self.root.addItems(['C','C♯','D','E♭','E','F','F♯','G','A♭','A','B♭','B']);controls.addWidget(QLabel('调'));controls.addWidget(self.root)
        self.mode=QComboBox();self.mode.addItems(['大调','自然小调','半音阶']);controls.addWidget(self.mode)
        self.octave=QSpinBox();self.octave.setRange(1,7);self.octave.setValue(4);controls.addWidget(QLabel('八度'));controls.addWidget(self.octave)
        controls.addWidget(QLabel('延迟发送'));self.wet=QSlider(Qt.Orientation.Horizontal);self.wet.setRange(0,127);self.wet.setValue(32);self.wet.valueChanged.connect(lambda v:self.enqueue(Event(7,parameter=v)));controls.addWidget(self.wet)
        layout.addLayout(controls)
        expression_row=QHBoxLayout();expression_row.addWidget(QLabel('当前角色表情'))
        self.expression=QSlider(Qt.Orientation.Horizontal);self.expression.setRange(0,127);self.expression.setValue(127);self.expression.valueChanged.connect(lambda n:self.parameter(0,n));expression_row.addWidget(self.expression)
        expression_row.addWidget(QLabel('弯音 ±2 半音'));self.bend=QSlider(Qt.Orientation.Horizontal);self.bend.setRange(0,16383);self.bend.setValue(8192);self.bend.valueChanged.connect(lambda n:self.parameter(1,n));self.bend.sliderReleased.connect(lambda:self.bend.setValue(8192));expression_row.addWidget(self.bend)
        self.vowel=QComboBox();self.vowel.addItems(['啊 / a','诶 / e','衣 / i','喔 / o','乌 / u']);self.vowel.currentIndexChanged.connect(lambda n:self.parameter(2,n));expression_row.addWidget(QLabel('新合唱音符'));expression_row.addWidget(self.vowel);layout.addLayout(expression_row)
        self.collaboration=QCheckBox('实时协作：主奏出现时和声收敛，贝斯跟随鼓的重音');self.collaboration.setChecked(True);self.collaboration.toggled.connect(lambda on:self.enqueue(Event(11,source=1,flags=3,parameter=int(on))));layout.addWidget(self.collaboration)
        patch=QPushButton('调整当前乐手的起音 / 衰减 / 持续 / 尾音');patch.clicked.connect(self.open_patch);layout.addWidget(patch)
        self.patch_button=patch
        calibrate=QPushButton('本地压力垫校准 / 保存');calibrate.clicked.connect(self.open_calibration);layout.addWidget(calibrate)
        self.root.currentIndexChanged.connect(lambda n:self.enqueue(Event(16,parameter=n)))
        tempo_row=QHBoxLayout();tempo_row.addWidget(QLabel('乐队速度 BPM'))
        self.tempo=QSpinBox();self.tempo.setRange(40,240);self.tempo.setValue(120);self.tempo.valueChanged.connect(lambda n:self.enqueue(Event(15,parameter=n)));tempo_row.addWidget(self.tempo);layout.addLayout(tempo_row)
        volume_row=QHBoxLayout();volume_row.addWidget(QLabel('主输出增益'))
        self.volume=QSlider(Qt.Orientation.Horizontal);self.volume.setRange(0,127);self.volume.setValue(96);self.volume.valueChanged.connect(lambda v:self.enqueue(Event(10,parameter=v)));volume_row.addWidget(self.volume);layout.addLayout(volume_row)
        pads=QHBoxLayout()
        for i,k in enumerate('ASDFGHJK'):
            b=QPushButton(f'{k}\n音阶 {i+1}');b.setMinimumHeight(74)
            b.pressed.connect(lambda n=i:self.press(208+n,self.scale_note(n),110));b.released.connect(lambda n=i:self.release(208+n));pads.addWidget(b)
        layout.addLayout(pads)
        learn=QPushButton('重新学习八个实体垫');learn.clicked.connect(self.learn);layout.addWidget(learn)
        self.info=QLabel('等待 FPGA 连接。V4 固件与旧 V2 演奏台不兼容。');layout.addWidget(self.info)
        self.metrics=QLabel('演出位置 —    活跃音符 —    样本计算 —    期限失误 —    削波 —');layout.addWidget(self.metrics)
        self.identity_label=QLabel('固件构建标识：尚未确认');layout.addWidget(self.identity_label)
        self.singer_label=QLabel('电子歌手：等待支持该功能的固件回传');layout.addWidget(self.singer_label)
        self.setStyleSheet('QWidget{background:#111c29;color:#e5edf5;font-size:13px} QGroupBox{border:1px solid #34465b;border-radius:8px;margin-top:16px;padding-top:16px} QPushButton{background:#233b50;border:1px solid #416078;border-radius:6px;padding:8px} QPushButton:hover{background:#345b70} QPushButton:checked{background:#964b53} QComboBox,QSpinBox{background:#233b50;padding:6px} QLabel{border:0}')
        self.setStyleSheet(self.styleSheet()+' QPushButton:disabled,QComboBox:disabled{background:#182635;color:#718092;border-color:#283848}')
        self.pump_timer=QTimer(self);self.pump_timer.timeout.connect(self.pump);self.pump_timer.start(5)
        self.beat_timer=QTimer(self);self.beat_timer.timeout.connect(self.heartbeat);self.beat_timer.start(100)
        self.part.currentIndexChanged.connect(lambda p:self.seat_parts.__setitem__(self.source(),p))
        self.part.currentIndexChanged.connect(self.refresh_role_controls)
        self.seat.valueChanged.connect(lambda s:self.part.setCurrentIndex(self.seat_parts[s]))
        QApplication.instance().applicationStateChanged.connect(self.focus_state)
        if self.mapping_warning:self.info.setText(self.mapping_warning)
    def source(self):return self.seat.value()
    def open_vision(self):
        from vision_control import VisionControl
        if self.vision_control is None:self.vision_control=VisionControl(self)
        self.vision_control.show();self.vision_control.raise_()
    def open_stage(self):
        if self.stage_view is None:self.stage_view=StageView(self,ROLES)
        self.stage_view.show();self.stage_view.raise_();self.stage_view.refresh()
    def capture_performance(self):
        return dict(version=1,tempo=self.tempo.value(),root=self.root.currentIndex(),mode=self.mode.currentIndex(),octave=self.octave.value(),master=self.volume.value(),wet=self.wet.value(),collaboration=self.collaboration.isChecked(),seat_parts=self.seat_parts,pad_mapping=dict(self.mapping),seat_pad_mappings={k:dict(v) for k,v in self.seat_mappings.items()},patches=self.patch_values,pad_calibration=self.pad_calibration)
    def restore_performance(self,p):
        if not p:return
        from calibration_model import normalize
        default_mapping=normalize_mapping(p.get('pad_mapping',self.mapping))
        seat_mappings=normalize_seats(p.get('seat_pad_mappings',{}))
        self.release_all();self.clear_midi_holds()
        self.pad_calibration=normalize(p.get('pad_calibration',{}))
        for widget,key in [(self.tempo,'tempo'),(self.octave,'octave'),(self.volume,'master'),(self.wet,'wet')]:
            if key in p:
                blocker=QSignalBlocker(widget);widget.setValue(int(p[key]));del blocker
        for widget,key in [(self.root,'root'),(self.mode,'mode')]:
            if key in p:
                blocker=QSignalBlocker(widget);widget.setCurrentIndex(int(p[key]));del blocker
        blocker=QSignalBlocker(self.collaboration);self.collaboration.setChecked(bool(p.get('collaboration',True)));del blocker
        self.patch_values={int(k):{int(a):int(v) for a,v in d.items()} for k,d in p.get('patches',{}).items()}
        self.mapping=default_mapping;self.seat_mappings=seat_mappings
        self.seat_parts={int(k):int(v) for k,v in p.get('seat_parts',self.seat_parts).items()};self.part.setCurrentIndex(self.seat_parts[self.source()])
    def start_performance(self):
        if self.await_upload:self.info.setText('请等待曲谱校验完成后再开始');return
        self.release_all();self.enqueue(Event(5,flags=1))
        for kind,value in [(7,self.wet.value()),(10,self.volume.value()),(15,self.tempo.value()),(16,self.root.currentIndex())]:self.enqueue(Event(kind,parameter=value))
        self.enqueue(Event(11,flags=3,parameter=int(self.collaboration.isChecked())))
        for part,params in self.patch_values.items():
            for parameter,value in params.items():self.enqueue(Event(11,part=part,flags=parameter,parameter=value))
        self.enqueue(Event(5))
    def open_calibration(self):
        from calibration_editor import CalibrationEditor
        if not hasattr(self,'calibration_editor'):self.calibration_editor=CalibrationEditor(self)
        self.calibration_editor.load_channel();self.calibration_editor.show();self.calibration_editor.raise_()
    def open_patch(self):
        if not hasattr(self,'patch_editor'):self.patch_editor=PatchEditor(self)
        self.patch_editor.show();self.patch_editor.raise_()
    def open_editor(self):
        if not self.editor:self.editor=ScoreEditor(self);self.editor.upload.connect(self.upload_score)
        self.editor.show();self.editor.raise_()
    def upload_score(self,score):
        if not self.port:self.info.setText('请先连接 V4 FPGA');return
        try:validate_target(score,self.board_identity.get('features',0) if self.board_identity else None)
        except ValueError as e:self.info.setText('未上传：'+str(e));return
        self.upload_generator=iter(upload_events(score));self.await_upload=True;self.upload_error_baseline=self.upload_errors
        self.info.setText('正在上传事件曲谱；当前演出继续使用原曲谱')
    def refresh_devices(self):
        try:
            selected=self.ports.currentText();self.ports.clear();self.ports.addItems([p.device for p in list_ports.comports()])
            if self.ports.findText(selected)>=0:self.ports.setCurrentText(selected)
            selected=self.midi_ports.currentText();self.midi_ports.clear()
            if rtmidi:
                probe=rtmidi.MidiIn();self.midi_ports.addItems(probe.get_ports());del probe
            if self.midi_ports.findText(selected)>=0:self.midi_ports.setCurrentText(selected)
            self.info.setText(f'已刷新：{self.ports.count()} 个串口，{self.midi_ports.count()} 个 MIDI 输入。已有连接保持不变。')
        except Exception as e:self.info.setText('刷新设备失败：'+str(e))
    def connect_port(self):
        if self.port:
            self.disconnect_port();return
        self.stage_state.reset();self.last_rx=0;self.board_identity=None
        self.singer_snapshot=None;self.singer_received=0;self.part.setItemText(15,ROLES[15]);self.refresh_singer()
        self.refresh_role_controls()
        try:
            self.port=serial.Serial(self.ports.currentText(),1000000,timeout=0,write_timeout=.05);self.decoder=Decoder();self.states.clear();self.queue.clear();self.connect_button.setText('断开连接');self.info.setText('串口已打开，等待 V4 回传确认…')
            self.identity_label.setText('固件构建标识：等待板端回传');self.enqueue(Event(18));self.identity_requested=time.monotonic()
        except Exception as e:self.info.setText(str(e))
    def disconnect_port(self,release=True):
        # Retire the entire host session before any I/O. In particular, never
        # resume a half-upload or process stale telemetry on a new connection.
        port,self.port=self.port,None
        self.upload_generator=None;self.await_upload=False
        self.queue.clear();self.held.clear();self.states.clear();self.clear_midi_holds()
        self.decoder=Decoder();self.stage_state.reset();self.last_rx=0;self.board_identity=None
        self.singer_snapshot=None;self.singer_received=0
        self.part.setItemText(15,ROLES[15]);self.refresh_role_controls();self.refresh_singer()
        self.connect_button.setText('连接 FPGA');self.identity_label.setText('固件构建标识：未连接')
        error=None
        if port:
            try:
                if release:
                    # Four guarded packets fit the normal batch. Discard old
                    # parameter traffic; machine source 0 continues playing.
                    for source in range(1,5):
                        raw=Event(2,source=source).encode_uart()
                        if port.write(raw)!=len(raw):raise IOError('串口写入不完整')
            except Exception as e:error=str(e)
            finally:
                try:port.close()
                except Exception as e:error=str(e)
        self.info.setText('已断开；旧上传已取消，需要重新上传。'+(' 释放未送达，板端租约负责回收：'+error if error else ''))
    def enqueue(self,event,front=False):
        if not self.port:return
        if len(self.queue)>=256:self.queue.clear();self.queue.append(Event(127));self.held.clear();self.clear_midi_holds();self.info.setText('控制队列过载，已请求停音');return
        if event.kind in (7,10,15,16):self.queue=deque(e for e in self.queue if e.kind!=event.kind)
        if event.kind==11:self.queue=deque(e for e in self.queue if not(e.kind==11 and e.part==event.part and e.source==event.source and e.flags==event.flags))
        (self.queue.appendleft if front else self.queue.append)(event)
    def command(self,part,cmd):
        self.part.setCurrentIndex(part);self.enqueue(Event(4,source=self.source(),part=part,flags=cmd))
    def parameter(self,parameter,value,source=None):
        source=self.source() if source is None else source;part=self.seat_parts[source];state=self.states.get(part)
        if part==15 and self.board_identity and self.board_identity.get('features',0)&32 and parameter!=0:return
        if source!=1 and(not state or state['owner']!=source):return
        self.patch_values.setdefault(part,{})[parameter]=value
        self.enqueue(Event(11,source=source,part=part,flags=parameter,parameter=value,epoch=state['epoch'] if state else 0))
    def scale_note(self,i):
        scale=([0,2,4,5,7,9,11,12],[0,2,3,5,7,8,10,12],list(range(8)))[self.mode.currentIndex()]
        return min(127,(self.octave.value()+1)*12+self.root.currentIndex()+scale[i])
    def press(self,contact,note,velocity,source=None,part=None):
        source=self.source() if source is None else source;part=self.seat_parts[source] if part is None else part
        key=(source,contact)
        if key in self.held or not self.port:return
        state=self.states.get(part)
        if state and state['owner'] not in (0,source):self.info.setText(f'该轨由演奏席 {state["owner"]} 控制');return
        self.held[key]=dict(part=part,source=source,note=note,velocity=min(127,max(1,velocity)),serial=self.next_serial,sent=False,queued=False,epoch=None)
        self.next_serial+=1
        # Taking an already-owned track cancels a queued next-bar return.
        self.enqueue(Event(4,source=source,part=part,flags=0))
        if state and state['owner']==source:self.flush_notes(part,state)
    def flush_notes(self,part,state):
        for (source,contact),n in self.held.items():
            if n['part']!=part:continue
            if state['owner']==0:
                if not any(e.kind==4 and e.part==part and e.source==source and e.flags==0 for e in self.queue):self.enqueue(Event(4,source=source,part=part,flags=0))
                continue
            if n['source']==state['owner'] and n['epoch'] is not None and n['epoch']!=state['epoch']:
                self.queue=deque(e for e in self.queue if not(e.kind==0 and e.serial==n['serial'] and e.source==source))
                n.update(queued=False,sent=False)
            if n['source']==state['owner'] and not n['queued']:
                n.update(queued=True,epoch=state['epoch']);self.enqueue(Event(0,source=n['source'],part=part,contact=contact,note=n['note'],velocity=n['velocity'],epoch=n['epoch'],serial=n['serial']))
    def release(self,contact,source=None):
        if source is None:
            for s,c in list(self.held):
                if c==contact:self.release(c,s)
            return
        n=self.held.pop((source,contact),None)
        if not n:return
        self.queue=deque(e for e in self.queue if not(e.kind==0 and e.serial==n['serial'] and e.source==n['source']))
        if n['sent']:self.enqueue(Event(1,source=n['source'],part=n['part'],contact=contact,note=n['note'],velocity=0,epoch=n['epoch'],serial=n['serial']),True)
        if not any(h['source']==source and h['part']==n['part'] for h in self.held.values()):
            self.enqueue(Event(4,source=source,part=n['part'],flags=1))
    def release_all(self,source=None):
        for s,c in list(self.held):
            if source is None or s==source:self.release(c,s)
        self.clear_midi_holds(source)
    def clear_midi_holds(self,source=None):
        self.midi_contacts={k:v for k,v in self.midi_contacts.items() if source is not None and k[0]!=source}
        self.midi_sustain={k for k in self.midi_sustain if source is not None and k[0]!=source}
        self.midi_deferred={k for k in self.midi_deferred if source is not None and k[0]!=source}
    def sustain_pedal(self,source,channel,down):
        key=(source,channel)
        if down:self.midi_sustain.add(key);return
        self.midi_sustain.discard(key)
        for identity in sorted(self.midi_deferred):
            if identity[:2]!=key:continue
            self.midi_deferred.discard(identity)
            contact=self.midi_contacts.pop(identity,None)
            if contact is not None:self.release(contact,source)
    def focus_state(self,state):
        if state!=Qt.ApplicationState.ApplicationActive:
            for s,c in list(self.held):
                if c>=208:self.release(c,s)
    def panic(self):
        self.held.clear();self.clear_midi_holds();self.queue.clear();self.upload_generator=None;self.await_upload=False;self.enqueue(Event(127),True)
    def heartbeat(self):
        for s,(device,name) in list(self.midis.items()):
            try:present=name in device.get_ports() and device.is_port_open()
            except Exception:present=False
            if not present:self.disconnect_midi(s)
        if self.port:
            if self.board_identity is None and time.monotonic()-self.identity_requested>=.5 and len(self.queue)<8:
                self.enqueue(Event(18));self.identity_requested=time.monotonic()
            sources={self.source()}|set(self.midis)|{n['source'] for n in self.held.values()}
            if self.await_upload:sources.add(1)
            for source in sources:
                parts={n['part'] for n in self.held.values() if n['source']==source} or {self.seat_parts[source]}
                for part in parts:self.enqueue(Event(14 if self.await_upload and source==1 else 6,source=source,part=part))
            # Bounded observer traffic, using an already refreshed source. Never
            # refresh another performer's lease, and yield to uploads/backlogs.
            if self.board_identity is not None and self.stage_view is not None and self.stage_view.isVisible() and not self.await_upload and not self.upload_generator and len(self.queue)<8:
                for _ in range(2):
                    self.enqueue(Event(6,source=self.source(),part=self.stage_poll_part))
                    self.stage_poll_part=(self.stage_poll_part+1)%16
            if self.last_rx and time.monotonic()-self.last_rx>1:self.info.setText('未收到近期 V4 回传；请检查固件及串口')
            if self.board_identity and self.board_identity.get('features',0)&32 and not self.await_upload and not self.upload_generator and len(self.queue)<8:
                self.enqueue(Event(19,source=self.source(),part=15))
        self.refresh_singer()
    def role_name(self,part):
        return '电子歌手' if part==15 and self.board_identity and self.board_identity.get('features',0)&32 else ROLES[part]
    def refresh_role_controls(self,*_):
        singer=self.part.currentIndex()==15 and self.board_identity and self.board_identity.get('features',0)&32
        for control in (self.bend,self.vowel,self.patch_button):
            control.setEnabled(not singer)
            control.setToolTip('当前电子歌手支持音符、力度与表情；此项尚未支持。' if singer else '')
    def refresh_singer(self):
        s=self.singer_snapshot
        live=self.port is not None and self.board_identity is not None and bool(self.board_identity.get('features',0)&32) and s is not None and 0<=time.monotonic()-self.singer_received<=2.5
        self.singer_label.setText((f'电子歌手 · '+(f'保持音符 {s["note"]}' if s['gate'] else '已松键（尾音未测）')+
            f' · 丢帧 {s["dropped"]} · 旧释放 {s["stale_off"]} · DAC 丢帧/欠载 {s["dac_dropped"]}/{s["dac_underruns"]} · 非响度测量')
            if live else '电子歌手：无有效回传 / 已过期')
    def pump(self):
        if not self.port:return
        try:
            for _ in range(UART_BATCH_SIZE):
                if self.queue:e=self.queue.popleft()
                elif self.upload_generator:
                    try:e=next(self.upload_generator)
                    except StopIteration:self.upload_generator=None;break
                else:break
                raw=e.encode_uart()
                if self.port.write(raw)!=len(raw):raise IOError('串口写入不完整')
                if e.kind==0:
                    for n in self.held.values():
                        if n['serial']==e.serial and n['source']==e.source:n['sent']=True
            for raw in self.decoder.feed(self.port.read(self.port.in_waiting)):
                if raw[1]==161:
                    build=int.from_bytes(raw[4:8],'little');capacity=int.from_bytes(raw[8:12],'little');fs=int.from_bytes(raw[12:16],'little');self.last_rx=time.monotonic()
                    features=int.from_bytes(raw[20:24],'little')
                    self.board_identity=dict(build_id=build,capacity=capacity,nominal_sample_rate=fs,features=features)
                    self.part.setItemText(15,self.role_name(15))
                    if 15 not in self.states:self.track_labels[15].setText(f'16  {self.role_name(15)}')
                    self.refresh_role_controls()
                    self.refresh_singer()
                    profile='实验固件 · ' if features&0x80000000 else ''
                    self.identity_label.setText(f'{profile}板端构建 {build:08x} · 音符槽 {capacity} · 标称采样率 {fs} Hz（采样率仍需仪器实测）');continue
                if raw[1]==162:
                    if self.board_identity and self.board_identity.get('features',0)&32:
                        self.singer_snapshot=singer_status(raw);self.singer_received=time.monotonic();self.last_rx=self.singer_received;self.refresh_singer()
                    continue
                if raw[1]==160:
                    self.last_rx=time.monotonic()
                    self.upload_errors=int.from_bytes(raw[12:16],'little');entries=int.from_bytes(raw[4:8],'little')
                    if self.await_upload and self.upload_errors>self.upload_error_baseline:
                        self.upload_generator=None;self.await_upload=False;self.info.setText('曲谱上传未通过验证，原曲谱保持可用')
                    elif self.await_upload and raw[2]&2:
                        self.await_upload=False;self.info.setText('曲谱 CRC 校验通过；下次停止并开始演出时启用，断电仍回到固件默认曲谱')
                    elif self.await_upload:self.info.setText(f'曲谱上传中：已校验 {entries} 条事件')
                    continue
                if raw[1] not in (128,129):continue
                s=status(raw);self.states[s['part']]=s;self.last_rx=time.monotonic();self.flush_notes(s['part'],s)
                self.stage_state.update(s,self.last_rx)
                self.track_labels[s['part']].setText(f'{s["part"]+1:02d} {self.role_name(s["part"])} · '+('机器' if not s['owner'] else f'席{s["owner"]}'))
                if not self.await_upload:self.info.setText('FPGA V4 已确认 · '+('乐队演出中' if s['playing'] else '自由演奏'))
                voice_label='乐队音符（不含独立歌手）' if self.board_identity and self.board_identity.get('features',0)&32 else '活跃音符'
                self.metrics.setText(f'演出位置 {s["song_sample"]/48000:.1f}s    {voice_label} {s["voices"]}    样本计算 {s["cycles"]} clocks    期限失误 {s["deadline_miss"]}    削波 {s["clips"]}    拒绝 {s["rejected"]}    回传 CRC 错误 {self.decoder.bad_crc}')
        except Exception as e:
            self.disconnect_port(release=False);self.info.setText(f'连接异常：{e}；旧上传已取消，板端租约负责回收。')
    def disconnect_midi(self,source):
        # Invalidate queued Qt callbacks before touching the native device.
        self.midi_generations[source]=self.midi_generations.get(source,0)+1
        bound=self.midis.pop(source,None)
        self.release_all(source);self.clear_midi_holds(source)
        self.enqueue(Event(2,source=source))
        parts={p for p,state in self.states.items() if state.get('owner')==source}
        parts.add(self.seat_parts[source])
        for part in parts:self.enqueue(Event(4,source=source,part=part,flags=1))
        if self.learning is not None and self.learning_source==source:self.learning=None
        if bound:
            try:bound[0].cancel_callback()
            except Exception:pass
            try:bound[0].close_port()
            except Exception:pass
    def connect_midi(self):
        if not rtmidi:return
        source=self.source();name=self.midi_ports.currentText();index=self.midi_ports.currentIndex()
        if not name or index<0:self.info.setText('请刷新并选择 MIDI 输入');return
        if any(s!=source and n==name for s,(d,n) in self.midis.items()):
            self.info.setText('该 MIDI 输入已绑定其他演奏席');return
        if source in self.midis and self.midis[source][1]==name:
            self.info.setText(f'演奏席 {source} 已连接该 MIDI 输入');return
        device=None
        try:
            device=rtmidi.MidiIn();ports=device.get_ports()
            if index>=len(ports) or ports[index]!=name or ports.count(name)!=1:
                raise ValueError('MIDI 设备列表已变化或名称重复，请刷新并检查设备名称')
            # Keep the old seat intact if opening its replacement fails.
            device.open_port(index)
            if source in self.midis:self.disconnect_midi(source)
            generation=self.midi_generations.get(source,0)+1
            self.midi_generations[source]=generation
            self.midis[source]=(device,name)
            device.set_callback(lambda event,data=None,s=source,g=generation:self.bridge.message.emit((s,g,list(event[0]))))
            self.info.setText(f'MIDI 已连接到演奏席 {source}')
        except Exception as e:
            if device is not None:
                if source in self.midis and self.midis[source][0] is device:self.disconnect_midi(source)
                else:
                    try:device.close_port()
                    except Exception:pass
            self.info.setText(str(e))
    def learn(self):
        self.learning_source=self.source();self.release_all(self.learning_source)
        self.midi_contacts={k:v for k,v in self.midi_contacts.items() if k[0]!=self.learning_source}
        self.learning=[];self.info.setText('按顺序敲当前席位的八个不同垫；学习时不发声')
    def on_midi(self,event):
        if len(event)==3:
            source,generation,msg=event
            if source not in self.midis or self.midi_generations.get(source)!=generation:return
        else:source,msg=event # In-process test/virtual-seat injection.
        if source not in self.seat_parts or len(msg)<2:return
        kind=msg[0]&240;note=msg[1];velocity=msg[2] if len(msg)>2 else 0
        if kind==208:self.parameter(0,note,source);return
        if len(msg)<3:return
        if self.learning is not None and source==self.learning_source:
            if kind==144 and velocity and note not in self.learning:
                self.learning.append(note)
                if len(self.learning)==8:
                    self.seat_mappings[source]={n:i for i,n in enumerate(self.learning)};self.learning=None
                    try:
                        save_maps(Path(__file__).with_name('pad_mapping.json'),self.mapping,self.seat_mappings)
                        self.info.setText(f'演奏席 {source} 的八垫映射已保存')
                    except OSError as error:self.info.setText(f'席 {source} 映射本次有效，保存失败：{error}')
            return
        mapping=self.seat_mappings.get(source,self.mapping)
        identity=(source,msg[0]&15,note)
        if kind==144 and velocity:
            if identity in self.midi_deferred:
                # Retrigger with a new serial; retire the old sustained note
                # before reusing its contact so an old release cannot kill it.
                self.midi_deferred.discard(identity)
                contact=self.midi_contacts.pop(identity,None)
                if contact is not None:self.release(contact,source)
            if identity not in self.midi_contacts:
                used={c for (s,ch,n),c in self.midi_contacts.items() if s==source};free=next((c for c in range(192) if c not in used),None)
                if free is None:self.info.setText('该席位触点容量已满');return
                self.midi_contacts[identity]=free
            contact=self.midi_contacts[identity]
            part=self.seat_parts[source]
            if part==0:
                # The kick track doubles as the three-drum kit entry. Other
                # selected roles retain their ordinary pitch mapping.
                part={36:0,38:1,42:2,46:2}.get(note,(0,1,2,0,1,2,1,2)[mapping[note]] if note in mapping else 0)
                pitch=(36,38,42)[part]
            else:pitch=self.scale_note(mapping[note]) if note in mapping else note
            self.press(contact,pitch,round(velocity*1.5),source,part)
        elif kind==128 or(kind==144 and not velocity):
            if identity[:2] in self.midi_sustain and identity in self.midi_contacts:
                self.midi_deferred.add(identity);return
            contact=self.midi_contacts.pop(identity,None)
            if contact is not None:self.release(contact,source)
        elif kind==176 and note==64:self.sustain_pedal(source,msg[0]&15,velocity>=64)
        elif kind==176 and note in (120,123):
            self.release_all(source);self.midi_contacts={k:v for k,v in self.midi_contacts.items() if k[0]!=source}
        elif kind==224:self.parameter(1,note|(velocity<<7),source)
        elif kind==176 and note==11:self.parameter(0,velocity,source)
        elif kind==176 and note==74:self.parameter(2,min(4,velocity*5//128),source)
    def keyPressEvent(self,e):
        if e.isAutoRepeat():return
        text=e.text().upper()
        if e.key()==Qt.Key.Key_Space:self.panic()
        elif text in 'ASDFGHJK' and len(text)==1:i='ASDFGHJK'.index(text);self.press(208+i,self.scale_note(i),110)
        else:super().keyPressEvent(e)
    def keyReleaseEvent(self,e):
        if not e.isAutoRepeat() and e.text().upper() in 'ASDFGHJK' and len(e.text())==1:self.release(208+'ASDFGHJK'.index(e.text().upper()))
        else:super().keyReleaseEvent(e)
    def closeEvent(self,e):
        if self.vision_control is not None:self.vision_control.close()
        if self.stage_view is not None:self.stage_view.close()
        self.disconnect_port()
        for source in list(self.midis):self.disconnect_midi(source)
        e.accept()
if __name__=='__main__':
    app=QApplication(sys.argv);window=Desk();window.show();sys.exit(app.exec())
