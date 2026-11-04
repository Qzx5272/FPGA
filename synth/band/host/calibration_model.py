"""Calibration for the 64 local pressure pads, independent of MIDI velocity."""
from protocol import Event
DEFAULT=dict(baseline=0,gain=127,invert=False)
def normalize(values):
    if not isinstance(values,dict):raise ValueError('压力校准必须为对象')
    result={}
    for key,value in values.items():
        try:channel=int(key)
        except (TypeError,ValueError):raise ValueError('非法压力通道') from None
        if not 0<=channel<64 or channel in result:raise ValueError('压力通道必须为唯一的 0–63')
        if not isinstance(value,dict) or set(value)!=set(DEFAULT):raise ValueError('校准需要 baseline、gain、invert')
        if type(value['baseline']) is not int or not 0<=value['baseline']<=4095:raise ValueError('零点必须为 0–4095')
        if type(value['gain']) is not int or not 1<=value['gain']<=65535:raise ValueError('增益必须为 1–65535')
        if type(value['invert']) is not bool:raise ValueError('反向必须为布尔值')
        result[channel]=dict(value)
    return result
def fit(released,pressed):
    if any(type(x) is not int or not 0<=x<=4095 for x in (released,pressed)):raise ValueError('ADC 测量值必须为 0–4095')
    span=abs(pressed-released)
    if span==0:raise ValueError('释放与按压测量值不能相同')
    gain=(127*4096+span-1)//span
    if gain>65535:raise ValueError('测量量程过小，无法使用当前定点增益')
    return dict(baseline=4095-released if pressed<released else released,gain=gain,invert=pressed<released)
def pressure(raw,calibration):
    c=normalize({0:calibration})[0]
    if type(raw) is not int or not 0<=raw<=4095:raise ValueError('ADC 测量值必须为 0–4095')
    oriented=4095-raw if c['invert'] else raw
    return min(127,max(0,oriented-c['baseline'])*c['gain']//4096)
def events(values):
    for channel,c in sorted(normalize(values).items()):
        yield Event(17,source=1,contact=channel,flags=int(c['invert']),serial=c['gain'],parameter=c['baseline'])
