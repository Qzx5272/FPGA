整机融合顶层：band_stage_top（实验源码，不可直接烧录）

组成：50MHz主时钟、原UART协议与上位机、10路ADC串行输入的本地压力垫/表情、本地四席脚踏保持控制权、I2S麦克风捕获、电子歌手声码器、整乐队音源、PT8211有界输出队列。

生成：python synth/band/tools/prepare_stage_integration.py。它从当前band_singer_board_engine和band_microphone_top生成独立模块名，复用原local_performer及pedal_command_gate；不改生产rtl目录。
联合验证：python synth/band/tools/test_singer_uart.py --stage。ADC和麦克风均为数字模型，UART由实际编码串行送入，不是实物外设。另见evidence/stage_top_chain/result.json，运行中不算通过。

接口：adc_dout[9:0]/adc_cs_n/adc_sclk/adc_din与原workstation_top一致；play/stop/panic为高有效；pedal_raw[3:0]分别保持本地席17/18/19/20控制权；root/minor选择本地音阶；seat_led显示本地触点，pedal_down显示消抖后踏板。麦克风仍需外部提供I2S时钟，24bit/32bit槽，未实现ASRC。

必须补齐实际麦克风/ADC/脚踏的型号、逻辑电平、管脚、电源和时钟约束，随后针对这个完整顶层重新做综合、布局布线和上板验收。此前band_singer_board_engine的内部时序成绩不覆盖此顶层；不提供猜测管脚或可烧录位流。

新增stable_selector对root/minor实体选择进行两级同步和默认5ms整字稳定过滤，只影响后续本地起音；它面向人操作的慢速开关，不是通用多位异步总线握手。测试见tb_stable_selector.v和evidence/stable_selector/result.json。正在运行的stage_syn_5f6085a96845冻结于本改动之前，不覆盖新选择器。

内部时序探索：python synth/band/tools/build_stage_synthesis.py --timing。现行dcd85058062f快照包含stable_selector。采用50MHz核心与名义3.072MHz麦克风时钟，对双向跨域路径使用20ns最大、0ns最小延时，未使用会覆盖最大延时的clock_groups。依据安装版厂商SUG940-2.0.4E章节3.8、5.2.5和5.4.2。只有clk固定，其余自动IO；结果只支持该模型下内部分析，不证明器件接线、外部时序、CDC亚稳态寿命或物理可烧录性。位流禁止烧录。

2026-10-25时序修订：500bfbf44218已完成但失败，4656setup/16hold，core Fmax42.165MHz。失败原始RTL/TCL/SDC/CST保存在timing_snapshots，不包含可烧录授权。stage_pad_frontend将查表、减基线、乘增益、阈值更新拆为4拍；10路每批40周期，忙时新批次计入overruns，配置在每路首拍捕获。复位/总停音撤销未完成批次；原pad_frontend基线不变。kind11 host_control去掉逻辑恒真的packet_ready依赖；98304组合等价检查通过。当前改版ef5b2476b970保持旧时序约束进行对比，待结果，不能假定50MHz通过。
