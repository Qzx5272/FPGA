"""Shared structural adaptation for generated and exported I2S stage engines."""

def replace(s, old, new):
    if s.count(old) != 1:
        raise ValueError('Stage source boundary changed: ' + old)
    return s.replace(old, new)

def adapt_stage_engine(engine):
    engine = replace(engine, 'module band_stage_engine #(', 'module band_stage_i2s_engine #(')
    engine = replace(engine, 'output wire transport_sample_tick,', 'input wire transport_fault,output wire transport_sample_tick,')
    engine = replace(engine, 'wire panic=host_panic||local_panic_sync;', 'wire panic=host_panic||local_panic_sync||transport_fault;')
    engine = replace(engine, 'output wire transport_sample_tick,', 'output wire transport_sample_tick,output wire audio_stop,input wire[31:0]external_dropped,external_underruns,')
    engine = replace(engine, 'assign pcm_left=left;', 'assign audio_stop=stop;assign pcm_left=left;')
    start = engine.index(' audio_pt8211_queue dac(')
    end = engine.index(' assign sample_tick=', start)
    engine = engine[:start] + ' assign debug_tick=0;assign HP_BCK=0;assign HP_WS=0;assign HP_DIN=0;\n assign dac_dropped=external_dropped;assign dac_underruns=external_underruns;\n assign dac_ready=1;assign dac_queued=0;\n' + engine[end:]
    engine = replace(engine, 'assign PA_EN=~rst;', 'assign PA_EN=0;')
    return engine
