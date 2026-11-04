set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module spectrum_bars
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
add_file spectrum_bars.v
set_option -output_base_name spectrum_bars
run syn
