"""Auditable allocation estimates. Only DDS unit costs are synthesis-backed."""
import json,math
from pathlib import Path

def estimate(partials,lanes,voices):
    depth=math.ceil(partials/lanes)
    bram={'partial_state_278logical_288physical_banked':lanes*math.ceil(depth/512)*8,
          'quarter_sine_paired_ROM_synthesized':lanes*2,
          'eight_string_delay_units_2048x36':32,
          'eight_FDN_delays_2048x36':32,
          'stereo_slapback_4096x36':16,
          'event_FIFO_release_mailboxes_track_state':16,
          'voice_cache_and_patch_parameters':16,
          'vocal_source_tables':8,
          'modal_state_control_scratch':16,'clock_initialization_CDC_audio_FIFO_reserve':4}
    dsp={'partial_lanes_assumed_7_each':7*lanes,'voice_pan_assumed_2_each':2*lanes,
         'modal_rotation_and_input_gain':9,'vocal_cascade_shared':6,'parallel_consonant_filter_core':6,
         'string_filters_shared':8,'effects':12,'master':8,'control_reserve':8}
    cycles={'partial_scan':depth,'per_voice_pan_and_bus':6*math.ceil(voices/lanes),
            'pipeline_flush':18,'dependent_four_voice_six_section_vocal_path':144,
            'mix_FDN_limiter_IO_reservation':160}
    total=sum(cycles.values());mem=sum(bram.values())
    return {'partials':partials,'lanes':lanes,'musical_voice_slots':voices,
            'state_depth_per_lane':depth,'bsram18k':bram,'bsram_total':mem,'bsram_margin':340-mem,
            'dsp27x18':dsp,'dsp_total':sum(dsp.values()),'dsp_margin':298-sum(dsp.values()),
            'critical_path_cycle_reservations':cycles,'sample_cycles_required':total,
            'sample_cycles_minimum_at_50MHz_48k':1041,'cycle_margin':1041-total,
            'with_half_second_stereo_delay_bram_total':mem-16+2*math.ceil(24000/512),
            'benchmark_oscillator_samples_per_second':partials*48000,
            'qualifier':'budget, not full design synthesis or timing closure; phase/frequency/envelope required per counted unit'}

out={'hardware':{'BSRAM18k':340,'DSP27x18':298,'clock_hz':50000000,'audio_fs':48000},
     'source':'Gowin DS1239E device resource and BSRAM/DSP tables; isolated HQ DDS synthesis',
     'profiles':[estimate(4096,8,64),estimate(8192,16,256)],
     'assumptions':['8 delay units mean 4 dual-polarization strings, not 8 dual-polarization voices',
                    'singers and FM operators consume the common partial/voice pool',
                    'envelopes are independent exponential segments with per-partial target/rate/timer',
                    'quarter-sine, modal rotation and envelope step have isolated synthesis; full lanes and effects remain estimates',
                    '278-bit partial state (32-bit generation and 25-bit envelope remainder) uses 288 bits in 8 x 36-bit banks',
                    '27-bit Q24 envelope coefficient times signed 25-bit delta uses two base DSPs per lane',
                    'all arithmetic multipliers use explicit signed-width handling',
                    'external DDR, full vocoder and long convolution are excluded']}
if __name__=='__main__':
    (Path(__file__).resolve().parent/'deep'/'architecture_budget.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
