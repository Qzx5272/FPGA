# 星群 V2 实装记录 — 2026-10-18

## 可以直接操作的功能

根目录 `启动星群演奏台.cmd` 启动 PySide6 本地桌面上位机，自动打开 COM12 并验证固件 v2 回传。板卡是已实际识别的 Tang Mega 138K Pro / GW5AST-138B，JTAG ID 0x0001081B。板载 3.5 mm 耳机输出连接有源音箱 AUX。

- A/S/D/F/G/H/J/K 或鼠标：C 大调八键；八度 C2–C6，最上方键到 C7；最多八音复音。
- 柔和、明亮、拨弦三预设；明亮度、Attack、Release 旋钮，主音量、触发力度滑块。
- 开始伴奏：FPGA 运行 C–F–G–C 和声及旋律的 16 步八分音符循环。速度 40–166 BPM。上位机没有发送逐音伴奏事件。
- 伴奏期间选择人声，可叠加单声部元音；“试听你好”运行既有板端 128 帧参数短句。不是输入任意文本的歌声模型。人声保持独立总线，不再必然替换伴奏。
- 空格 / 全部停止 / 窗口失焦 / 通信失联停止所有音；伴奏停止按钮允许尾音释放。切音色会重启伴奏第一步。
- 电平是 FPGA 数字样本峰值，图形是包络参数示意；通信往返不是声学延迟。

## HDL 修改

`engine.v` 顺序调度一个 `hq_sine_quarter.v`，每帧发出 24 个相位请求；四级流水、每周期一个结果，接收到每个音符三个分量后完成包络/力度/混音。采样触发后 40 个 50 MHz 周期内完成，低于 1041/1042 周期采样间隔。表是四分之一周期 1024×34 位成对端点，恢复等价 4096 点正弦并以相位低 20 位插值，内部 18 位，输出缩为 16 位。数据是数学波形，不是录音 PCM。

`auto_accompaniment.v` 在 48 kHz 采样使能时累加 BPM，每跨越 1,440,000 单位前进一步，表示一个八分音符；最后 15% 为松键间隔。无变量除法器。手奏与伴奏位图合并，同音共享槽；不宣称独立多人声部所有权。

`top.v` 将乐器与人声各乘 0.5 再加，17 位中间结果避免两条 16 位总线溢出。人声模式最多九个活跃声部，乐器模式最多八个。现有元音和短句算法未升级为任意歌词系统。

`control.v` 协议第 13 字节 bit0 panic、bit1 自动伴奏、bits7:2 速度；看门狗同时关闭自动伴奏。回传版本升级为 2，上位机拒绝把旧固件当作新版已连接。

## 已取得的验证

- UART 全字节、包校验/原子更新、看门狗、PT8211 与独立 I2S 格式、八声部引擎、元音、短句共六组原有 RTL 测试通过。
- 新增自动伴奏测试验证 96 BPM 时每步 15,000 样本、120 BPM 时每步 12,000 样本、松键间隔、停止和 panic；控制测试覆盖新增速度/播放字段。
- 桌面三个交互测试及协议测试通过；实际 Windows 字体渲染截图已检查。
- 仿真音频：A4 FFT 440.000 Hz；八个基本音均存在；测试最大绝对样本 21,265，小于 32,767；释放和拨弦末段为数字零。不是 DAC 的失真/噪声实测。
- Gowin 1.9.12.03 完整综合与布局布线：4695 LUT、2100 ALU、3271 FF、26/340 BSRAM、41/298 DSP；50 MHz 约束，报告 Fmax 57.198 MHz，setup/hold 违例均为零。
- SRAM 加载后板上通过固件 v2 回传、1/8 声部、释放、非零输出峰值、500 ms 看门狗测试。
- 板上集成测试通过自动伴奏、伴奏与“你好”同时活跃、伴奏与元音同时活跃、panic 静音和通信超时。记录在 `test-output/duet_hardware.json`。测试发出短暂低音量声音；没有麦克风回录或主观听感结论。
- 15:49 开机 Flash 编程与读回校验成功（日志明确 `Program and Verify Flash successfully`），随后 JTAG Reprogram 从 Flash 重新加载，固件 v2 硬件检查再次通过。没有执行物理拔电重插。
- 发布位流 SHA-256：`B10366835BDEDE336A9350DE706C68241E5A056D0E94AA9F47958466CA0FF17A`。

## 仍保留的工程边界

板载 PT8211 为 16 位右对齐格式，本次继续使用真实硬件对应的格式。外置标准 I2S DAC、音频 PLL、全端到端延迟、实体多维传感器尚未验收。工具对时钟入口使用通用路由有提示，内部约束的时序检查通过；当前约束没有外部 DAC 的输入延迟模型，不能据此声称模拟音频性能达标。

三谐波并非商业钢琴/弦乐建模。此版将研究中的插值核和自动控制带到现有板上，但 V3 的 4096 分音池、物理弦/模态、混响、任意普通话音素库、多轨歌声和实体多人交互仍未实现。八度范围内最高第三谐波约 12.56 kHz，不越过 48 kHz 的 Nyquist 频率。

## 复现入口

```
.venv\Scripts\python.exe synth/tests/test_host.py
.venv\Scripts\python.exe synth/tests/test_ui.py
.venv\Scripts\python.exe synth/tools/run_tests.py
powershell -ExecutionPolicy Bypass -File synth/tools/build.ps1
powershell -ExecutionPolicy Bypass -File synth/tools/load_sram.ps1
.venv\Scripts\python.exe synth/tools/hardware_check.py --port COM12 --sound
.venv\Scripts\python.exe synth/tools/check_duet.py
```

硬件检查先关闭演奏台以释放 COM12。`analyze_samples.py` 需要 NumPy；当前使用 Codex 缓存 Python 的 NumPy 执行，不是桌面上位机的运行依赖。原有开机位流备份在 `release/archive-20261018/aurora_synth.fs`。
