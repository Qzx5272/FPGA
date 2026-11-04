"""Read-only stage projection from timestamped FPGA telemetry, never audio inference."""
import time
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QGridLayout,QLabel,QPushButton

class StageState:
    def __init__(self):self.reset()
    def reset(self):self.tracks={};self.latest=None;self.received=None
    def update(self,state,now):
        if state.get('profile')!='band' or not 0<=state['part']<16:return
        self.tracks[state['part']]=(dict(state),now)
        self.latest=dict(state);self.received=now
    def snapshot(self,now,connected):
        fresh=lambda timestamp:connected and timestamp is not None and 0<=now-timestamp<=2.5
        return dict(live=fresh(self.received),latest=self.latest,
            owners=[self.tracks[p][0]['owner'] if p in self.tracks and fresh(self.tracks[p][1]) else None for p in range(16)])

def owner_text(owner):
    if owner is None:return '等待回传 / 已过期'
    if owner==0:return '机器乐手'
    if 17<=owner<=20:return f'本地演奏席 {owner-16}'
    if 1<=owner<=4:return f'MIDI / 上位机席 {owner}'
    return f'来源 {owner}'

class StageView(QDialog):
    def __init__(self,desk,roles):
        super().__init__(desk);self.desk=desk;self.roles=roles
        self.setWindowTitle('星群 · 舞台实时状态');self.resize(1160,780)
        self.setStyleSheet('QDialog{background:#0c1724} QLabel{color:#e4f0f5;font-size:17px;padding:8px} QPushButton{padding:10px;background:#294557;color:white}')
        layout=QVBoxLayout(self)
        title=QLabel('星群  /  FPGA 乐队');title.setStyleSheet('font-size:32px;color:#7de2d1');layout.addWidget(title)
        self.health=QLabel();layout.addWidget(self.health)
        self.position=QLabel();layout.addWidget(self.position)
        grid=QGridLayout();self.cards=[]
        for p,role in enumerate(roles):
            card=QLabel();card.setMinimumHeight(72);self.cards.append(card);grid.addWidget(card,p//4,p%4)
        layout.addLayout(grid)
        self.metrics=QLabel();self.metrics.setWordWrap(True);layout.addWidget(self.metrics)
        self.singer=QLabel();self.singer.setWordWrap(True);layout.addWidget(self.singer)
        note=QLabel('显示 FPGA 回传；不推测逐轨响度、静音状态或歌词。位置为曲谱时间，变速后不等于实际经过时间。')
        note.setWordWrap(True);layout.addWidget(note)
        self.audio_monitor=None
        audio=QPushButton('音频输入 · 波形 / 频谱 / 李萨如');audio.clicked.connect(self.open_audio);layout.addWidget(audio)
        full=QPushButton('全屏 / 窗口');full.clicked.connect(lambda:self.showNormal() if self.isFullScreen() else self.showFullScreen());layout.addWidget(full)
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(100);self.refresh()
    def open_audio(self):
        from audio_monitor import AudioMonitor
        if self.audio_monitor is None:self.audio_monitor=AudioMonitor(self,panic=self.desk.panic)
        self.audio_monitor.show();self.audio_monitor.raise_()
    def closeEvent(self,event):
        if self.audio_monitor is not None:self.audio_monitor.close()
        super().closeEvent(event)
    def refresh(self):
        self.desk.refresh_singer();self.singer.setText(self.desk.singer_label.text())
        state=self.desk.stage_state.snapshot(time.monotonic(),self.desk.port is not None)
        self.health.setText('● FPGA 回传有效' if state['live'] else '○ 未连接或回传超时 · 状态不可信')
        s=state['latest'] if state['live'] else None
        self.position.setText(('自动演出' if s['playing'] else '停止 / 自由演奏')+f'  ·  曲谱位置 {s["song_sample"]/48000:.2f} 秒' if s else '曲谱位置 —')
        for p,owner in enumerate(state['owners']):
            self.cards[p].setText(f'{p+1:02d}  {self.desk.role_name(p)}\n{owner_text(owner)}')
            color='#183c3c' if owner==0 else '#303050' if owner is not None else '#26303c'
            self.cards[p].setStyleSheet(f'background:{color};border-radius:8px;padding:12px;font-size:16px')
        voice_label='乐队音符（不含独立歌手）' if self.desk.board_identity and self.desk.board_identity.get('features',0)&32 else '全局活跃音符'
        self.metrics.setText(f'{voice_label} {s["voices"]}  ·  样本计算 {s["cycles"]} 周期\n期限违例 {s["deadline_miss"]}  ·  削波 {s["clips"]}  ·  拒绝 {s["rejected"]}  ·  回传 CRC 错误 {self.desk.decoder.bad_crc}' if s else '工程计数 —（等待新的有效板端回传）')
    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Space:self.desk.panic()
        else:super().keyPressEvent(event)
