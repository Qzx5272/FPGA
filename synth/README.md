# 星群 STARCLUSTER — FPGA 演奏台（固件 v2）

2026-10-18：已实现桌面键盘、三个旋钮、音量与力度、FPGA 自动伴奏及人声混音。双击根目录 `启动星群演奏台.cmd` 自动连接 COM12；串口号变化时在界面选择实际端口。电脑只传控制包。

### USB MIDI 打击垫

2026-10-18 音量与配色调整：上位机默认主音量改为 127/127，MIDI Note On 力度乘 1.5 后封顶 127；界面力度滑块显示补偿后的数值，MIDI 状态显示原始消息值。此补偿提升普通敲击响度，不改变 FPGA 混音余量，也不能把本来已满力度的声音继续放大。

已用官方 MIDI Suite 1.15.0 对 Preset 1 / Pad Bank 3 配色并执行保存：Pad 1–4 青绿、5–8 蓝、9–12 紫、13–16 橙。`midi-presets/SMC-Pocket-original.spp` 为修改前导出，`SMC-Pocket-starcluster.spp` 为配色文件。通过单垫颜色导出差分确认 RGB 字段后，仅修改当前 bank 的 16 组 RGB，其余字节完全保留；导入后编辑器显示四排配色。保存后的重新读取尚未完成（编辑器随后关闭），未做断电保留测试。软件 MIDI 端口与 FPGA 已恢复连接。

官方说明的可编程项目包括 Note、CC Toggle/Momentary、Program Change、自定义 SysEx、通道、力度范围、灯色、Aftertouch、Note Repeat/Tempo/Swing/Latch 等；星群目前仅消费音符/力度及停止消息。可进一步把 CC 映射到音量、明亮度、起音、释放、伴奏速度，把按钮映射到音色与伴奏开关，但本次未修改这些控制映射。官方资料：<https://manualf.oss-cn-hongkong.aliyuncs.com/manual/MIDI-KEYBOARD/SMC-PAD-POCKET.pdf>；编辑器下载：<https://www.m-vave.com/download>。

已接入 Windows 识别的 SMC-PAD Pocket。信号路径：打击垫 USB MIDI → 上位机映射音符/力度 → UART → FPGA 合成 → 板载耳机口。启动时自动打开第一个 MIDI 输入；可在 MIDI 下拉框选择其他端口。SMC-PAD Pocket 有三个输入端口，默认选择 `SMC-PAD Pocket 0`；如敲击时没有 MIDI 提示，断开 MIDI 后尝试另一个端口。

默认 MIDI 音符 36–43 映射屏幕 C/D/E/F/G/A/B/高 C；接收所有通道，包括常见打击垫的通道 10。可点击“学习八个垫子”，依次敲八个不同垫子，顺序对应这八个音。学习期间不发声，完整映射保存到 `host/midi_mapping.json`，下次启动恢复。学习映射绑定通道和音符；更改硬件银行/通道后可重新学习。

敲击力度 1–127 会传给 FPGA，Note Off 或力度为零的 Note On 释放相应音符。界面可显示收到的音符、力度及按下键数。USB 拔出检查约每秒一次；断开 MIDI 会释放 MIDI 按键，电脑键盘仍可演奏。空格/全部停止清空所有输入。当前固件共用八个音符槽，不支持把每个 MIDI 音符原样映射到完整半音音域，也未加入延音踏板、弯音、触后和硬件旋钮 CC 映射。多个来源演奏同一个槽时合并持有；该槽以首次触发力度为准。极密集事件的独立力度精度受现有共享力度字段和串口队列限制。

