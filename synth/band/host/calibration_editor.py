"""Explicit measured two-point calibration; no fabricated live ADC readings."""
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QSpinBox,QCheckBox,QPushButton,QMessageBox
from calibration_model import DEFAULT,normalize,fit,pressure,events
class CalibrationEditor(QDialog):
    def __init__(self,desk):
        super().__init__(desk);self.desk=desk;self.setWindowTitle('本地压力垫 · 校准');self.resize(660,440)
        layout=QVBoxLayout(self)
        note=QLabel('适用于接入 MCP3208 的 64 个压力垫。请填写实测 ADC 值；本窗口没有实时采集功能。MIDI 打击垫不使用这套校准。');note.setWordWrap(True);layout.addWidget(note)
        self.channel=QSpinBox();self.channel.setRange(0,63)
        self.baseline=QSpinBox();self.baseline.setRange(0,4095)
        self.gain=QSpinBox();self.gain.setRange(1,65535)
        self.invert=QCheckBox('ADC 数值随压力增加而减小')
        for name,widget in [('通道（0–63）',self.channel),('零点（反向后的 ADC 值）',self.baseline),('定点增益（除以 4096）',self.gain)]:
            row=QHBoxLayout();row.addWidget(QLabel(name));row.addWidget(widget);layout.addLayout(row)
        layout.addWidget(self.invert)
        self.released=QSpinBox();self.released.setRange(0,4095)
        self.pressed=QSpinBox();self.pressed.setRange(0,4095);self.pressed.setValue(4095)
        row=QHBoxLayout();row.addWidget(QLabel('实测释放值'));row.addWidget(self.released);row.addWidget(QLabel('实测最大按压值'));row.addWidget(self.pressed);layout.addLayout(row)
        for label,callback in [('由两个实测值计算',self.calculate),('保存此通道到当前作品',self.store),('发送已保存校准（先总停音）',self.send)]:
            button=QPushButton(label);button.clicked.connect(callback);layout.addWidget(button)
        self.info=QLabel('参数随作品 JSON 保存，并进入脱机导出工程。当前板载试听固件未启用本地 ADC 输入，只有相应外设固件才会应用这些参数。');self.info.setWordWrap(True);layout.addWidget(self.info)
        self.channel.valueChanged.connect(self.load_channel);self.load_channel()
    def load_channel(self):
        c=self.desk.pad_calibration.get(self.channel.value(),DEFAULT)
        self.baseline.setValue(c['baseline']);self.gain.setValue(c['gain']);self.invert.setChecked(c['invert'])
    def calculate(self):
        try:
            c=fit(self.released.value(),self.pressed.value())
            self.baseline.setValue(c['baseline']);self.gain.setValue(c['gain']);self.invert.setChecked(c['invert'])
            self.info.setText(f"按当前两个测量值计算：释放压力 {pressure(self.released.value(),c)}，最大压力 {pressure(self.pressed.value(),c)}。请保存此通道，再保存作品。")
        except ValueError as e:QMessageBox.warning(self,'不能计算',str(e))
    def store(self):
        c=dict(baseline=self.baseline.value(),gain=self.gain.value(),invert=self.invert.isChecked())
        self.desk.pad_calibration.update(normalize({self.channel.value():c}))
        self.info.setText('已保存到当前编辑状态；请在作品编辑器中保存作品 JSON，以便下次恢复。')
    def send(self):
        if not self.desk.port:self.info.setText('未连接 FPGA；校准已保留在编辑状态。');return
        if not self.desk.pad_calibration:self.info.setText('请先保存至少一个通道。');return
        self.desk.panic()
        for event in events(self.desk.pad_calibration):self.desk.enqueue(event)
        self.info.setText('总停音后已排入校准队列。只有本地 ADC 外设固件会应用；请释放全部垫子后再演奏。参数未写入 Flash。')
