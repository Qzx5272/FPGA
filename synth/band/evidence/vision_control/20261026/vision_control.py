"""Opt-in local camera marker control. FPGA remains the sound generator."""
import time
from PySide6.QtCore import QTimer,Qt
from PySide6.QtGui import QImage,QPixmap,QPainter,QColor,QPen
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QSpinBox
from PySide6.QtMultimedia import QCamera,QMediaCaptureSession,QMediaDevices,QVideoSink
from vision_selection import SelectionGate,red_marker,apply_selection


class VisionControl(QDialog):
    def __init__(self,desk):
        super().__init__(desk);self.desk=desk;self.camera=None;self.running=False
        self.gate=SelectionGate();self.last_frame=-1.;self.capture=QMediaCaptureSession(self)
        self.sink=QVideoSink(self);self.capture.setVideoSink(self.sink)
        self.sink.videoFrameChanged.connect(self.frame)
        self.setWindowTitle('星群 · 视觉选择与演奏融合（实验）');self.resize(760,580)
        layout=QVBoxLayout(self)
        hint=QLabel('将单个红色标记移到目标格，保持约 0.8 秒，再点击确认。\n只选择后续演奏角色；音符由 MIDI / 键盘输入，接管仍由 FPGA 仲裁。画面不镜像。')
        hint.setWordWrap(True);layout.addWidget(hint)
        row=QHBoxLayout();self.devices=QComboBox();row.addWidget(self.devices,1)
        self.start_button=QPushButton('开启摄像头');self.start_button.clicked.connect(self.start);row.addWidget(self.start_button)
        stop=QPushButton('关闭摄像头');stop.clicked.connect(self.stop);row.addWidget(stop)
        layout.addLayout(row)
        self.preview=QLabel('摄像头未开启');self.preview.setMinimumSize(640,360)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter);layout.addWidget(self.preview)
        row=QHBoxLayout();row.addWidget(QLabel('映射到演奏席'));self.seat=QSpinBox();self.seat.setRange(1,4);self.seat.setValue(desk.source());self.seat.valueChanged.connect(lambda:self.gate.reset());row.addWidget(self.seat)
        self.confirm=QPushButton('确认候选');self.confirm.clicked.connect(self.accept_candidate);self.confirm.setEnabled(False);row.addWidget(self.confirm)
        cancel=QPushButton('撤销候选');cancel.clicked.connect(self.cancel);row.addWidget(cancel);layout.addLayout(row)
        self.message=QLabel('仅在本机处理画面，不保存或发送视频；真实相机、光照和误触率尚待验收。');self.message.setWordWrap(True);layout.addWidget(self.message)
        panic=QPushButton('总停音 · 空格');panic.clicked.connect(self.panic);layout.addWidget(panic)
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(100)
        self.refresh_devices()

    def refresh_devices(self):
        self.available=QMediaDevices.videoInputs();self.devices.clear()
        for device in self.available:self.devices.addItem(device.description())
        self.start_button.setEnabled(bool(self.available))

    def start(self):
        index=self.devices.currentIndex();self.stop()
        if not 0<=index<len(self.available):self.message.setText('未检测到摄像头，请连接后重新打开窗口');return
        self.camera=QCamera(self.available[index],self);self.capture.setCamera(self.camera)
        self.camera.errorOccurred.connect(self.camera_error)
        self.camera.activeChanged.connect(self.active_changed)
        self.running=True;self.devices.setEnabled(False);self.start_button.setEnabled(False)
        self.last_frame=-1.;self.camera.start()

    def active_changed(self,active):
        if not active and self.running:
            self.stop();self.message.setText('摄像头已停止；候选已清除')

    def camera_error(self,*_):
        detail=self.camera.errorString() if self.camera else ''
        self.stop();self.message.setText('摄像头不可用：'+detail)

    def stop(self):
        self.running=False;self.gate.reset();self.confirm.setEnabled(False)
        camera=self.camera;self.camera=None
        if camera is not None:camera.stop();self.capture.setCamera(None);camera.deleteLater()
        self.devices.setEnabled(True);self.start_button.setEnabled(bool(getattr(self,'available',[])))
        self.preview.clear();self.preview.setText('摄像头未开启')

    def frame(self,frame):
        if not self.running:return
        now=time.monotonic()
        if now-self.last_frame<.1:return
        self.last_frame=now;self.process_image(frame.toImage(),now)

    def process_image(self,image,now):
        if not self.running:return
        if image.isNull():self.gate.observe(None,now);self.refresh();return
        small=image.scaled(96,64,Qt.AspectRatioMode.IgnoreAspectRatio).convertToFormat(QImage.Format.Format_RGBA8888)
        marker=red_marker(bytes(small.constBits()),small.width(),small.height(),small.bytesPerLine())
        self.gate.observe(marker['part'] if marker else None,now)
        picture=image.scaled(640,360,Qt.AspectRatioMode.KeepAspectRatio).convertToFormat(QImage.Format.Format_ARGB32)
        painter=QPainter(picture);painter.setPen(QPen(QColor('white'),2))
        w=picture.width();h=picture.height()
        for column in range(1,4):painter.drawLine(column*w//4,0,column*w//4,h)
        painter.drawLine(0,h//2,w,h//2)
        for part in range(8):
            x=part%4*w//4;y=part//4*h//2
            painter.fillRect(x+2,y+2,w//4-4,24,QColor(0,0,0,170))
            painter.drawText(x+6,y+20,self.desk.role_name(part))
        if marker:
            painter.setPen(QPen(QColor('#00ff88'),3));painter.drawEllipse(int(marker['x']*w)-7,int(marker['y']*h)-7,14,14)
        painter.end();self.preview.setPixmap(QPixmap.fromImage(picture));self.refresh(now)

    def refresh(self,now=None):
        now=time.monotonic() if now is None else now
        part=self.gate.candidate(now) if self.running else None
        self.confirm.setEnabled(part is not None)
        self.confirm.setText('确认：'+self.desk.role_name(part) if part is not None else '等待稳定的视觉候选')

    def accept_candidate(self):
        part=self.gate.candidate(time.monotonic()) if self.running else None
        if part is None:self.message.setText('候选不存在或已过期，请重新保持标记');return
        success,message=apply_selection(self.desk,self.seat.value(),part)
        self.message.setText(message)
        if success:self.gate.consume()
        self.refresh()

    def cancel(self):
        self.gate.consume();self.message.setText('已撤销；移开标记后再选择');self.refresh()

    def panic(self):
        self.gate.consume();self.desk.panic();self.refresh()

    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Space:self.panic()
        elif len(event.text())==1 and event.text().upper() in 'ASDFGHJK':self.desk.keyPressEvent(event)
        else:super().keyPressEvent(event)

    def keyReleaseEvent(self,event):
        if len(event.text())==1 and event.text().upper() in 'ASDFGHJK':self.desk.keyReleaseEvent(event)
        else:super().keyReleaseEvent(event)

    def showEvent(self,event):
        if not self.running:self.refresh_devices()
        super().showEvent(event)

    def hideEvent(self,event):
        self.stop();super().hideEvent(event)
