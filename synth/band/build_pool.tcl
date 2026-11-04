set here [file dirname [file normalize [info script]]]
file mkdir "$here/build/pool4096"
cd "$here/build/pool4096"
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module partial_pool
set_option -verilog_std v2001
add_file "$here/rtl/partial_pool.v"
add_file "$here/rtl/partial_lane.v"
add_file "$here/../rtl/hq_sine_quarter.v"
set_option -output_base_name pool4096
run syn
