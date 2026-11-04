# 外设桥接软件

当前桥接代码对应 Starcluster V6 事件帧，不能把桥接器当作 FPGA 音频输出。

## ESP32-C3 SuperMini 蓝牙桥

`esp32c3/` 是手机 BLE GATT → UART → FPGA 的控制桥，不传输音频，也不提供 USB Host。PlatformIO 环境为 `esp32-c3-supermini`。UART 为 1 Mbaud、8N1：ESP GPIO4/TX 接 FPGA UART RX，GPIO5/RX 接 FPGA UART TX，并共地。ESP32 IO 是 3.3 V；不要接 FPGA 的未确认引脚，也不要用 IO 脚供电。

手机页在 `phone/index.html`，适用于支持 Web Bluetooth 的 Android Chromium 或桌面 Chromium，需 HTTPS/localhost。iPhone Safari 不支持此页面依赖的 Web Bluetooth。首连需在浏览器中选择 Starcluster-C3。页面可奏 16 垫、改力度/表情/弯音/合唱元音、开始/停止板载曲目并导出事件录音。手机席位可以停止曲目，紧急 panic、曲谱上传和管理命令仍保留给电脑。桥接器带连接失效停音与帧校验，但尚未在实体手机/无线环境配对验证。

编译（已在 PlatformIO 6.1.18 / espressif32 6.9.0 编译通过）：

```powershell
$env:PYTHONPATH='D:\StarclusterBuilds\python_tools'
$env:PLATFORMIO_CORE_DIR='D:\StarclusterBuilds\platformio'
python -m platformio run -d synth\band\bridges\esp32c3
```

## Teensy 4.1 USB-MIDI 桥

`usb_host/` 使用 Teensy 4.1 的 USB Host 接口读取 MIDI 打击垫，另一路 Serial1 连 FPGA。板载 Serial1：Teensy pin 1/TX → FPGA UART RX，Teensy pin 0/RX ← FPGA UART TX，共地，1 Mbaud、3.3 V TTL。USB Host 端接符合 USB-MIDI 的垫或有源 Hub；它不是 USB Audio 接口。GPIO2 对地脚踏仅用作可选延音开关。

PlatformIO 环境为 `teensy41`。固件编译已通过，尚未在 Teensy 或实物打击垫上烧录验证。零力度NoteOn等同NoteOff并遵守延音；MIDI CC64与实体踏板按逻辑或叠加，CC120/123释放本席音符。打击垫拔掉后释放音符并停止刷新FPGA席位租约，防止机器声部一直被占住。ESP32-C3 与 Teensy 功能不同：C3 做 BLE，不能替代 Teensy USB Host。

CC20将0–127等分为16个声部（`floor(value*16/128)`）；第16轨为电子歌手，必须等待固件声明歌手能力。歌手仅接受音符/力度/表情，未支持的弯音、元音及ADSR消息不会发送。最后一个音符释放后会请求按小节归还声部；两座桥启动时先释放各自旧实例的音符。FPGA的“声部”旋钮选择参数编辑目标，USB演奏声部由MIDI CC20选择，这两者目前独立。

`tools/verify_teensy_bridge.py` 和 `tools/verify_c3_bridge.py` 已以实际固件C++回调、模拟串口/USB/GATT执行行为检查；手机页另有真实控制器脚本测试。它们验证协议逻辑，不模拟射频环境，也不替代实体USB枚举或手机配对。

## 供电与边界

FPGA 板使用板卡规定的独立电源输入。初次联调可让 ESP32-C3 和 Teensy 各自经 USB 供电；只连接 UART 信号和公共地，不把多个 5 V 电源输出并接。外置 DAC、24.576 MHz 音频时钟、I²S 麦克风、MCP3208 ADC 与模拟传感器均属尚未固定管脚的扩展配置；先核对实际板卡原理图、电源轨、电流、I/O Bank 电压与地线，再接线。当前没有给扩展配置生成可烧录 CST。
