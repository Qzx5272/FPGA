set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module audio_clock_watchdog
set_option -verilog_std sysv2017
add_file audio_clock_watchdog.v
set_option -output_base_name audio_watchdog
run syn
