set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module i2s24_queue_bridge
set_option -verilog_std sysv2017
add_file i2s24_queue_bridge.v
add_file audio_cdc_fifo.v
add_file i2s24_tx.v
set_option -output_base_name i2s24_queue
run syn