MIDI 解析与桌面混合输入自动测试已通过，实际 MIDI 端口已成功打开；实体敲击到音箱的听感与延迟需现场演奏确认。本次仅更新上位机，无需重新烧录 FPGA。后端参考 [python-rtmidi 官方 API](https://spotlightkid.github.io/python-rtmidi/rtmidi.html)。

- 乐器引擎改为共享 4096 点、18 位插值正弦核，在每个采样周期内顺序计算 24 个分量；8 个音符仍各共用自己的包络，不等于 24 个独立音符。
- 自动伴奏由 `rtl/auto_accompaniment.v` 在 FPGA 采样时钟下执行，C 大调 16 步循环，40–166 BPM、步进 2 BPM。支持手奏叠加；乐器手奏与伴奏共用八个音符槽，同音合并。
- 人声模式下伴奏与单声部元音 / 固定“你好”参数短句并行合成，两个音频总线各取半幅再混合。最多 8 个乐器音符加 1 个人声。不是任意歌词歌唱系统。
- 停止伴奏允许乐器尾音释放；空格、全部停止、窗口失焦、500 ms 通信看门狗会停止所有声音。切换音色会清音并从第一步重新开始伴奏。
- 协议回传版本为 2。控制包字节 13：bit0 全部停止，bit1 自动伴奏，bits7:2 速度编码，BPM=40+2×编码。字节 5 音色 3 表示人声；字节 6 的 0–7 为音素，8/9 为正常/慢速“你好”。

本次实现和验证详情见 [V2_IMPLEMENTATION.md](V2_IMPLEMENTATION.md)。V3 研究报告中的大规模分音池、物理建模、多轨任意歌词及实体多人传感器仍是后续工作，未混入本版完成声明。

适用于当前已连接的 Tang Mega 138K Pro，电脑通过 JTAG/UART 接口控制 FPGA，开发板 3.5mm 耳机口接有源音箱 AUX。电脑只发送控制指令，不生成声音、不播放预录 PCM。

## 使用

1. 开发板正常供电，USB 接 JTAG/UART，3.5mm 音频线接音箱 AUX，音箱从小音量开始。
2. 当前固件已写入板载 Flash 并通过读回校验，已验证从 Flash 重新加载后正常运行。断电再上电会自动加载，无需每次烧录；等待约 5 秒后连接上位机。以后更新开机固件可双击项目根目录 `烧录FPGA开机程序.cmd`，它会替换 Flash 内容并校验。`加载FPGA临时程序.cmd` 仍保留供调试，仅写 SRAM。烧录前先关闭占用下载接口的其他工具。
3. 双击 `启动合成器.cmd`，选择当前设备串口 COM12，点击连接。只有收到正确版本的 FPGA 回传才显示已连接。端口号以后可能变化。
4. A/S/D/F/G/H/J/K 对应 C/D/E/F/G/A/B/高 C；支持同时按键及鼠标。硬件键盘自身可能有多键冲突。
5. 明亮度改变第二、第三谐波强度；Attack 控制起音；Release 控制松键尾音。主音量与力度滑块分别控制整体增益和新触发声部的力度。力度是软件设定值，不是真实压力测量。
6. 柔和、明亮、拨弦三种预设会设置推荐参数，随后仍可旋钮调节。八度 C2–C6（最高键 C7）；切换八度时先停音。
7. 空格或“全部停止”立即清除声部。窗口失去焦点会停音；失去有效控制包 500 ms 后 FPGA 自行静音。

## 工程结构

中文人声资料见 [发音词库说明](voice/README.md) 和 [移植说明](voice/PORT.md)：已新增单声部元音与“你好”试唱原型，尚不支持任意歌词歌曲。人声模式中明亮度旋钮停用，字段用于音素编号；其他演奏控件保留。

“你好”已升级为 FPGA 内部控制的连续参数短句，界面提供“试听‘你好’”和“慢速对比”。短句模式的音高与包络由内部参数谱决定，主音量和力度可调。清晰度需要试听确认。

- `host/app.py`：PySide6 桌面控制台、三个旋钮、滑块、键盘事件、设备回传。
- `host/protocol.py`：完整状态协议及回传解析。
- `rtl/engine.v`：8 个独立相位与包络声部，每声部 3 个实时正弦分量；共享 `hq_sine_quarter.v` 插值核与压缩数学正弦表，非录音采样。
- `rtl/audio_serial.v`：48 kHz 双声道串行输出；默认 PT8211 模式，另有可独立验证的标准 I2S 模式。
- `rtl/control.v` / `uart.v` / `telemetry.v`：包校验、原子参数更新、看门狗、UART 收发及反馈。
- `constraints/`：引脚与 50 MHz 时钟约束。
- `build.tcl`：Gowin 构建入口；`tools/build.ps1` 构建并复制发布位流。
- `tests/`：UART、通信协议、合成器、音频时序及桌面控件测试。
- `release/aurora_synth.fs`：当前板卡可临时加载的位流。
- `test-output/`：本机验证输出，不纳入源代码版本控制。

## 音频与时序边界

板载 PT8211 是 16 位右对齐 DAC，**不是标准 I2S DAC**。本固件真实板端输出采用它要求的格式，WS 低为右、高为左；当前左右声道播放相同混音。标准 I2S 模块模式存在于源代码并由独立接收测试验证，但没有接到物理 I2S DAC，不能据此宣称已完成赛题的外部 I2S 验收。最终参赛若严格要求标准 I2S DAC，可接外置 I2S DAC，并按实际模块核定引脚与时钟。

50 MHz 系统时钟使用分数分频产生平均 48 kHz 采样节奏。串行时钟边沿存在最多一个系统周期（20 ns）的量化抖动。此原型尚未使用低抖动音频 PLL/外部音频时钟，不以音频质量测试达标交付。ADSR 步长为 16 位整数，界面毫秒值是目标，实际时间有量化误差；释放时间按满幅包络标定，从较低保持电平释放会更短。

音量和明亮度逐采样平滑；力度在触发时锁存。ADSR 衰减和保持值由预设决定。统一音量采用八声部保守混音余量，避免多键叠加溢出。界面显示的是 FPGA 输出峰值，不是麦克风采样；包络图明确为参数示意。

界面的“通信往返”是串口往返时间，受 USB 缓冲影响，**不是按键到音箱的音频延迟**。完整端到端 ≤10 ms 需要实际测量，目前不宣称已经达标。电脑交互属于本阶段开发替代，最终赛题的传感器多维交互仍需实现/确认。

## 通信协议 v2

115200 baud、8N1。每次发送完整 15 字节状态，键事件立即发送，旋钮变更合并约 8 ms，静止时每 100 ms 保活。

| 字节 | 定义 |
|---|---|
| 0–1 | A5 5A |
| 2 | 序号 |
| 3 | 8 键位图 |
| 4 | 起始八度 2–6 |
| 5 | 音色 0–3（3 为人声） |
| 6 | 明亮度 0–255 |
| 7 | 音量 0–127 |
| 8 | 力度 0–127 |
| 9–10 | Attack 每采样增量，小端，非零 |
| 11–12 | Release 每采样减量，小端，非零 |
| 13 | bit0 全部停止；bit1 自动伴奏；bits7:2 编码速度 |
| 14 | 字节 2–13 异或校验 |

回传 10 字节：5A A5、序号、手奏键位图、活跃声部数、峰值低字节、峰值高字节、在线标志、版本 2、字节 2–8 异或校验。高频发送时回传可能合并/跳过，界面以最近有效回传为准。回传键位图不包含自动伴奏，活跃声部和峰值包含实际混音。

## 构建与测试

本机 Gowin 路径为 `D:/Gowin/Gowin_V1.9.12.03_x64`。构建目标依据官方 Pro 示例选择 GW5AST-138B / GW5AST-LV138FPG676AC1/I0，并启用 CPU 管脚 GPIO 复用。实际 SRAM 下载器已接受该目标。许可证只配置在本机 IDE，未复制进项目。

```powershell
.\.venv\Scripts\python.exe synth/tests/test_host.py
.\.venv\Scripts\python.exe synth/tests/test_ui.py
.\.venv\Scripts\python.exe synth/tools/run_tests.py
powershell -File synth/tools/build.ps1
.\.venv\Scripts\python.exe synth/tools/hardware_check.py --port COM12
```

`hardware_check.py --sound` 会短暂低音量发声，结束后停音。RTL 仿真工具使用项目 tmp 下便携 OSS CAD Suite 的 Icarus。

## 依据

- 既有方案记录：2026-10-07《汇总138K Pro比赛开发方案》；当前用户要求以电脑控件替代实体面板。
- [Sipeed 官方板卡说明](https://wiki.sipeed.com/hardware/zh/tang/tang-mega-138k/mega-138k-pro.html)
- [官方音频示例](https://github.com/sipeed/TangMega-138KPro-example/tree/main/audio/audio_sinewave)
- [Pro Dock 原理图目录](https://dl.sipeed.com/shareURL/TANG/Mega_138K_Pro/02_Schematic)，4071f3 第 5/6/18 页核定串口 N16/P15、音频 E22/F24/G24、放大器使能 H17。
- [PT8211 厂商资料](https://www.princeton.com.tw/en-us/Products/Multi-Media-Audio/Digital-to-Analog-Converter/DTAC-PT8211)
- [官方赛题](https://www.gowinsemi.com.cn/university/match2026)
