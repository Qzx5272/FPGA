# Resource exploration only. No guessed pins; this target cannot publish a bitstream.
set here [file dirname [file normalize [info script]]]
file mkdir "$here/build/workstation_synth"
cd "$here/build/workstation_synth"
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module workstation_top
set_option -verilog_std v2001
set_option -use_cpu_as_gpio 1
foreach f [glob "$here/rtl/*.v"] {add_file $f}
foreach f {hq_sine_quarter.v audio_serial.v uart.v} {add_file "$here/../rtl/$f"}
set_option -output_base_name workstation_exploration
run syn
