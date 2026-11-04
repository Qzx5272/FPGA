> 屏幕类型已更正：用户使用 J20 RGB 套餐屏。HDMI 候选 b 已停止、未上板。本目录的 UI 像素内核和仿真继续复用，实际 LCD 上板结果见 evidence/lcd_ui_20261031。

# 星群 HDMI 演奏台

640×480 中文 RTL UI，继承已验证的 HDMI0/DVI 时钟、OSER10 复位链、PT8211 与 C3 独立 UART 接口。
当前候选构建：`D:/StarclusterBuilds/hdmi_ui_20261031_b`，身份 `0x20261041`。
初版 a 综合通过，PnR 因原频谱电路已移除、专用约束目标不存在而终止；b 仅删除该不存在目标的旧 hold 例外，HDMI／音频／UART 约束继续保留。
当前发布选择器不变；上板使用 SRAM，最终状态见 `../../evidence/hdmi_ui_20261031/`。

`instrument_ui.v` 使用中文字模和文本格 ROM，三级像素流水线同时延迟 RGB/DE/HS/VS。
`ui_state.v` 观察实际 FPGA 入口及引擎状态，不阻塞音频；`ui_snapshot` 冻结状态并经握手在帧边界切换。
16格高亮表示收到 source2 的 60..75 音符事件，持续约200ms；不冒充音符分配成功或垫的物理布局。
“发声数”来自引擎实际 active_voices，桥在线来自 source2 最近1秒有效事件；不是手机连接状态。
音色显示最后一次实体垫音符指定的声部，音高／力度也是最近一次事件。当前初始拨弦与 C3 固定 part8 一致。
全局音量、BPM、播放状态为真实引擎值。八度显示“+0 固定”，新增面板操作清楚标“待接入”。
这次实现演奏首页；录制、曲谱和参数页面尚未实现，不能宣称六个旋钮按压已经能翻页或录制。

## 复现

1. `python generate_assets.py`：使用 Windows 微软雅黑生成232字形的 ROM。生产构建直接使用已生成 ROM，不依赖字体文件。
2. `iverilog -g2012 -I . -s tb_ui -o tb_ui.vvp instrument_ui.v tb_ui.sv`，在本目录运行 vvp，输出 `ui_frame.ppm`。
3. `tb_ui_state.sv` 验证来源区分、事件字段、高亮、桥超时、帧边界跨时钟快照。
4. `../../tools/prepare_hdmi_ui.py` 从哈希验证过的 phone_uart 候选建立新目录，保留源候选不可变。
5. Gowin 运行新目录 `build.tcl`；`audit_phone_uart.py --build ... --evidence hdmi_ui_20261031` 核对实际时序、引脚、位流。
6. 仅审查通过后用 `load_phone_uart_sram.py` 同样参数加载 SRAM 并核对板上身份。

`ui_preview.png` 是 RTL 仿真的测试场景，不是实物屏照片。
六旋钮按压＋四按键的方案详见 `../../hardware/wiring_proposal_20261028/面板更新_6旋钮按压_4按键_20261031.md`。
