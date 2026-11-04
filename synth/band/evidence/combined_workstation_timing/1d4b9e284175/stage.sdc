# Internal exploratory clocks; NO actual external wiring/timing acceptance.
create_clock -name core_clk -period 20.000000 [get_ports {clk}]
create_clock -name mic_clk -period 325.520833 [get_ports {mic_bck}]
create_clock -name audio_clk -period 40.690104 [get_ports {audio_clk}]
create_clock -name display_clk -period 20.000000 [get_ports {display_clk}]
set_max_delay -from [get_clocks {core_clk}] -to [get_clocks {mic_clk}] 20.000
set_min_delay -from [get_clocks {core_clk}] -to [get_clocks {mic_clk}] 0.000
set_max_delay -from [get_clocks {core_clk}] -to [get_clocks {audio_clk}] 20.000
set_min_delay -from [get_clocks {core_clk}] -to [get_clocks {audio_clk}] 0.000
set_max_delay -from [get_clocks {core_clk}] -to [get_clocks {display_clk}] 20.000
set_min_delay -from [get_clocks {core_clk}] -to [get_clocks {display_clk}] 0.000
set_max_delay -from [get_clocks {mic_clk}] -to [get_clocks {core_clk}] 20.000
set_min_delay -from [get_clocks {mic_clk}] -to [get_clocks {core_clk}] 0.000
set_max_delay -from [get_clocks {mic_clk}] -to [get_clocks {audio_clk}] 20.000
set_min_delay -from [get_clocks {mic_clk}] -to [get_clocks {audio_clk}] 0.000
set_max_delay -from [get_clocks {mic_clk}] -to [get_clocks {display_clk}] 20.000
set_min_delay -from [get_clocks {mic_clk}] -to [get_clocks {display_clk}] 0.000
set_max_delay -from [get_clocks {audio_clk}] -to [get_clocks {core_clk}] 20.000
set_min_delay -from [get_clocks {audio_clk}] -to [get_clocks {core_clk}] 0.000
set_max_delay -from [get_clocks {audio_clk}] -to [get_clocks {mic_clk}] 20.000
set_min_delay -from [get_clocks {audio_clk}] -to [get_clocks {mic_clk}] 0.000
set_max_delay -from [get_clocks {audio_clk}] -to [get_clocks {display_clk}] 20.000
set_min_delay -from [get_clocks {audio_clk}] -to [get_clocks {display_clk}] 0.000
set_max_delay -from [get_clocks {display_clk}] -to [get_clocks {core_clk}] 20.000
set_min_delay -from [get_clocks {display_clk}] -to [get_clocks {core_clk}] 0.000
set_max_delay -from [get_clocks {display_clk}] -to [get_clocks {mic_clk}] 20.000
set_min_delay -from [get_clocks {display_clk}] -to [get_clocks {mic_clk}] 0.000
set_max_delay -from [get_clocks {display_clk}] -to [get_clocks {audio_clk}] 20.000
set_min_delay -from [get_clocks {display_clk}] -to [get_clocks {audio_clk}] 0.000
# Targeted asynchronous hold-only exceptions; never clock_groups/setup cuts.
set_false_path -hold -from [get_clocks {mic_clk}] -to [get_regs {band/input_audio/transport/fifo/wgray_r1* band/input_audio/latest* band/input_audio/held*}]
set_false_path -hold -from [get_clocks {audio_clk}] -to [get_regs {band/output_audio/fifo/rgray_w1* band/output_audio/request1* band/clock_watch/sync1*}]
set_false_path -hold -from [get_clocks {display_clk}] -to [get_regs {band/analyzer/display_frame/ack1*}]
