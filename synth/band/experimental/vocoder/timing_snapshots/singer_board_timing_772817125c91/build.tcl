set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module band_singer_board_engine
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
set_option -netlist_hierarchy 0
foreach f [glob rtl/*.v rtl/*.sv] {add_file $f}
add_file engine.sdc
add_file engine.cst
set_option -output_base_name singer_engine
run all
