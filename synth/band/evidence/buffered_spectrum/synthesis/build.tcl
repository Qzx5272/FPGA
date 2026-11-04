set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module pcm_spectrum_buffered
set_option -verilog_std sysv2017
add_file fft_fixed.v
add_file pcm_snapshot.v
add_file pcm_spectrum.v
add_file spectrum_snapshot.v
add_file pcm_spectrum_buffered.v
set_option -output_base_name buffered_spectrum2048
run syn
