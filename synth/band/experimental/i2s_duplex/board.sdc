create_clock -name core_clk -period 20.000 [get_ports {clk}]
create_generated_clock -name audio_clk -source [get_ports {clk}] -multiply_by 29 -divide_by 59 [get_pins {clock_source/pll/CLKOUT0}]
# First stage of intentionally oversampled external inputs only.
set_false_path -from [get_ports {mic_sd}] -to [get_pins {link/rx_meta_s0/D}]
set_false_path -from [get_ports {key_play_n key_stop_n key_panic_n}] -to [get_pins {key_meta_0_s0/D key_meta_1_s0/D key_meta_2_s0/D}]
# 20ns board-pad budget; data/WS change on the falling BCLK half-cycle.
# Testbench uses 70ns total pad/data delay (engineering assumption, not a
# datasheet maximum). Sampled after four audio clocks (~163ns), then the
# synchronizer pipeline. Actual wiring and signal integrity still need checking.
set_max_delay 20.000 -from [get_clocks {audio_clk}] -to [get_ports {i2s_bck i2s_ws i2s_sd mic_bck mic_ws}]
set_min_delay 0.000 -from [get_clocks {audio_clk}] -to [get_ports {i2s_bck i2s_ws i2s_sd mic_bck mic_ws}]
