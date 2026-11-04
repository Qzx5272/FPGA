# INMP441 + PCM5102 双向 I²S 联调

本目录是第2、5项的专用实物联调固件，先独立验证输入和输出。它不包含完整乐器、上位机控制或DVI显示，不修改 `CURRENT_RELEASE.json`。旧 PT8211 工作站 Flash 保留。

## 固件行为

- 默认静音，但持续输出 BCLK/LRCK，保证麦克风和 DAC 时钟连续。
- 板载 S0：约1kHz正弦测试音，双声道相同，峰值约-30dBFS。
- 板载 S1：INMP441左声道直通到DAC左右声道，固定4倍增益、饱和保护。
- 板载 S2：静音。PLL失锁后重新锁定也回到静音。
- 麦克风启动保留8192帧（约171ms）等待，覆盖器件的262144个SCK启动周期。
- 板载 PT8211 功放保持关闭。声音从PCM5102的模拟输出端接出。
- S0/S1/S2与LCD触摸接口复用；使用本固件时不连接触摸控制信号。

## 信号接线（断电后操作）

连接器编号按Pro Dock官方原理图和项目已核对的引脚表。必须认准J23第1针标记，不按照片左右猜针序。

| FPGA排针 | FPGA球位 | 外设端 |
|---|---|---|
| **J23-5** | W21 | **仅 PCM5102 BCK** |
| **J23-6** | Y21 | **仅 PCM5102 LCK/LRCK** |
| **J23-7** | P21 | PCM5102 DIN |
| **J23-8** | U17 | INMP441 SD |
| **J23-37** | V19 | **仅 INMP441 SCK** |
| **J23-38** | W19 | **仅 INMP441 WS** |
| **J23-12** | GND | PCM5102 GND；模块SCK在模块侧接此地 |
| **J24-3** | GND | INMP441 GND；L/R在模块侧接地 |
| **J23-11** | 5V | PCM5102 VIN（照片为常见带稳压紫板，首次单独供电检查A3V3约3.3V） |
| J24-1或J24-2 | 3.3V | INMP441 VDD（确认实物针号后） |

INMP441的L/R接GND，选择左声道。如CHIPEN引出，应为高电平使能。VDD使用3.3V，不能接J23-11的5V。SD到GND建议100kΩ下拉；FPGA内部弱下拉已启用，外部电阻按模块已有元件情况补齐。每块模块电源附近有100nF去耦。

按用户要求，两模块全部音频信号使用不同物理排针，不做一根排针分接两模块。FPGA内部仍由同一个时钟源产生同步波形，保证输入输出采样率一致；电源地在板内相通是必须的。J23-37/38来自新旧两版官方原理图，未占用当前面板/蓝牙/USB预留信号。尽量使用短线并伴随地线。J23不能同时插入占用这些信号的SDRAM扩展。

## PCM5102 的 SCK、FLT、FMT 不能混淆

| 脚位 | 本方案配置 |
|---|---|
| BCK | 接J23-5，这是音频位时钟 |
| LCK/LRCK | 接J23-6，这是左右声道时钟 |
| DIN | 接J23-7 |
| SCK（如果引出） | 系统/MCLK输入，本方案三线I²S使用BCK恢复时钟，按模块电路将SCK拉低；**不是接INMP441的SCK** |
| FMT | I²S应为低；可能已在背面焊盘固定，需确认 |
| FLT | 滤波延迟选择；低为普通延迟，高为低延迟。本次用低；**不等于FMT** |
| XSMT/XMT | 高电平解除静音；只用模块的3.3V逻辑电源，不接5V |
| DEMP（若引出） | 低，关闭去加重 |
| VIN | 照片为VIN、A3V3、H1L～H4L的常见带稳压紫色模块，与参考模块布局一致：VIN接5V。首次只接电源，测A3V3对AGND约3.3V再接信号。A3V3不是5V输入 |
| L/R模拟输出 | 接有源音箱AUX或功放线路输入，不直接驱动无源喇叭或低阻耳机 |

已查看用户正反面照片：排针有VIN、GND、LRCK、DIN、BCK、SCK，长边有FLT、DEMP、XSMT、FMT、A3V3。目标模式为H1L→L（FLT）、H2L→L（DEMP）、H3L→H（XSMT）、H4L→L（FMT）。照片不足以可靠判断现有焊桥是否导通；先断电测通断，已符合的不用补线，不能同时短接H和L。优先用板上焊盘设置模式，不占用FPGA信号引脚。参考：[ESP32-A2DP作者的同类PCM5102模块接线](https://github.com/pschatzmann/ESP32-A2DP/wiki/Audio-Output#pcm5102-dac)。

## 时钟与格式

板载50MHz输入，GW5AST PLL采用IDIV=2、MDIV=29、ODIV0=29.5：PFD25MHz，VCO725MHz。
音频时钟24.576271186MHz；BCLK3.072033898MHz；LRCK48000.529661Hz（相对48kHz约+11.0ppm，不含板载晶振误差）。每帧64个BCLK，每声道32位时隙、24位二补码，WS变化一位后发送MSB。
不需要额外24.576MHz振荡器，不接J23-39。

## 构建与验证

在项目根目录执行：

```powershell
.venv/Scripts/python.exe synth/band/tools/test_i2s_duplex.py
.venv/Scripts/python.exe synth/band/tools/build_i2s_duplex.py
.venv/Scripts/python.exe synth/band/tools/audit_i2s_duplex.py D:/StarclusterBuilds/实际构建目录
```

构建脚本只生成文件，不烧录。最终文件位于 `output/i2s_audio_20261031`；manifest记录位流哈希、时序、引脚与待测范围。首次使用只下载到SRAM，断电可回到原Flash工作站。现有根目录的临时加载入口仍指向旧工作站，不能用它加载本测试位流。

数字仿真检查双声道位序、64时钟/帧、24位符号极值、麦克风空闲三态、70ns模拟传输延迟、静音、上电等待、直通/限幅、PLL失锁恢复。70ns是测试假设，不是器件数据手册保证的最大延迟。实际线长、边沿、上电、听音和音质需要实物复核。

实物验收顺序：低音量接有源音箱 → SRAM下载 → 按S0听测试音 → 按S2静音 → 按S1说话监听 → 按S2停止。麦克风远离音箱，避免声反馈。仅听到S0不代表麦克风输入已通过。

## 资料依据

- [TDK INMP441数据手册](https://product.tdk.cn/system/files/dam/doc/product/sw_piezo/mic/mems-mic/data_sheet/inmp441.pdf)：I²S、64时钟帧、声道选择、启动周期与下拉。
- [TI PCM510xA数据手册](https://www.ti.com/lit/ds/symlink/pcm5102a.pdf)：三线I²S、BCK恢复系统时钟、FMT/FLT/XSMT及线路输出。
- [Gowin Arora V时钟资源](https://cdn.gowinsemi.com.cn/UG306E.pdf)：PLL参数。实装工具另检查PFD必须在19～81.25MHz范围。
- 项目 `synth/band/hardware/wiring_proposal_20261028/完整引脚表.md`：J23与FPGA球位对应。
