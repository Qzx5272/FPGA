# Internal two-clock exploration; no external ADC/board timing acceptance.
# SUG940-2.0.4E sections3.8,5.2.5,5.4.2: clock_groups would override max_delay.
create_clock -name core_clk -period 20.000 [get_ports {clk}]
create_clock -name mic_clk -period 325.520833 [get_ports {mic_bck}]
set_max_delay -from [get_clocks {core_clk}] -to [get_clocks {mic_clk}] 20.000
set_max_delay -from [get_clocks {mic_clk}] -to [get_clocks {core_clk}] 20.000
set_min_delay -from [get_clocks {core_clk}] -to [get_clocks {mic_clk}] 0.000
set_min_delay -from [get_clocks {mic_clk}] -to [get_clocks {core_clk}] 0.000
