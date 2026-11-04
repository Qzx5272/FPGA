"""Explicitly started PC audio input monitor; never generates or forwards audio.
QAudioSource API: https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QAudioSource.html
PCM is transient, bounded and never written to disk by this module.
"""
import math,cmath,struct,time
from collections import deque
from PySide6.QtCore import QTimer,QPointF,Qt
from PySide6.QtGui import QPainter,QColor,QPolygonF
from PySide6.QtWidgets import QDialog,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox

def spectrum(samples):
    """1024-point Hann-windowed one-sided peak amplitude, in dBFS."""
    n=1024
    if len(samples)<n:return []
    window=[0.5-0.5*math.cos(2*math.pi*i/(n-1)) for i in range(n)]
    a=[complex(v*w) for v,w in zip(samples[-n:],window)]
    j=0
    for i in range(1,n):
        bit=n>>1
        while j&bit:j^=bit;bit>>=1
        j^=bit
        if i<j:a[i],a[j]=a[j],a[i]
    size=2
    while size<=n:
        step=cmath.exp(-2j*math.pi/size)
        for start in range(0,n,size):
            w=1
            for k in range(size//2):
                u=a[start+k];v=w*a[start+k+size//2]
                a[start+k]=u+v;a[start+k+size//2]=u-v;w*=step
        size*=2
    scale=sum(window)
    return [20*math.log10(max(1e-6,abs(a[k])*(1 if k in (0,n//2) else 2)/scale)) for k in range(n//2+1)]

class PCMWindow:
    def __init__(self,rate=48000,channels=2,encoding='h'):
        if rate<=0 or not 1<=channels<=8 or encoding not in ('B','h','i','f'):raise ValueError('Unsupported PCM format')
        self.rate=rate;self.channels=channels;self.encoding=encoding
        self.frame=struct.Struct('<'+encoding*channels);self.pending=b''
        self.left=deque(maxlen=2048);self.right=deque(maxlen=2048);self.received=None
    def feed(self,data,now):
        data=self.pending+data;n=len(data)//self.frame.size*self.frame.size
        self.pending=data[n:]
        # Drop older complete frames if the UI was delayed, preserving alignment.
        for values in self.frame.iter_unpack(data[max(0,n-2048*self.frame.size):n]):
            def normalized(v):
                x=(v-128)/128 if self.encoding=='B' else v/(32768 if self.encoding=='h' else 2147483648) if self.encoding!='f' else v
                return x if math.isfinite(x) else 0.0
            self.left.append(normalized(values[0]));self.right.append(normalized(values[1] if self.channels>1 else values[0]))
        if n:self.received=now
    def snapshot(self,now):
        if self.received is None or not 0<=now-self.received<=0.5:return None
        left=list(self.left);right=list(self.right)
        positive_limit={'B':127/128,'h':32767/32768,'i':2147483647/2147483648,'f':1}[self.encoding]
        return dict(left=left,right=right,db=spectrum(left),rate=self.rate,channels=self.channels,
                    peak=max(map(abs,left+right),default=0),clipped=sum(x<=-1 or x>=positive_limit for x in (left if self.channels==1 else left+right)))

class AudioCanvas(QWidget):
    def __init__(self):super().__init__();self.data=None;self.setMinimumSize(640,460)
    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#0c1724'));p.setPen(QColor('#bce4e5'))
        if not self.data:p.drawText(20,35,'等待新的音频输入 · 无有效波形');return
        d=self.data;w=self.width();h=self.height();row=h/3
        def line(points,color):
            p.setPen(QColor(color));p.drawPolyline(QPolygonF([QPointF(x,y) for x,y in points]))
        p.drawText(12,20,'波形 · 左 / 右（单声道时复制显示）')
        for data,color in ((d['left'],'#7de2d1'),(d['right'],'#f7bb72')):
            values=data[-512:];line([(20+i*(w-40)/max(1,len(values)-1),row/2-max(-1,min(1,v))*(row/2-25)) for i,v in enumerate(values)],color)
        p.setPen(QColor('#bce4e5'));p.drawText(12,int(row+20),f'左声道频谱 · Hann 1024 · 0 — {d["rate"]/2000:g} kHz · 0 至 −120 dBFS')
        line([(20+i*(w-40)/max(1,len(d['db'])-1),row+30+(max(-120,min(0,v))/-120)*(row-40)) for i,v in enumerate(d['db'])],'#7de2d1')
        p.setPen(QColor('#bce4e5'));p.drawText(12,int(2*row+20),'李萨如 · X=左声道，Y=右声道'+(' · 单声道，无立体声相位信息' if d['channels']==1 else ''))
        scale=row/2-25
        line([(w/2+max(-1,min(1,l))*scale,2.5*row-max(-1,min(1,r))*scale) for l,r in zip(d['left'][-512:],d['right'][-512:])],'#b8a4f3')

class AudioMonitor(QDialog):
    def __init__(self,parent=None,panic=None):
        super().__init__(parent);self.setWindowTitle('星群 · 音频输入监测');self.resize(920,650)
        self.panic=panic
        self.source=None;self.io=None;self.window=None;self.devices=[]
        layout=QVBoxLayout(self);row=QHBoxLayout();self.inputs=QComboBox();row.addWidget(self.inputs,1)
        refresh=QPushButton('刷新输入');refresh.clicked.connect(self.refresh_devices);row.addWidget(refresh)
        self.begin=QPushButton('开始监测');self.begin.clicked.connect(self.start);row.addWidget(self.begin)
        end=QPushButton('停止');end.clicked.connect(lambda:self.stop('已停止'));row.addWidget(end);layout.addLayout(row)
        if panic:
            emergency=QPushButton('FPGA 总停音 · Ctrl+Space');emergency.clicked.connect(panic);layout.addWidget(emergency)
        label=QLabel('来源是所选电脑音频输入。监测 FPGA 时，将其音频输出接至合适的线路输入；本窗口不播放、不保存音频。');label.setWordWrap(True);layout.addWidget(label)
        self.status=QLabel('未开始');layout.addWidget(self.status);self.canvas=AudioCanvas();layout.addWidget(self.canvas,1)
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(50)
        self.refresh_devices()
    def refresh_devices(self):
        if self.source:return
        try:
            from PySide6.QtMultimedia import QMediaDevices
            self.devices=QMediaDevices.audioInputs();self.inputs.clear()
            for d in self.devices:self.inputs.addItem(d.description())
            self.begin.setEnabled(bool(self.devices))
            if not self.devices:self.status.setText('未找到音频输入')
        except Exception as exc:self.status.setText('音频输入不可用：'+str(exc));self.begin.setEnabled(False)
    def start(self):
        from PySide6.QtMultimedia import QAudioSource,QAudioFormat
        self.stop('准备输入')
        index=self.inputs.currentIndex()
        if not 0<=index<len(self.devices):return
        device=self.devices[index];fmt=QAudioFormat();fmt.setSampleRate(48000);fmt.setChannelCount(2);fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(fmt):fmt=device.preferredFormat()
        enc={QAudioFormat.SampleFormat.UInt8:'B',QAudioFormat.SampleFormat.Int16:'h',QAudioFormat.SampleFormat.Int32:'i',QAudioFormat.SampleFormat.Float:'f'}.get(fmt.sampleFormat())
        try:self.window=PCMWindow(fmt.sampleRate(),fmt.channelCount(),enc)
        except ValueError:self.stop('设备格式不支持');return
        self.source=QAudioSource(device,fmt,self);self.source.setBufferSize(max(4096,fmt.bytesForDuration(100000)))
        self.io=self.source.start()
        if self.io is None:self.stop('无法启动音频输入');return
        self.io.readyRead.connect(self.read_input);self.inputs.setEnabled(False);self.begin.setEnabled(False)
        self.status.setText(f'等待输入：{device.description()} · {fmt.sampleRate()} Hz / {fmt.channelCount()} 声道')
    def read_input(self):
        if self.io is not None and self.window is not None:self.window.feed(bytes(self.io.readAll()),time.monotonic())
    def refresh(self):
        if self.source:
            from PySide6.QtMultimedia import QAudio
            if self.source.error()!=QAudio.Error.NoError:self.stop('输入错误：'+self.source.error().name);return
            self.canvas.data=self.window.snapshot(time.monotonic())
            if self.canvas.data:
                d=self.canvas.data;peak=20*math.log10(max(1e-6,d['peak']))
                self.status.setText(f'{self.inputs.currentText()} · {d["rate"]} Hz / {d["channels"]} 声道 · 当前窗口峰值 {peak:.1f} dBFS · 满量程采样 {d["clipped"]}')
            else:self.status.setText('等待输入 / 超过 0.5 秒没有新采样')
        self.canvas.update()
    def stop(self,message='已停止'):
        source=self.source;self.source=None
        if source:source.stop();source.deleteLater()
        self.io=None;self.window=None;self.canvas.data=None;self.canvas.update()
        self.inputs.setEnabled(True);self.begin.setEnabled(bool(self.devices));self.status.setText(message)
    def hideEvent(self,event):self.stop();self.timer.stop();super().hideEvent(event)
    def showEvent(self,event):self.timer.start();super().showEvent(event)
    def keyPressEvent(self,event):
        if self.panic and event.key()==Qt.Key.Key_Space and event.modifiers()&Qt.KeyboardModifier.ControlModifier:self.panic();event.accept()
        else:super().keyPressEvent(event)
