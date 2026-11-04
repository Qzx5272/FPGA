# J20 套餐屏中文演奏台

用户已明确屏幕为开发板套餐自带、宽排线接 J20 的 RGB LCD，非 HDMI。
2026-10-31 彩条实物测试：800×480、25MHz、DE 模式，用户确认完整彩条和四周白色边框。
屏幕准确型号尚未读到，不能把兼容点亮等同于已核对屏厂数据手册所有极限参数。
测试依据 Sipeed 官方 `TangMega-138KPro-example/rgb_screen/800_480_screen` 引脚和有效区／消隐布局；
原例 PLL 为35MHz，本轮在完整输出时序预算下使用25MHz，约39.35帧/秒。

## 当前实现

`board_lcd_ui_top.sv` 直接集成原 PT8211+C3 音频引擎、状态观察器、帧边界快照和中文 UI。
800×480 内居中放置640×480界面，左右各80像素边距；RGB888截取高6位送RGB666。
LCD像素时钟为内部像素时钟反相，像素数据在内部上升沿发布、外部上升沿采样。
新 UI 继承 `../hdmi_ui/instrument_ui.v`，十路外接按压和六路旋转目前仅更新方案，尚未接入此固件。
音高／力度、C3垫桥心跳、实际发声数、音量、BPM、播放状态来自真实事件或引擎。
八度标“+0 固定”，面板、录制、页面等显示待接入；没有伪造控制成功。

构建目录 `D:/StarclusterBuilds/lcd_ui_20261031_c`，身份 `0x20261051`。
证据 `../../evidence/lcd_ui_20261031/`；Flash 和 CURRENT_RELEASE 不改。
HDMI 候选已停止、未上板，不作为本屏可用版本。

## 验证与复现

- `../../tools/prepare_lcd_ui.py`：逐文件校验父候选并创建独立 LCD 候选，35个物理引脚。
- `../../tools/verify_lcd_ui.py`：像素仿真，音频引擎与PLL使用明确的测试桩；验证800×480完整帧与RGB666输出。此测试不代替音频整机测试。
- `../../tools/audit_lcd_ui.py`：真实PnR setup/hold/pulse、全部SDC激活、35固定引脚与源哈希检查。
- `../../tools/load_lcd_ui_sram.py`：审查通过后仅写SRAM，再通过PC串口读取实际身份。
- 外部输出预算5ns setup、1ns hold相对反相送屏时钟；实物点亮已验证，最终长稳／温度边界与屏厂规格仍需实测。

官方参考：https://github.com/sipeed/TangMega-138KPro-example/tree/main/rgb_screen

候选 c 已通过实际 PnR setup/hold/pulse、引脚与源哈希审查，已加载 SRAM 并由 COM12 回读确认身份 0x20261051，CRC 错误为零。用户已实物确认：界面正常、敲击有反馈且有声音。串口记录发声数最高 2，事件拒绝和音频超时为零。
