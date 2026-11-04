import copy
from pathlib import Path
from PySide6.QtCore import Qt,Signal,QTimer
from PySide6.QtGui import QColor,QBrush,QPen
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QComboBox,QSpinBox,QPushButton,QLabel,QGraphicsView,QGraphicsScene,QFileDialog,QMessageBox,QToolButton,QMenu
import score as model
from score_tools import History, articulate, section
class Roll(QGraphicsView):
    edit=Signal(float,int,bool)
    move_note=Signal(int,float,int,bool)
    step=.25
    drag=None
    def mousePressEvent(self,e):
        p=self.mapToScene(e.position().toPoint())
        item=self.itemAt(e.position().toPoint())
        if e.button()==Qt.MouseButton.LeftButton and item is not None and item.data(0) is not None:
            self.drag=(int(item.data(0)),p.x(),bool(e.modifiers()&Qt.KeyboardModifier.ShiftModifier));return
        if 48<=p.x()<944 and 0<=p.y()<600:self.edit.emit(int((p.x()-48)/(224*self.step))*self.step,95-int(p.y()//10),e.button()==Qt.MouseButton.RightButton)
        else:super().mousePressEvent(e)
    def mouseReleaseEvent(self,e):
        if self.drag is not None:
            serial,old_x,resize=self.drag;self.drag=None
            p=self.mapToScene(e.position().toPoint())
            beat=round((p.x()-old_x)/224/self.step)*self.step
            self.move_note.emit(serial,beat,max(36,min(95,95-int(p.y()//10))),resize)
        else:super().mouseReleaseEvent(e)
class ScoreEditor(QDialog):
    upload=Signal(object)
    def __init__(self,parent=None):
        super().__init__(parent);self.setWindowTitle('星群 · 作品编排');self.resize(1040,780)
        self.score=model.load(Path(__file__).resolve().parents[1]/'assets/confluence_smooth.json');self.filename=None;self.history=History();self.clipboard=None;self.loop_enabled=False;self.loop_armed=False
        layout=QVBoxLayout(self);row=QHBoxLayout();self.part=QComboBox();self.part.addItems([f'{i+1}: {x}' for i,x in enumerate(self.score['roles']+[f'备用{i+1}' for i in range(8,16)])]);row.addWidget(self.part)
        self.profile=QComboBox();self.profile.addItems(['第16轨：扩展音色','第16轨：电子歌手']);row.addWidget(self.profile)
        row.addWidget(QLabel('小节'));self.bar=QSpinBox();self.bar.setRange(1,self.measure_count());row.addWidget(self.bar)
        row.addWidget(QLabel('音长/拍'));self.length=QComboBox();self.length.addItems(['0.125','0.166666667','0.25','0.333333333','0.5','0.75','1','1.5','2','4']);self.length.setCurrentText('0.5');row.addWidget(self.length)
        row.addWidget(QLabel('力度'));self.velocity=QSpinBox();self.velocity.setRange(1,127);self.velocity.setValue(90);row.addWidget(self.velocity);layout.addLayout(row)
        tools=QHBoxLayout();layout.addLayout(tools)
        self.grid=QComboBox()
        for label,value in [('1/16音符',.25),('1/32音符',.125),('十六分三连音',1/6),('八分三连音',1/3)]:self.grid.addItem(label,value)
        tools.addWidget(QLabel('网格'));tools.addWidget(self.grid)
        for label,callback in [('撤销',self.undo),('重做',self.redo),('复制小节',self.copy_bar),('粘贴小节',self.paste_bar),('平滑短间隙',self.smooth),('加入节拍器',self.metronome)]:
            b=QPushButton(label);b.clicked.connect(callback);tools.addWidget(b)
        loop_row=QHBoxLayout();layout.addLayout(loop_row)
        self.loop_start=QSpinBox();self.loop_start.setRange(1,999);self.loop_end=QSpinBox();self.loop_end.setRange(1,999);self.loop_end.setValue(4)
        loop_row.addWidget(QLabel('循环起止小节'));loop_row.addWidget(self.loop_start);loop_row.addWidget(self.loop_end)
        for label,callback in [('上传循环段',self.upload_loop),('停止循环',self.stop_loop),('导入 MIDI',self.import_midi),('导出 MIDI',self.export_midi)]:
            b=QPushButton(label);b.clicked.connect(callback);loop_row.addWidget(b)
        layout.addWidget(QLabel('左键加音，右键删音；拖动已有音符移动，Shift+拖动调音长。曲谱保存事件，不含音频。'))
        vocal=QHBoxLayout();vocal.addWidget(QLabel('合唱轨元音 · 本小节第'))
        self.vowel_position=QComboBox();self.vowel_position.addItems([f'{1+i/4:g} 拍' for i in range(16)]);vocal.addWidget(self.vowel_position)
        self.vowel_choice=QComboBox();self.vowel_choice.addItems(['A','E','I','O','U']);vocal.addWidget(self.vowel_choice)
        for label,erase in [('设置元音',False),('删除此处元音',True)]:
            b=QPushButton(label);b.clicked.connect(lambda checked=False,remove=erase:self.edit_vowel(remove));vocal.addWidget(b)
        layout.addLayout(vocal)
        phrase=QHBoxLayout();self.phrase_choice=QComboBox();self.phrase_choice.addItems(['A I O U · 上行','U O I A · 下行','A A E O · 呼应']);phrase.addWidget(self.phrase_choice)
        phrase.addWidget(QLabel('乐句基音 MIDI'));self.phrase_pitch=QSpinBox();self.phrase_pitch.setRange(36,84);self.phrase_pitch.setValue(60);phrase.addWidget(self.phrase_pitch)
        insert=QPushButton('在本小节插入四拍元音乐句');insert.clicked.connect(self.insert_phrase);phrase.addWidget(insert);layout.addLayout(phrase)
        self.view=Roll();self.scene=QGraphicsScene();self.view.setScene(self.scene);self.view.edit.connect(self.edit);self.view.move_note.connect(self.move_note);layout.addWidget(self.view)
        buttons=QHBoxLayout()
        for label,callback in [('打开作品',self.open),('保存作品',self.save),('上传到 FPGA 备用曲谱',self.send)]:
            b=QPushButton(label);b.clicked.connect(callback);buttons.addWidget(b)
        export_button=QToolButton();export_button.setText('导出脱机工程');export_button.setPopupMode(QToolButton.InstantPopup)
        export_menu=QMenu(export_button)
        for label,options in [('基础乐队 · 板载音频',{}),('融合演奏席 · 板载音频',{'stage':True}),
                              ('外置 I2S 音频与频谱读取',{'workstation':True}),
                              ('外置 I2S 音频与逻辑 RGB',{'video':True}),
                              ('外置 I2S 音频与 DVI 显示 · 开发候选',{'dvi':True}),
                              ('板载 PT8211 音频与 DVI 显示 · 开发候选',{'pt8211_dvi':True}),
                              ('共享乐队 · 板载音频与显示 · 开发候选',{'shared':True}),
                              ('V6完整扩展 · I²S/面板/DVI · 未定管脚',{'v6':True}),
                              ('V6 USB16垫 + 脉冲旋钮 · 无ADC · 未定管脚',{'v6':True,'usb16':True}),
                              ('V6 16垫精简扩展 · 3片ADC · 未定管脚',{'v6':True,'compact16':True})]:
            action=export_menu.addAction(label);action.triggered.connect(lambda checked=False,options=options:self.export_offline(**options))
        export_button.setMenu(export_menu);buttons.addWidget(export_button)
        layout.addLayout(buttons);self.info=QLabel('上传不会打断当前演出；停止并重新开始后启用新曲谱。RAM 曲谱断电后回到固件默认作品。');self.info.setWordWrap(True);layout.addWidget(self.info)
        self.part.currentIndexChanged.connect(self.draw);self.bar.valueChanged.connect(self.draw);self.draw()
        self.grid.currentIndexChanged.connect(self.update_grid)
        self.loop_timer=QTimer(self);self.loop_timer.timeout.connect(self.poll_loop);self.loop_timer.start(100)
        self.profile.currentIndexChanged.connect(self.change_profile)
        identity=getattr(parent,'board_identity',None)
        if identity and identity.get('features',0)&32 and not any(e['part']==15 for e in self.score['events']):self.profile.setCurrentIndex(1)
    def measure_count(self):
        # Include the final partial measure, using integer sample arithmetic.
        numerator=self.score['duration_samples']*self.score['bpm']
        denominator=self.score['sample_rate']*60*4
        return max(1,(numerator+denominator-1)//denominator)
    def change_profile(self,index):
        candidate=copy.deepcopy(self.score);candidate['engine_profile']='singer-v1' if index else 'band-v1'
        candidate['format']='starcluster-score-2' if index else 'starcluster-score-1'
        try:model.validate(candidate)
        except ValueError as e:
            self.profile.blockSignals(True);self.profile.setCurrentIndex(1 if self.score.get('engine_profile')=='singer-v1' else 0);self.profile.blockSignals(False)
            self.info.setText('角色未改变：'+str(e));return
        self.score=candidate;self.part.setItemText(15,'16: 电子歌手' if index else '16: 扩展音色')
        self.info.setText('第16轨角色已写入作品；上传时会检查目标支持。电子歌手可导出源码工程，麦克风接线与时序需配置。' if index else '第16轨使用标准乐队扩展音色。')
    def draw(self):
        self.scene.clear();self.scene.setSceneRect(0,0,944,600);start=(self.bar.value()-1)*4;spb=48000*60/self.score['bpm']
        for row in range(60):
            pitch=95-row;black=pitch%12 in (1,3,6,8,10);color=QColor('#1c2836' if black else '#26384a')
            self.scene.addRect(48,row*10,896,10,QPen(QColor('#344455')),QBrush(color))
            if pitch%12==0:
                label=self.scene.addText(f'C{pitch//12-1}');label.setDefaultTextColor(QColor('#e5edf5'));label.setPos(0,row*10-5)
        step=self.grid.currentData()
        for col in range(round(4/step)+1):
            x=48+col*step*224;self.scene.addLine(x,0,x,600,QPen(QColor('#66818e' if abs(col*step-round(col*step))<.001 else '#344455')))
        if self.part.currentIndex()==7:
            for e in self.score['events']:
                beat=e['sample']/spb-start
                if e['kind']==2 and e['part']==7 and 0<=beat<4:
                    x=48+beat*224;self.scene.addLine(x,0,x,600,QPen(QColor('#f0bd69')))
                    label=self.scene.addText('AEIOU'[e['note']]);label.setDefaultTextColor(QColor('#f0bd69'));label.setPos(x,0)
        offs={(e['part'],e['note'],e['serial']):e for e in self.score['events'] if e['kind']==1}
        for e in self.score['events']:
            if e['kind'] or e['part']!=self.part.currentIndex() or not 36<=e['note']<=95:continue
            end=offs[(e['part'],e['note'],e['serial'])]['sample']/spb;begin=e['sample']/spb
            if end<=start or begin>=start+4:continue
            x=max(begin-start,0);length=min(end-start,4)-x
            item=self.scene.addRect(48+x*224,(95-e['note'])*10,max(3,length*224),9,QPen(Qt.PenStyle.NoPen),QBrush(QColor('#59ccb5')));item.setToolTip(f'MIDI {e["note"]} · 力度 {e["velocity"]}');item.setData(0,e['serial'])
    def insert_phrase(self):
        patterns=[[(0,0),(2,4),(3,7),(4,12)],[(4,12),(3,7),(2,4),(0,0)],[(0,0),(0,7),(1,4),(3,0)]]
        try:
            sample=(self.bar.value()-1)*96000
            self.history.remember(self.score)
            self.score=model.insert_vowel_phrase(self.score,sample,[(v,self.phrase_pitch.value()+n,24000) for v,n in patterns[self.phrase_choice.currentIndex()]],self.velocity.value())
            self.part.setCurrentIndex(7);self.draw();self.info.setText('已插入四拍有限元音乐句：每拍换元音和音高，音节间留10%间隙，结束恢复原元音。只允许空白合唱区；不代表自然歌词歌唱。')
        except ValueError as e:QMessageBox.warning(self,'不能插入乐句',str(e))
    def edit_vowel(self,erase=False):
        sample=round(((self.bar.value()-1)*4+self.vowel_position.currentIndex()/4)*48000*60/self.score['bpm'])
        try:
            self.history.remember(self.score)
            self.score=model.edit_vowel(self.score,sample,None if erase else self.vowel_choice.currentIndex())
            self.part.setCurrentIndex(7);self.draw()
            self.info.setText('合唱轨元音已编辑：应用于此位置之后新起的合唱音符，已持续的音符保持原元音。元音事件本身不会起音；保存、上传及脱机导出均会保留。')
        except ValueError as e:QMessageBox.warning(self,'无法编辑元音',str(e))
    def edit(self,beat,pitch,erase):
        spb=48000*60/self.score['bpm'];start=round(((self.bar.value()-1)*4+beat)*spb);part=self.part.currentIndex()
        candidate=copy.deepcopy(self.score);events=candidate['events']
        if erase:
            ids={e['serial'] for e in events if e['kind']==0 and e['part']==part and e['note']==pitch and start<=e['sample']<start+spb*self.grid.currentData()}
            candidate['events']=[e for e in events if not(e['kind'] in (0,1) and e['part']==part and e['note']==pitch and e['serial'] in ids)]
        else:
            serial=max((e['serial'] for e in events),default=0)+1
            end=min(candidate['duration_samples']-1,start+round(float(self.length.currentText())*spb))
            if end<=start:return
            for kind,t,vel in [(0,start,self.velocity.value()),(1,end,0)]:events.append(dict(sample=t,kind=kind,part=part,note=pitch,velocity=vel,serial=serial))
            events.sort(key=lambda e:(e['sample'],e['kind']==0,e['part'],e['serial']))
        candidate['edited']=True;candidate['decisions']=[]
        try:self.set_score(candidate)
        except ValueError as exc:self.info.setText(str(exc))
    def open(self):
        p,_=QFileDialog.getOpenFileName(self,'打开事件作品','','星群作品 (*.json)')
        if p:
            try:
                self.set_score(model.load(p));self.filename=p;self.parent().restore_performance(self.score.get('performance'));self.bar.setMaximum(self.measure_count())
                self.profile.blockSignals(True);index=1 if self.score.get('engine_profile')=='singer-v1' else 0;self.profile.setCurrentIndex(index);self.profile.blockSignals(False)
                self.part.setItemText(15,'16: 电子歌手' if index else '16: 扩展音色');self.draw()
            except Exception as e:QMessageBox.warning(self,'无法打开',str(e))
    def save(self):
        p,_=QFileDialog.getSaveFileName(self,'保存事件作品',self.filename or '星群作品.json','星群作品 (*.json)')
        if p:
            try:self.score['performance']=self.parent().capture_performance();model.save(p,self.score);self.filename=p;self.info.setText('作品、音色参数与输入映射已保存：'+p)
            except Exception as e:QMessageBox.warning(self,'无法保存',str(e))
    def send(self):
        try:model.validate(self.score);self.upload.emit(copy.deepcopy(self.score));self.info.setText('已提交上传。等待演奏台显示 CRC 校验通过后，停止并重新开始演出。')
        except Exception as e:QMessageBox.warning(self,'不能上传',str(e))
    def export_offline(self,stage=False,workstation=False,video=False,dvi=False,pt8211_dvi=False,shared=False,v6=False,compact16=False,usb16=False):
        from offline import export_project
        if stage or workstation or video or dvi or pt8211_dvi or shared or v6:
            if self.score.get('engine_profile')!='singer-v1':
                QMessageBox.warning(self,'不能导出融合工程','请先将第16轨角色设为电子歌手，并确认曲谱适合该角色。');return
            from offline_stage import export_stage_project as export_project
            if workstation:from offline_workstation import export_workstation_project as export_project
            if video:from offline_video import export_video_project as export_project
            if dvi:from offline_dvi import export_dvi_project as export_project
            if pt8211_dvi:from offline_pt8211_dvi import export_pt8211_dvi_project as export_project
            if shared:from offline_shared import export_shared_project as export_project
            if v6:from offline_v6 import export_v6_project as export_project
        destination=QFileDialog.getExistingDirectory(self,'选择一个空目录存放完整脱机工程')
        if not destination:return
        try:
            if self.parent() is not None:self.score['performance']=self.parent().capture_performance()
            performance=self.score.get('performance',{})
            if not v6 and (performance.get('effect_mode',0) or any(int(k) in (8,9) for values in performance.get('patches',{}).values() for k in values)):
                raise ValueError('此作品含V6独立音色/声像或效果，请选择V6完整扩展导出，旧导出不能保存这些参数')
            if self.score.get('timbre_schema')=='workstation-v6' and not(shared or v6):
                raise ValueError('V6扩展音色请使用共享乐队或V6完整扩展导出，避免旧引擎发错音色')
            result=export_project(copy.deepcopy(self.score),destination,autoplay=False,compact16=compact16,usb16=usb16) if v6 else export_project(copy.deepcopy(self.score),destination,autoplay=True)
            if v6:
                self.info.setText('已导出V6完整扩展源码及作品/音色/声像/效果/校准；启动保持停止。扩展管脚和时序未审核，不能直接烧录：'+str(result));return
            self.info.setText(('已导出板载 PT8211 与 DVI 候选；保留扩展接口，需重新构建和验收：' if pt8211_dvi else '已导出 DVI 显示候选工程；需核对实际接线、重新构建和验收：' if dvi else '已导出舞台视频工程（I2S 音频与逻辑 RGB）；需配置真实音频、显示时钟及接口：' if video else '已导出工作站工程（外部 I2S 音频、频谱读取）；需要外部音频时钟、DAC及显示接口配置：' if workstation else '已导出融合源码工程（本地垫、脚踏、麦克风）；先配置全部外设引脚与时序：' if stage else '已导出电子歌手源码工程；先配置麦克风引脚与时序：' if self.score.get('engine_profile')=='singer-v1' else '已导出上电自动演出的工程：')+str(result)+'。需重新构建和验证；当前板上内容未改变。')
        except Exception as e:QMessageBox.warning(self,'不能导出',str(e))

    def set_score(self,score):
        model.validate(score);self.history.remember(self.score);self.score=copy.deepcopy(score)
        self.bar.setMaximum(self.measure_count())
        self.profile.blockSignals(True);self.profile.setCurrentIndex(int(score.get('engine_profile')=='singer-v1'));self.profile.blockSignals(False)
        self.draw()
    def update_grid(self):
        self.view.step=self.grid.currentData();self.draw()
    def undo(self):self.score=self.history.undo(self.score);self.bar.setMaximum(self.measure_count());self.draw()
    def redo(self):self.score=self.history.redo(self.score);self.bar.setMaximum(self.measure_count());self.draw()
    def smooth(self):
        try:self.set_score(articulate(self.score));self.info.setText('已连接不超过1/4拍的短间隙，保留段落休止。可撤销。')
        except ValueError as exc:self.info.setText(str(exc))
    def move_note(self,serial,delta,pitch,resize):
        candidate=copy.deepcopy(self.score);part=self.part.currentIndex();pair=[e for e in candidate['events'] if e['serial']==serial and e['part']==part and e['kind'] in (0,1)]
        if len(pair)!=2:return
        on=next(e for e in pair if e['kind']==0);off=next(e for e in pair if e['kind']==1);samples=round(delta*24000)
        if resize:off['sample']=min(candidate['duration_samples']-1,max(on['sample']+1,off['sample']+samples))
        else:
            samples=max(-on['sample'],min(samples,candidate['duration_samples']-1-off['sample']))
            for e in pair:e['sample']+=samples;e['note']=pitch
        candidate['events'].sort(key=lambda e:(e['sample'],e['kind']==0,e['part'],e['serial']))
        try:self.set_score(candidate)
        except ValueError as exc:self.info.setText(str(exc))
    def copy_bar(self):
        try:self.clipboard=section(self.score,(self.bar.value()-1)*4,self.bar.value()*4);self.info.setText('已复制当前小节全部声部')
        except ValueError as exc:self.info.setText(str(exc))
    def paste_bar(self):
        if not self.clipboard:return
        candidate=copy.deepcopy(self.score);offset=(self.bar.value()-1)*96000
        serial=max(e['serial'] for e in candidate['events'])+1;ids={}
        for e in self.clipboard['events']:
            n=copy.deepcopy(e);key=(e['part'],e['serial']);ids.setdefault(key,serial+len(ids));n['serial']=ids[key];n['sample']+=offset
            if n['sample']>=candidate['duration_samples']:self.info.setText('粘贴超出作品长度，未修改');return
            candidate['events'].append(n)
        candidate['events'].sort(key=lambda e:(e['sample'],e['kind']==0,e['part'],e['serial']))
        try:self.set_score(candidate)
        except ValueError as exc:self.info.setText(str(exc))
    def metronome(self):
        from score_tools import with_metronome
        try:self.set_score(with_metronome(self.score));self.info.setText('节拍器已加入踩镲轨，可撤销；上传后由FPGA生成声音。')
        except ValueError as exc:self.info.setText(str(exc))

    def upload_loop(self):
        try:
            loop=section(self.score,(self.loop_start.value()-1)*4,self.loop_end.value()*4)
            self.upload.emit(loop);self.loop_enabled=True;self.loop_armed=False;self.loop_seen=False;self.loop_errors=self.parent().upload_errors;self.loop_started=0;self.info.setText('循环段已提交；校验完成后自动开始，循环重启由电脑调度。')
        except ValueError as exc:self.info.setText(str(exc))
    def poll_loop(self):
        desk=self.parent()
        if not self.loop_enabled or not desk or not desk.port:return
        if desk.upload_errors>self.loop_errors:
            self.stop_loop();self.info.setText('上传失败，循环已停止');return
        if desk.await_upload:return
        import time
        now=time.monotonic()
        if not self.loop_armed:
            desk.start_performance();self.loop_armed=True;self.loop_started=now;return
        fresh=[x for x in desk.states.values() if x.get('_received',0)>self.loop_started]
        if any(x.get('playing',False) for x in fresh):self.loop_seen=True
        if self.loop_seen and fresh and all(not x.get('playing',False) for x in fresh):
            desk.start_performance();self.loop_seen=False;self.loop_started=now
        elif not self.loop_seen and now-self.loop_started>5:
            self.stop_loop();self.info.setText('未收到开始确认，循环已停止')
    def stop_loop(self):
        self.loop_enabled=False;self.loop_armed=False
        from protocol import Event
        if self.parent():self.parent().enqueue(Event(5,flags=1))
    def import_midi(self):
        path,_=QFileDialog.getOpenFileName(self,'导入 MIDI','','MIDI (*.mid *.midi)')
        if path:
            try:
                from midi_file import read_midi
                self.set_score(read_midi(path));self.info.setText('MIDI已导入；通道映射为声部，乐器需在音色库确认。')
            except Exception as exc:self.info.setText(str(exc))
    def export_midi(self):
        path,_=QFileDialog.getSaveFileName(self,'导出 MIDI','作品.mid','MIDI (*.mid)')
        if path:
            try:
                from midi_file import write_midi
                write_midi(path,self.score);self.info.setText('已导出音符MIDI；星群专用元音/参数保留在JSON作品中。')
            except Exception as exc:self.info.setText(str(exc))
    def closeEvent(self,event):
        self.stop_loop();self.loop_timer.stop();event.accept()
    def showEvent(self,event):
        self.loop_timer.start();super().showEvent(event)
