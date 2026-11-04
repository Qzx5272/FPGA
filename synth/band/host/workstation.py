"""Workstation tools: actual presets, control takes, mixer, library and evidence."""
import copy
import json
import time
from dataclasses import replace
from pathlib import Path
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QTabWidget,QWidget,
    QLabel,QPushButton,QComboBox,QFileDialog,QMessageBox,QSlider,QGridLayout,
    QTableWidget,QTableWidgetItem,QHeaderView,QDoubleSpinBox,QCheckBox,QSpinBox)
from protocol import Event
from performance_recording import Recorder, Playback, load, save
from instruments import PRESETS, envelope, supported

BAND=Path(__file__).resolve().parents[1]


def button(layout,text,callback):
    b=QPushButton(text);b.clicked.connect(callback);layout.addWidget(b);return b


class Workstation(QDialog):
    def __init__(self,desk):
        super().__init__(desk)
        self.desk=desk;self.setWindowTitle('星群 · 音色 / 录制 / 混音 / 曲库 / 指标')
        self.resize(1100,760);self.recorder=Recorder();self.player=Playback()
        self.take=None;self.replay_contacts={};self.muted={};self.solo=None;self.filename=None
        self.pending_return=None;self.replay_wait=None;self.replay_parts={}
        self.last_library_poll=0
        layout=QVBoxLayout(self);self.tabs=QTabWidget();layout.addWidget(self.tabs)
        self.status=QLabel('选择音色或录制演奏事件；声音由 FPGA 生成。');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.build_presets();self.build_recording();self.build_mixer();self.build_library();self.build_metrics();self.sync_mixer()
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(10)

    def page(self,name):
        widget=QWidget();self.tabs.addTab(widget,name);return QVBoxLayout(widget)

    def error(self,error):self.status.setText(str(error))

    def build_presets(self):
        box=self.page('音色库')
        box.addWidget(QLabel('选择算法声部和包络；扩展音色要求新版固件。按 ASDFGHJK 或使用16垫试听。'))
        self.family=QComboBox();self.family.addItems(['全部']+sorted({p['family'] for p in PRESETS}));box.addWidget(self.family)
        self.presets=QComboBox();box.addWidget(self.presets)
        self.family.currentTextChanged.connect(self.filter_presets);self.filter_presets()
        button(box,'应用音色到当前演奏席',self.apply_preset)
        row=QHBoxLayout();box.addLayout(row)
        button(row,'试听 C4',self.audition)
        button(row,'停止试听',lambda:self.desk.release(207,self.desk.source()))
        button(row,'编辑 ADSR',self.desk.open_patch)
        button(box,'保存当前参数为用户预设',self.save_preset)
        button(box,'装载用户预设',self.load_preset)
        box.addWidget(QLabel('拨弦/笛/钟/木琴等是参数合成仿声；不标作已验证的物理声学模型。'))
        self.pad_velocity=QSpinBox();self.pad_velocity.setRange(1,127);self.pad_velocity.setValue(96)
        self.pad_velocity.setPrefix('屏幕垫力度 ');box.addWidget(self.pad_velocity)
        pads=QGridLayout();box.addLayout(pads)
        for i in range(16):
            pad=QPushButton(f'{i+1:02d}');pad.setMinimumHeight(58)
            pad.pressed.connect(lambda n=i:self.desk.press(176+n,self.desk.scale_note(n),self.pad_velocity.value()))
            pad.released.connect(lambda n=i:self.desk.release(176+n))
            pads.addWidget(pad,i//4,i%4)
        box.addStretch()

    def filter_presets(self,*_):
        self.presets.clear()
        for p in PRESETS:
            if self.family.currentText() in ('全部',p['family']):
                self.presets.addItem(p['name']+' / '+p['family'],p['id'])

    def apply_preset(self):
        preset=next(p for p in PRESETS if p['id']==self.presets.currentData())
        if not supported(preset,self.desk.board_identity):
            self.error('当前固件未声明扩展音色能力，未发送。请使用新版工作站固件。');return
        independent=bool(self.desk.board_identity and self.desk.board_identity.get('features',0)&512)
        part=self.desk.part.currentIndex() if independent and self.desk.part.currentIndex()<15 else preset['part']
        if not independent:self.desk.release_all(self.desk.source())
        self.desk.part.setCurrentIndex(part)
        if independent:
            self.desk.patch_values.setdefault(part,{})[8]=preset['part']
            self.desk.enqueue(Event(11,source=1,part=part,flags=8,parameter=preset['part']))
        for parameter,value in envelope(*preset['adsr']).items():
            self.desk.patch_values.setdefault(part,{})[parameter]=value
            self.desk.enqueue(Event(11,source=1,part=part,flags=parameter,parameter=value))
        self.status.setText('已选择 '+preset['name']+('；保留声部，新起音使用新算法。' if independent else '；板载固件通过算法声部切换，保存作品可保留。'))

    def audition(self):
        self.apply_preset()
        preset=next(p for p in PRESETS if p['id']==self.presets.currentData())
        if not supported(preset,self.desk.board_identity):return
        source=self.desk.source();self.desk.press(207,60,95)
        QTimer.singleShot(650,lambda:self.desk.release(207,source))

    def save_preset(self):
        path,_=QFileDialog.getSaveFileName(self,'保存用户预设','用户预设.json','JSON (*.json)')
        if not path:return
        part=self.desk.part.currentIndex()
        data=dict(format='starcluster-preset-1',part=part,parameters=self.desk.patch_values.get(part,{}))
        try:
            from storage import atomic_json
            atomic_json(path,data);self.status.setText('预设已保存')
        except Exception as exc:self.error(exc)

    def load_preset(self):
        path,_=QFileDialog.getOpenFileName(self,'装载用户预设','','JSON (*.json)')
        if not path:return
        try:
            data=json.loads(Path(path).read_text(encoding='utf-8'));part=data['part']
            if data.get('format')!='starcluster-preset-1' or type(part)is not int or not 0<=part<15:raise ValueError('预设格式非法')
            if part>=8 and not supported(dict(extended=True),self.desk.board_identity):raise ValueError('固件不支持扩展音色')
            values={int(k):v for k,v in data['parameters'].items()}
            limits={0:127,1:16383,2:4,4:16383,5:15,6:16383,7:15,8:14,9:127}
            if any(k in (8,9) for k in values) and not(self.desk.board_identity and self.desk.board_identity.get('features',0)&512):raise ValueError('此预设需要逐声部音色/声像扩展固件')
            if any(k not in limits or type(v)is not int or not 0<=v<=limits[k] for k,v in values.items()):raise ValueError('预设参数非法')
            self.desk.release_all(self.desk.source());self.desk.part.setCurrentIndex(part)
            for k,v in values.items():
                self.desk.patch_values.setdefault(part,{})[k]=v
                self.desk.enqueue(Event(11,source=1,part=part,flags=k,parameter=v))
            self.status.setText('预设已装载')
        except Exception as exc:self.error(exc)

    def build_recording(self):
        box=self.page('事件录制 / 重放')
        text=QLabel('记录音符、力度、音色参数与时序并可重放；不录制WAV。扩展固件能回传本地控件与外设事件。若板端报告事件丢失，将自动停止并标记录制不完整。')
        text.setWordWrap(True);box.addWidget(text)
        row=QHBoxLayout();box.addLayout(row)
        button(row,'● 开始录制',self.start_recording);button(row,'■ 结束录制',self.stop_recording)
        button(row,'保存录制',self.save_take);button(row,'打开录制',self.open_take)
        self.record_info=QLabel('尚无录制');box.addWidget(self.record_info)
        row=QHBoxLayout();box.addLayout(row)
        self.speed=QDoubleSpinBox();self.speed.setRange(.25,4);self.speed.setSingleStep(.25);self.speed.setValue(1);self.speed.setSuffix(' ×');row.addWidget(self.speed)
        button(row,'▶ 重放',self.start_playback);button(row,'■ 停止重放',self.stop_playback)
        self.loop=QCheckBox('循环重放');box.addWidget(self.loop)
        box.addWidget(QLabel('重放会申请新的声部授权；现场键盘/MIDI在重放期间暂停，避免同一触点冲突。可随时总停音。'))
        box.addStretch()

    def start_recording(self):
        if not self.desk.port:self.error('先连接 FPGA 再录制');return
        if self.desk.capture_uncertain:self.error('板端事件历史发生丢失，请先总停音再开始新录制。');return
        if self.recorder.active:self.error('已经在录制');return
        self.stop_playback()
        held=[Event(0,source=n['source'],part=n['part'],contact=c,note=n['note'],velocity=n['velocity'],epoch=n['epoch'] or 0,serial=n['serial'])
              for (s,c),n in self.desk.held.items() if n['sent']]
        held.extend(self.desk.captured_held.values())
        self.recorder.start(time.monotonic(),self.desk.capture_performance(),self.desk.board_identity,held)
        self.status.setText('正在录制；结束时会补齐尚未释放的音符。')

    def stop_recording(self):
        if self.recorder.active:
            self.take=self.recorder.stop(time.monotonic());self.filename=None
            self.status.setText('录制已结束，可保存或重放。')

    def capture(self,event):
        if self.player.active:return
        try:self.recorder.capture(event,time.monotonic())
        except Exception as exc:self.take=self.recorder.take;self.error(exc)

    def capture_from_board(self,event,ticks):
        if self.player.active:return
        try:self.recorder.capture_hardware(event,ticks,time.monotonic())
        except Exception as exc:self.stop_recording();self.error(exc)

    def capture_failure(self,count):
        if self.recorder.active:
            self.recorder.take['capture_incomplete']=True
            self.stop_recording()
        self.error(f'板端事件回传累计丢失 {count} 条；录制已停止，不能当作完整演奏。')

    @staticmethod
    def replay_source(source):
        if 1<=source<=4:return source
        if 64<=source<255:return 4
        raise ValueError('录制含无法映射的演奏席位')

    def save_take(self):
        self.stop_recording()
        if self.take is None:self.error('没有录制内容');return
        path,_=QFileDialog.getSaveFileName(self,'保存演奏事件',self.filename or '演奏录制.take.json','JSON (*.json)')
        if path:
            try:save(path,self.take);self.filename=path;self.status.setText('录制已保存：'+path)
            except Exception as exc:self.error(exc)

    def open_take(self):
        path,_=QFileDialog.getOpenFileName(self,'打开演奏事件','','JSON (*.json)')
        if path:
            try:
                take=load(path);self.stop_playback();self.stop_recording();self.take=take;self.filename=path
                self.status.setText('已打开录制；尚未开始重放')
            except Exception as exc:self.error(exc)

    def start_playback(self):
        if self.recorder.active:self.error('先结束录制');return
        if not self.desk.port or self.desk.board_identity is None:self.error('先连接并等待固件身份');return
        if self.take is None:self.error('请先录制或打开文件');return
        if self.take.get('capture_incomplete'):self.error('此录制标记为事件不完整，拒绝作为完整演奏自动重放。');return
        try:
            self.stop_playback();self.desk.panic()
            self.desk.restore_performance(self.take.get('performance',{}))
            if self.desk.apply_performance_controls() is False:raise ValueError('当前固件无法重放此场景')
            requirements={}
            for item in self.take['events']:
                e=item['event']
                if e['kind']!=0:continue
                part,source=e['part'],self.replay_source(e['source'])
                if part in requirements and requirements[part]!=source:raise ValueError('同一声部跨席位录制暂不支持自动重放')
                requirements[part]=source
            now=time.monotonic()
            self.replay_contacts={};self.replay_parts=requirements;self.replay_wait=(now,requirements)
            for part,source in requirements.items():self.desk.enqueue(Event(4,source=source,part=part))
            self.status.setText('事件重放中；使用新授权，桌面调度不作为硬件延迟证明。')
        except Exception as exc:self.stop_playback();self.error(exc)

    def stop_playback(self):
        if self.player.active or self.replay_contacts:
            self.player.active=False
            for (s,p,c,serial),contact in list(self.replay_contacts.items()):self.desk.release(contact,s)
            self.replay_contacts.clear()
        for part,source in self.replay_parts.items():self.desk.enqueue(Event(4,source=source,part=part,flags=1))
        self.replay_parts={};self.pending_return=None;self.replay_wait=None

    def replay(self,data):
        e=Event(**data)
        e=replace(e,source=self.replay_source(e.source))
        if e.kind in (0,1):
            key=(e.source,e.part,e.contact,e.serial)
            if e.kind==0:
                if not 1<=e.source<=4:raise ValueError('录制含非上位机席位，需板端重放支持')
                used={v for k,v in self.replay_contacts.items() if k[0]==e.source}
                contact=next((i for i in range(192) if i not in used),None)
                if contact is None:raise ValueError('回放并发触点超过192')
                self.replay_contacts[key]=contact
                self.desk.press(contact,e.note,e.velocity,e.source,e.part)
            else:
                contact=self.replay_contacts.pop(key,None)
                if contact is not None:self.desk.release(contact,e.source)
        elif e.kind==11:
            state=self.desk.states.get(e.part,{})
            if e.flags!=3:self.desk.patch_values.setdefault(e.part,{})[e.flags]=e.parameter
            self.desk.enqueue(Event(11,source=1,part=e.part,flags=e.flags,parameter=e.parameter,epoch=state.get('epoch',0)))
        elif e.kind==127:
            self.desk.held.clear();self.replay_contacts.clear();self.desk.queue.clear();self.desk.enqueue(Event(127),True)
        elif e.kind==2:
            self.desk.release_all(e.source)
            self.replay_contacts={k:v for k,v in self.replay_contacts.items() if k[0]!=e.source}
            self.desk.enqueue(e)
        else:self.desk.enqueue(e)

    def build_mixer(self):
        box=self.page('混音 / 控制')
        grid=QGridLayout();box.addLayout(grid);self.mixers=[];self.solos=[];self.mutes=[];self.pans=[]
        for part in range(15):
            grid.addWidget(QLabel(f'{part+1:02d} '+self.desk.role_name(part)),part,0)
            slider=QSlider(Qt.Orientation.Horizontal);slider.setRange(0,127);slider.setValue(127)
            slider.valueChanged.connect(lambda v,p=part:self.mix(p,v));grid.addWidget(slider,part,1);self.mixers.append(slider)
            mute=QPushButton('静音');self.mutes.append(mute);mute.setCheckable(True);mute.toggled.connect(lambda on,p=part:self.mute(p,on));grid.addWidget(mute,part,2)
            solo=QPushButton('独奏');self.solos.append(solo);solo.setCheckable(True);solo.toggled.connect(lambda on,p=part:self.set_solo(p,on));grid.addWidget(solo,part,3)
            pan=QSlider(Qt.Orientation.Horizontal);pan.setRange(0,127);pan.setValue(64);pan.setToolTip('声像：左0 / 中64 / 右127；需扩展固件')
            pan.valueChanged.connect(lambda v,p=part:self.pan(p,v));grid.addWidget(pan,part,4);self.pans.append(pan)
        self.effect_mode=QComboBox();self.effect_mode.addItems(['延迟','多抽头混响（扩展固件）','合唱（扩展固件）'])
        self.effect_mode.currentIndexChanged.connect(self.choose_effect);box.addWidget(self.effect_mode)
        self.effect=QCheckBox('效果旁路');self.effect.toggled.connect(self.bypass);box.addWidget(self.effect)
        box.addWidget(QLabel('混音控制使用指挥权限。混响/合唱仅在扩展固件声明能力时可用。板载固件使用延迟。'))

    def sync_mixer(self):
        for p,slider in enumerate(self.mixers):
            slider.blockSignals(True);slider.setValue(self.desk.patch_values.get(p,{}).get(0,127));slider.blockSignals(False)
        state=self.desk.mixer_state;self.muted={p:True for p in state.get('muted',[])};self.solo=state.get('solo')
        for p,b in enumerate(self.solos):b.blockSignals(True);b.setChecked(p==self.solo);b.blockSignals(False)
        for p,b in enumerate(self.mutes):b.blockSignals(True);b.setChecked(self.muted.get(p,False));b.blockSignals(False)
        self.effect.blockSignals(True);self.effect.setChecked(state.get('bypass',False));self.effect.blockSignals(False)
        self.effect_mode.blockSignals(True);self.effect_mode.setCurrentIndex(self.desk.effect_mode);self.effect_mode.blockSignals(False)
        for p,s in enumerate(self.pans):s.blockSignals(True);s.setValue(self.desk.patch_values.get(p,{}).get(9,64));s.blockSignals(False)
        self.refresh_features()

    def refresh_features(self):
        features=self.desk.board_identity.get('features',0) if self.desk.board_identity else 0
        for slider in self.pans:slider.setEnabled(bool(features&512))

    def pan(self,part,value):
        if not(self.desk.board_identity and self.desk.board_identity.get('features',0)&512):return
        self.desk.patch_values.setdefault(part,{})[9]=value
        self.desk.enqueue(Event(11,source=1,part=part,flags=9,parameter=value))

    def mixer_snapshot(self):
        return dict(muted=sorted(p for p,on in self.muted.items() if on),solo=self.solo,bypass=self.effect.isChecked())

    def apply_mixer(self):
        for p,s in enumerate(self.mixers):self.mix(p,s.value())
        self.bypass(self.effect.isChecked())

    def choose_effect(self,index):
        if index and not (self.desk.board_identity and self.desk.board_identity.get('features',0)&128):
            self.effect_mode.blockSignals(True);self.effect_mode.setCurrentIndex(0);self.effect_mode.blockSignals(False)
            self.desk.effect_mode=0;self.error('当前固件只支持延迟；混响/合唱需要扩展固件。');return
        self.desk.effect_mode=index;self.bypass(self.effect.isChecked())

    def mix(self,part,value):
        self.desk.patch_values.setdefault(part,{})[0]=value
        muted=self.muted.get(part) or self.solo is not None and self.solo!=part
        self.desk.enqueue(Event(4,source=1,part=part,flags=2 if muted else 3))
        self.desk.enqueue(Event(11,source=1,part=part,flags=0,parameter=value))

    def mute(self,part,on):
        self.muted[part]=on;self.mix(part,self.mixers[part].value())

    def set_solo(self,part,on):
        if on:
            self.solo=part
            for p,b in enumerate(self.solos):
                b.blockSignals(True);b.setChecked(p==part);b.blockSignals(False)
        elif self.solo==part:self.solo=None
        for p,s in enumerate(self.mixers):self.mix(p,s.value())

    def bypass(self,on):
        self.desk.enqueue(Event(7,flags=self.desk.effect_mode,parameter=0 if on else self.desk.wet.value()))

    def build_library(self):
        box=self.page('曲库 / 场景')
        self.songs=QComboBox();box.addWidget(self.songs);self.refresh_library()
        button(box,'刷新曲库',self.refresh_library)
        onboard=QHBoxLayout();self.onboard_songs=QComboBox()
        for name in ('confluence_v6','four_families_demo','scale_chord_practice'):self.onboard_songs.addItem(name)
        onboard.addWidget(self.onboard_songs);button(onboard,'切换板端内置曲目',self.select_onboard_song);box.addLayout(onboard)
        self.library_status=QLabel('板端内置曲目尚未查询');box.addWidget(self.library_status)
        button(box,'打开所选曲目编排',self.open_song)
        button(box,'上传所选曲目（校验后手动开始）',self.upload_song)
        button(box,'导入外部作品 JSON',self.import_song)
        button(box,'保存当前演奏场景',self.save_scene);button(box,'恢复演奏场景',self.load_scene)
        box.addWidget(QLabel('上传曲谱保存在板端RAM，断电回到固件内置曲；持久曲库需重新导出固件或接入独立存储。'))
        box.addStretch()

    def refresh_library(self):
        self.songs.clear()
        for p in sorted((BAND/'assets').glob('*.json')):
            try:
                s=json.loads(p.read_text(encoding='utf-8'))
                if s.get('format') in ('starcluster-score-1','starcluster-score-2'):self.songs.addItem(p.stem,str(p))
            except (OSError,ValueError):pass

    def select_onboard_song(self):
        if not self.desk.port or not self.desk.board_identity or not self.desk.board_identity.get('features',0)&2048:
            self.error('当前已烧录固件未声明板端内置曲库；请使用扩展构建并重新验收。');return
        self.desk.enqueue(Event(20,source=1,parameter=self.onboard_songs.currentIndex()))
        self.library_status.setText('请求已发送；曲谱校验通过后板端自动启用新曲。')

    def update_library_status(self,status):
        self.library_status.setText(('板端曲目 '+str(status['song'])+' 已载入' if not status['busy'] and not status['failed'] else
          '板端曲目载入失败' if status['failed'] else '板端正在载入曲目 '+str(status['song'])))

    def selected_song(self):
        from score import load as read_score
        return read_score(self.songs.currentData())

    def open_song(self):
        try:
            self.desk.open_editor();self.desk.editor.set_score(self.selected_song());self.status.setText('曲目已打开')
        except Exception as exc:self.error(exc)

    def upload_song(self):
        try:
            score=self.selected_song()
            from score import validate_target
            validate_target(score,self.desk.board_identity.get('features',0) if self.desk.board_identity else None)
            self.desk.restore_performance(score.get('performance',{}));self.desk.upload_score(score)
            self.status.setText('已提交曲谱，请看演奏台上传结果，校验通过后再开始。')
        except Exception as exc:self.error(exc)

    def import_song(self):
        path,_=QFileDialog.getOpenFileName(self,'打开作品','','JSON (*.json)')
        if path:
            from score import load as read_score
            try:read_score(path);self.songs.addItem(Path(path).stem,path);self.songs.setCurrentIndex(self.songs.count()-1)
            except Exception as exc:self.error(exc)

    def save_scene(self):
        path,_=QFileDialog.getSaveFileName(self,'保存场景','演奏场景.json','JSON (*.json)')
        if path:
            try:
                from storage import atomic_json
                atomic_json(path,dict(format='starcluster-scene-1',performance=self.desk.capture_performance()));self.status.setText('场景已保存')
            except Exception as exc:self.error(exc)

    def load_scene(self):
        path,_=QFileDialog.getOpenFileName(self,'恢复场景','','JSON (*.json)')
        if path:
            try:
                data=json.loads(Path(path).read_text(encoding='utf-8'))
                if data.get('format')!='starcluster-scene-1':raise ValueError('不是星群场景')
                from scene import validate_performance
                validate_performance(data['performance']);self.desk.restore_performance(data['performance']);self.desk.apply_performance_controls()
                self.status.setText('场景已恢复')
            except Exception as exc:self.error(exc)

    def build_metrics(self):
        box=self.page('赛项 / 诊断')
        self.requirements=QTableWidget(0,4);self.requirements.setHorizontalHeaderLabels(['要求','当前实现','验收状态','展示方式'])
        self.requirements.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.requirements.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.requirements.setWordWrap(True)
        self.requirements.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);box.addWidget(self.requirements)
        rows=[('O01 · ≥2个自研交互维度','ADC/压力/编码器RTL；当前固定壳未接入','待接线、分维度实演','输入原始值和独立声音响应'),
              ('O02 · HDL完整音频生成','FPGA事件驱动参数音源；当前板载PT8211','数字链路已实现；听音待验','板端演奏和源码/存储审查'),
              ('O03 · ≥4复音/变调/ADSR/混音','256音符槽设计、表情与包络参数通路','数字证据；实际听音待验','四音和弦演示与包络控制'),
              ('O04 · I²S→DAC / ≤10 ms','PT8211为右对齐；I²S扩展源码未布管脚','当前板不满足I²S；延迟未测','接外置DAC并测触发到模拟输出'),
              ('O05 · 不用预录PCM作音源','曲目是事件数据，由HDL按参数发声','软件结构符合；交付审计待做','改音高/音色并审查ROM内容'),
              ('O06 · ≥32复音/加法分量','256槽数字负载证据；槽数不等于声学分量','数字通过；独立可听分量待验','多频测量、活动计数与期限遥测'),
              ('O07 · ≥3表情/≥2音色/硬件效果','力度/弯音/表情、15预设、延迟；扩展含混响/合唱','算法与RTL已做；外设/听感待验','音色页、参数控制、效果旁路A/B'),
              ('O08 · ≤5 ms/确定性/可视化','固定周期音频处理、DVI/FFT数字链路','周期有界；模拟时延/实屏待验','模拟输出测延迟并接真实显示器'),
              ('O09 · 脱机LED曲目指引','ROM事件曲库及LED指引扩展源码','逻辑待冷启动；LED未接线','断开主机播放和音高/节拍指示'),
              ('O10 · 手机联动','C3 BLE/UART固件、手机演奏和曲目控制页','固件编译；配对/断链待实测','连接手机、控制曲目并断链复验'),
              ('产品项 · 演奏事件录制','上位机记录音符/力度/参数并重放，不录WAV','电脑事件回归通过；面板回传属扩展','录制页和实体输入记录重放')]
        self.requirements.setRowCount(len(rows))
        for r,row in enumerate(rows):
            for c,value in enumerate(row):
                item=QTableWidgetItem(value);item.setToolTip(value);self.requirements.setItem(r,c,item)
        self.live=QLabel();self.live.setWordWrap(True);box.addWidget(self.live)
        row=QHBoxLayout();box.addLayout(row)
        button(row,'舞台投屏 / 音频监测',self.desk.open_stage)
        button(row,'四音和弦演示',self.demo_chord)
        button(row,'导出当前诊断记录',self.export_diagnostics)
        box.addWidget(QLabel('官方：gowinsemi.com.cn/university/match2026。展示入口不是验收通过按钮；过期数据不计成绩。'))

    def demo_chord(self):
        if not self.desk.port:self.error('先连接FPGA');return
        s=self.desk.source()
        for i,note in enumerate((60,64,67,72)):self.desk.press(200+i,note,85)
        QTimer.singleShot(1600,lambda:[self.desk.release(200+i,s) for i in range(4)])

    def export_diagnostics(self):
        path,_=QFileDialog.getSaveFileName(self,'保存诊断','诊断记录.json','JSON (*.json)')
        if path:
            try:
                from storage import atomic_json
                atomic_json(path,dict(identity=self.desk.board_identity,states=self.desk.states,
                    rx_age_s=time.monotonic()-self.desk.last_rx if self.desk.last_rx else None,
                    bad_crc=self.desk.decoder.bad_crc,scope='UART telemetry; not acoustic/latency/thermal proof'))
                self.status.setText('诊断已保存')
            except Exception as exc:self.error(exc)

    def tick(self):
        now=time.monotonic()
        if self.desk.port and self.desk.board_identity and self.desk.board_identity.get('features',0)&2048 and now-self.last_library_poll>=1:
            self.last_library_poll=now;self.desk.enqueue(Event(21))
        if self.recorder.active:
            self.record_info.setText(f'录制中 {(now-self.recorder.started):.1f}s · {len(self.recorder.take["events"])} 事件')
            if self.desk.port is None:self.stop_recording();self.status.setText('连接丢失，录制已结束并补齐释放；请保存。')
        elif self.take:self.record_info.setText(f'{self.take["duration_us"]/1000000:.2f}s · {len(self.take["events"])} 事件')
        if self.replay_wait:
            started,requirements=self.replay_wait
            if not self.desk.port or now-started>4:
                self.stop_playback();self.error('重放授权超时或断连');return
            if all(self.desk.states.get(p,{}).get('owner')==source and
                   self.desk.states[p].get('_received',0)>started+.1 for p,source in requirements.items()) and now-started>.2:
                self.replay_wait=None;self.player.start(self.take,now,self.speed.value())
        if self.player.active:
            if self.desk.port is None or self.desk.await_upload:
                self.stop_playback();self.error('重放停止：断连或曲谱上传');return
            if len(self.desk.queue)>64:
                self.stop_playback();self.desk.panic();self.error('重放事件超过实时发送能力，已停音；降低速度或事件密度');return
            try:
                for data in self.player.due(now,8):self.replay(data)
                if not self.player.active:
                    self.pending_return=now+.25
            except Exception as exc:self.stop_playback();self.desk.panic();self.error(exc)
        if self.pending_return and now>=self.pending_return:
            self.stop_playback()
            if self.loop.isChecked():self.start_playback()
        age=now-self.desk.last_rx if self.desk.last_rx else None
        self.live.setText('未连接 / 遥测过期' if self.desk.port is None or age is None or age>1.5 else
            self.desk.identity_label.text()+'\n'+self.desk.metrics.text())

    def shutdown(self):
        self.stop_playback();self.stop_recording();self.timer.stop()
        if self.take is not None:
            try:
                target=BAND/'recordings';target.mkdir(exist_ok=True)
                save(target/('autosave_'+time.strftime('%Y%m%d_%H%M%S')+'.take.json'),self.take)
            except Exception as exc:self.error('自动保存失败：'+str(exc))

    def closeEvent(self,event):
        self.stop_playback();self.stop_recording();event.accept()
