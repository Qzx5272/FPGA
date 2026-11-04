set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module hq_sine_quarter
set_option -verilog_std v2001
set_option -use_cpu_as_gpio 1
set_option -output_base_name hq_quarter_research
add_file "$here/hq_sine_quarter.v"
run syn
