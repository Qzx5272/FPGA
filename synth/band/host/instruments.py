"""Playable algorithm presets. Extended roles require the workstation V6 capability."""
import math

EXTENDED_TIMBRES = 1 << 6


def envelope(attack, decay, sustain, release):
    return {4:max(1,min(16383,round(65535/(attack*48)))),
            5:max(0,min(15,round(math.log2(decay*48/math.log(1000))))),
            6:round(sustain*16383/100),
            7:max(0,min(15,round(math.log2(release*48/math.log(1000)))))}


PRESETS = [
    dict(id='kick',name='底鼓 · 深沉',family='膜鸣',part=0,adsr=(.1,90,0,30)),
    dict(id='snare',name='军鼓 · 沙响',family='膜鸣',part=1,adsr=(.1,100,0,35)),
    dict(id='hat',name='踩镲 · 短促',family='体鸣',part=2,adsr=(.1,45,0,20)),
    dict(id='bass',name='合成贝斯',family='电子',part=3,adsr=(1,250,30,100)),
    dict(id='ep',name='FM 电钢琴',family='电子',part=4,adsr=(.4,1000,0,180)),
    dict(id='reed',name='持续簧音',family='气鸣式',part=5,adsr=(18,800,85,120)),
    dict(id='lead',name='柔和主奏',family='电子',part=6,adsr=(8,600,90,140)),
    dict(id='choir',name='元音合唱',family='人声式',part=7,adsr=(35,1500,85,280)),
    dict(id='pluck',name='拨弦式 · 明亮',family='弦鸣式',part=8,adsr=(.5,900,0,160),extended=True),
    dict(id='flute',name='笛式 · 气息',family='气鸣式',part=9,adsr=(22,700,88,150),extended=True),
    dict(id='bell',name='钟式 · 金属',family='体鸣式',part=10,adsr=(.5,2400,0,450),extended=True),
    dict(id='wood',name='木琴式 · 木质',family='体鸣式',part=11,adsr=(.2,400,0,85),extended=True),
    dict(id='bowed',name='弓弦式 · 合奏',family='弦鸣式',part=12,adsr=(65,900,90,320),extended=True),
    dict(id='organ',name='风琴式 · 管音',family='气鸣式',part=13,adsr=(4,500,100,90),extended=True),
    dict(id='brass',name='铜管式 · 强奏',family='气鸣式',part=14,adsr=(30,450,78,140),extended=True),
]
BY_ID = {p['id']:p for p in PRESETS}
ROLE_NAMES = ['底鼓','军鼓','踩镲','贝斯','电钢琴','持续簧音','主奏','元音式合唱',
              '拨弦式','笛式','钟式','木琴式','弓弦式','风琴式','铜管式','扩展轨 16']


def supported(preset, identity):
    return not preset.get('extended') or bool(identity and identity.get('features',0)&EXTENDED_TIMBRES)
