set here [file dirname [file normalize [info script]]]
file mkdir "$here/build/diagnostic4096"
cd "$here/build/diagnostic4096"
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module diagnostic_top
set_option -verilog_std v2001
set_option -use_cpu_as_gpio 1
foreach f {diagnostic_top.v partial_pool.v partial_lane.v event_receiver.v status_sender.v} {add_file "$here/rtl/$f"}
foreach f {hq_sine_quarter.v uart.v audio_serial.v} {add_file "$here/../rtl/$f"}
add_file "$here/../constraints/board.cst"
add_file "$here/../constraints/board.sdc"
set_option -output_base_name diagnostic4096
run all
