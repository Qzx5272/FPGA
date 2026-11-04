create_clock -name reference_clk -period 20.000 [get_ports {clk50}]
create_generated_clock -name serial_clk -source [get_ports {clk50}] -multiply_by 63 -divide_by 25 [get_pins {video_clocks/pll/CLKOUT0}]
create_generated_clock -name pixel_clk -source [get_pins {video_clocks/pll/CLKOUT0}] -divide_by 5 [get_pins {video_clocks/divider/CLKOUT}]
set_false_path -from [get_clocks {pixel_clk}] -to [get_pins {transmitter/serial_release_0_s0/CLEAR transmitter/serial_release_1_s0/CLEAR}]
