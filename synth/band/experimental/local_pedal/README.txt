本地脚踏保持控制权扩展（source-only）

local_pedal_performer复用原local_performer，额外四路pedal_raw，顺序对应本地席17/18/19/20。输入为同步前的高有效电平，默认50MHz下5ms稳定消抖。实际电平、电源、上拉和管脚需按硬件确定，没有自动分配。

踩下：最后一个压力垫松开仍发note-off，声音进入原有释放包络，但暂缓下一小节归还；松开：提交归还申请，由track_ownership在下一小节执行。同轨新take取消暂存归还。此模块不是CC64音频延音，两者用途不同。

模块使用寄存输出遵守command ready/valid；对下游背压时保持载荷。panic清空暂存命令与归还，实际所有权模块既有panic策略在下个小节归还本地席。

复现：python synth/band/tools/test_local_pedal.py。测试包含原local_performer与实际track_ownership，覆盖短抖动、控制权保持、下一小节归还、重新起音取消旧归还和panic。没有通过新GPIO、整机PnR或实物脚踏验收；默认生产固件和当前歌手时序快照均未改动。集成时以本wrapper替换本地performer并连接新增四路输入；必须重新完成整机验证。
