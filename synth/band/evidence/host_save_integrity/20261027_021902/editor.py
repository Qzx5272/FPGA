import copy
from pathlib import Path
from PySide6.QtCore import Qt,Signal
from PySide6.QtGui import QColor,QBrush,QPen
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QComboBox,QSpinBox,QPushButton,QLabel,QGraphicsView,QGraphicsScene,QFileDialog,QMessageBox,QToolButton,QMenu
import score as model
class Roll(QGraphicsView):
    edit=Signal(float,int,bool)
    def mousePressEvent(self,e):
        p=self.mapToScene(e.position().toPoint())
        if 48<=p.x()<944 and 0<=p.y()<600:self.edit.emit(int((p.x()-48)//56)/4,95-int(p.y()//10),e.button()==Qt.MouseButton.RightButton)
        else:super().mousePressEvent(e)
class ScoreEditor(QDialog):
    upload=Signal(object)
    def __init__(self,parent=None):
        super().__init__(parent);self.setWindowTitle('星群 · 作品编排');self.resize(1040,780)
        self.score=model.load(Path(__file__).resolve().parents[1]/'assets/confluence.json');self.filename=None
        layout=QVBoxLayout(self);row=QHBoxLayout();self.part=QComboBox();self.part.addItems([f'{i+1}: {x}' for i,x in enumerate(self.score['roles']+[f'备用{i+1}' for i in range(8,16)])]);row.addWidget(self.part)
        self.profile=QComboBox();self.profile.addItems(['第16轨：扩展音色','第16轨：电子歌手']);row.addWidget(self.profile)
        row.addWidget(QLabel('小节'));self.bar=QSpinBox();self.bar.setRange(1,self.measure_count());row.addWidget(self.bar)
        row.addWidget(QLabel('音长/拍'));self.length=QComboBox();self.length.addItems(['0.25','0.5','1','2','4']);self.length.setCurrentText('0.5');row.addWidget(self.length)
        row.addWidget(QLabel('力度'));self.velocity=QSpinBox();self.velocity.setRange(1,127);self.velocity.setValue(90);row.addWidget(self.velocity);layout.addLayout(row)
        layout.addWidget(QLabel('左键添加音符，右键删除该格中的音符。每格 1/4 拍；曲谱仅保存事件和参数。'))
        vocal=QHBoxLayout();vocal.addWidget(QLabel('合唱轨元音 · 本小节第'))
        self.vowel_position=QComboBox();self.vowel_position.addItems([f'{1+i/4:g} 拍' for i in range(16)]);vocal.addWidget(self.vowel_position)
        self.vowel_choice=QComboBox();self.vowel_choice.addItems(['A','E','I','O','U']);vocal.addWidget(self.vowel_choice)
        for label,erase in [('设置元音',False),('删除此处元音',True)]:
            b=QPushButton(label);b.clicked.connect(lambda checked=False,remove=erase:self.edit_vowel(remove));vocal.addWidget(b)
        layout.addLayout(vocal)
        phrase=QHBoxLayout();self.phrase_choice=QComboBox();self.phrase_choice.addItems(['A I O U · 上行','U O I A · 下行','A A E O · 呼应']);phrase.addWidget(self.phrase_choice)
        phrase.addWidget(QLabel('乐句基音 MIDI'));self.phrase_pitch=QSpinBox();self.phrase_pitch.setRange(36,84);self.phrase_pitch.setValue(60);phrase.addWidget(self.phrase_pitch)
        insert=QPushButton('在本小节插入四拍元音乐句');insert.clicked.connect(self.insert_phrase);phrase.addWidget(insert);layout.addLayout(phrase)
        self.view=Roll();self.scene=QGraphicsScene();self.view.setScene(self.scene);self.view.edit.connect(self.edit);layout.addWidget(self.view)
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
                              ('共享乐队 · 板载音频与显示 · 开发候选',{'shared':True})]:
            action=export_menu.addAction(label);action.triggered.connect(lambda checked=False,options=options:self.export_offline(**options))
        export_button.setMenu(export_menu);buttons.addWidget(export_button)
        layout.addLayout(buttons);self.info=QLabel('上传不会打断当前演出；停止并重新开始后启用新曲谱。RAM 曲谱断电后回到固件默认作品。');self.info.setWordWrap(True);layout.addWidget(self.info)
        self.part.currentIndexChanged.connect(self.draw);self.bar.valueChanged.connect(self.draw);self.draw()
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
        for col in range(17):self.scene.addLine(48+col*56,0,48+col*56,600,QPen(QColor('#66818e' if col%4==0 else '#344455')))
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
            item=self.scene.addRect(48+x*224,(95-e['note'])*10,max(3,length*224),9,QPen(Qt.PenStyle.NoPen),QBrush(QColor('#59ccb5')));item.setToolTip(f'MIDI {e["note"]} · 力度 {e["velocity"]}')
    def insert_phrase(self):
        patterns=[[(0,0),(2,4),(3,7),(4,12)],[(4,12),(3,7),(2,4),(0,0)],[(0,0),(0,7),(1,4),(3,0)]]
        try:
            sample=(self.bar.value()-1)*96000
            self.score=model.insert_vowel_phrase(self.score,sample,[(v,self.phrase_pitch.value()+n,24000) for v,n in patterns[self.phrase_choice.currentIndex()]],self.velocity.value())
            self.part.setCurrentIndex(7);self.draw();self.info.setText('已插入四拍有限元音乐句：每拍换元音和音高，音节间留10%间隙，结束恢复原元音。只允许空白合唱区；不代表自然歌词歌唱。')
        except ValueError as e:QMessageBox.warning(self,'不能插入乐句',str(e))
    def edit_vowel(self,erase=False):
        sample=round(((self.bar.value()-1)*4+self.vowel_position.currentIndex()/4)*48000*60/self.score['bpm'])
        try:
            self.score=model.edit_vowel(self.score,sample,None if erase else self.vowel_choice.currentIndex())
            self.part.setCurrentIndex(7);self.draw()
            self.info.setText('合唱轨元音已编辑：应用于此位置之后新起的合唱音符，已持续的音符保持原元音。元音事件本身不会起音；保存、上传及脱机导出均会保留。')
        except ValueError as e:QMessageBox.warning(self,'无法编辑元音',str(e))
    def edit(self,beat,pitch,erase):
        spb=48000*60/self.score['bpm'];start=round(((self.bar.value()-1)*4+beat)*spb);part=self.part.currentIndex()
        events=self.score['events']
        if erase:
            ids={e['serial'] for e in events if e['kind']==0 and e['part']==part and e['note']==pitch and start<=e['sample']<start+spb/4}
            self.score['events']=[e for e in events if not(e['kind'] in (0,1) and e['part']==part and e['note']==pitch and e['serial'] in ids)]
        else:
            serial=max(e['serial'] for e in events)+1 if events else 1
            end=min(self.score['duration_samples']-1,start+round(float(self.length.currentText())*spb))
            if end<=start:return
            for kind,t,vel in [(0,start,self.velocity.value()),(1,end,0)]:events.append(dict(sample=t,kind=kind,part=part,note=pitch,velocity=vel,serial=serial))
            events.sort(key=lambda e:(e['sample'],e['kind']==0,e['part'],e['serial']))
        self.score['edited']=True;self.score['decisions']=[];self.draw()
    def open(self):
        p,_=QFileDialog.getOpenFileName(self,'打开事件作品','','星群作品 (*.json)')
        if p:
            try:
                self.score=model.load(p);self.filename=p;self.parent().restore_performance(self.score.get('performance'));self.bar.setMaximum(self.measure_count())
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
    def export_offline(self,stage=False,workstation=False,video=False,dvi=False,pt8211_dvi=False,shared=False):
        from offline import export_project
        if stage or workstation or video or dvi or pt8211_dvi or shared:
            if self.score.get('engine_profile')!='singer-v1':
                QMessageBox.warning(self,'不能导出融合工程','请先将第16轨角色设为电子歌手，并确认曲谱适合该角色。');return
            from offline_stage import export_stage_project as export_project
            if workstation:from offline_workstation import export_workstation_project as export_project
            if video:from offline_video import export_video_project as export_project
            if dvi:from offline_dvi import export_dvi_project as export_project
            if pt8211_dvi:from offline_pt8211_dvi import export_pt8211_dvi_project as export_project
            if shared:from offline_shared import export_shared_project as export_project
        destination=QFileDialog.getExistingDirectory(self,'选择一个空目录存放完整脱机工程')
        if not destination:return
        try:
            if self.parent() is not None:self.score['performance']=self.parent().capture_performance()
            result=export_project(copy.deepcopy(self.score),destination,autoplay=True)
            self.info.setText(('已导出板载 PT8211 与 DVI 候选；保留扩展接口，需重新构建和验收：' if pt8211_dvi else '已导出 DVI 显示候选工程；需核对实际接线、重新构建和验收：' if dvi else '已导出舞台视频工程（I2S 音频与逻辑 RGB）；需配置真实音频、显示时钟及接口：' if video else '已导出工作站工程（外部 I2S 音频、频谱读取）；需要外部音频时钟、DAC及显示接口配置：' if workstation else '已导出融合源码工程（本地垫、脚踏、麦克风）；先配置全部外设引脚与时序：' if stage else '已导出电子歌手源码工程；先配置麦克风引脚与时序：' if self.score.get('engine_profile')=='singer-v1' else '已导出上电自动演出的工程：')+str(result)+'。需重新构建和验证；当前板上内容未改变。')
        except Exception as e:QMessageBox.warning(self,'不能导出',str(e))
