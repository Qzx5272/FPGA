set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module top
set_option -verilog_std v2001
set_option -use_cpu_as_gpio 1
set_option -include_path [list "$here/rtl"]
foreach f [glob "$here/rtl/*.v"] { add_file $f }
add_file "$here/constraints/board.cst"
add_file "$here/constraints/board.sdc"
set_option -output_base_name aurora_synth
run all
