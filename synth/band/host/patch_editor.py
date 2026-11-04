"""Performance envelope editor. Milliseconds are converted to bounded RTL rates."""
import math
from PySide6.QtWidgets import QDialog,QFormLayout,QDoubleSpinBox,QPushButton,QLabel
class PatchEditor(QDialog):
    def __init__(self,desk):
        super().__init__(desk);self.desk=desk;self.setWindowTitle('当前乐手 · 起音与尾音');layout=QFormLayout(self)
        self.attack=QDoubleSpinBox();self.attack.setRange(.1,1300);self.attack.setValue(5.3);self.attack.setSuffix(' ms')
        self.decay=QDoubleSpinBox();self.decay.setRange(.1,5000);self.decay.setValue(1179);self.decay.setSuffix(' ms')
        self.sustain=QDoubleSpinBox();self.sustain.setRange(0,100);self.sustain.setValue(100);self.sustain.setSuffix(' %')
        self.release=QDoubleSpinBox();self.release.setRange(.1,5000);self.release.setValue(37);self.release.setSuffix(' ms')
        for label,widget in [('起音时间',self.attack),('衰减时间',self.decay),('持续音量',self.sustain),('释放时间',self.release)]:layout.addRow(label,widget)
        layout.addRow(QLabel('适用于贝斯、键盘、主奏及合唱；鼓保持专用的打击包络。'))
        for name,values in [('打击键盘',(.2,1179,0,37)),('持续主奏',(5.3,1179,100,74)),('柔和合唱',(40,2358,82,295))]:
            button=QPushButton(name);button.clicked.connect(lambda checked=False,v=values:self.preset(v));layout.addRow(button)
        apply=QPushButton('应用到当前演奏角色');apply.clicked.connect(self.apply);layout.addRow(apply)
        self.info=QLabel('衰减与释放时间表示衰减约 60 dB 的时间，实际值取最近可用档位。');self.info.setWordWrap(True);layout.addRow(self.info)
    def preset(self,values):
        for widget,value in zip((self.attack,self.decay,self.sustain,self.release),values):widget.setValue(value)
        self.apply()
    def load_current(self):
        values=self.desk.patch_values.get(self.desk.part.currentIndex(),{})
        for parameter,widget in ((4,self.attack),(5,self.decay),(6,self.sustain),(7,self.release)):
            if parameter not in values:continue
            raw=values[parameter]
            shown=65535/(max(1,raw)*48) if parameter==4 else raw*100/16383 if parameter==6 else 2**raw*math.log(1000)/48
            widget.setValue(shown)
    def apply(self):
        values=[max(1,min(16383,round(65535/(self.attack.value()*48)))),max(0,min(15,round(math.log2(self.decay.value()*48/math.log(1000))))),round(self.sustain.value()*16383/100),max(0,min(15,round(math.log2(self.release.value()*48/math.log(1000)))))]
        for parameter,value in enumerate(values,4):self.desk.parameter(parameter,value)
        self.info.setText('参数已排入发送队列；保存作品可保存参数。' if self.desk.port else '未连接 FPGA；参数已存入当前编辑状态，可随作品保存。')
