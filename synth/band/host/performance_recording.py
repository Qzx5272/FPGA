"""Versioned performance event takes. Never replay stale ownership/epoch packets."""
import copy
import json
import math
import os
import tempfile
from pathlib import Path

FORMAT = 'starcluster-take-1'
KINDS = {0, 1, 2, 4, 5, 7, 10, 11, 15, 16, 127}


def validate(take):
    if not isinstance(take, dict) or take.get('format') != FORMAT:
        raise ValueError('不是星群演奏事件录制文件')
    duration = take.get('duration_us')
    if type(duration) is not int or not 0 <= duration <= 24*3600*1000000:
        raise ValueError('录制时长非法')
    events = take.get('events')
    if not isinstance(events, list) or len(events) > 1000000:
        raise ValueError('录制事件数量非法')
    if not isinstance(take.get('performance', {}), dict):
        raise ValueError('录制参数非法')
    last = -1
    from protocol import Event
    for e in events:
        if not isinstance(e, dict) or type(e.get('at_us')) is not int or not last <= e['at_us'] <= duration:
            raise ValueError('录制事件时间顺序非法')
        last = e['at_us']
        data = e.get('event')
        if not isinstance(data, dict) or data.get('kind') not in KINDS:
            raise ValueError('录制含不支持的事件')
        try:
            if any(type(v) is not int for v in data.values()):raise ValueError('非整数控制')
            if data['kind']==4 and(data.get('flags') not in (2,3) or data.get('source')!=1):raise ValueError('仅可重放指挥静音/取消静音命令')
            Event(**data).encode()
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError('录制事件非法：'+str(exc)) from exc
    return take


def save(path, take):
    validate(take)
    path = Path(path)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=path.name+'.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(take, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):os.unlink(name)


def load(path):
    path = Path(path)
    if path.stat().st_size > 128*1024*1024:raise ValueError('录制文件过大')
    return validate(json.loads(path.read_text(encoding='utf-8')))


class Recorder:
    def __init__(self):
        self.active = False
        self.take = None
        self.live = {}

    def start(self, now, performance, identity, held=()):
        self.started = now
        self.live = {}
        self.take = dict(format=FORMAT, duration_us=0, performance=copy.deepcopy(performance),
                         board_identity=copy.deepcopy(identity), events=[],
                         capture_scope='Successfully transmitted host controls; local FPGA controls require event return telemetry')
        self.active = True
        self.hardware_origin = None
        for event in held:self.capture(event, now)

    def capture(self, event, now):
        if not self.active or event.kind not in KINDS:return
        if event.kind==4 and event.flags<2:return
        if len(self.take['events']) >= 1000000:
            self.stop(now)
            raise ValueError('录制达到100万事件上限，已结束')
        from dataclasses import asdict
        at = max(self.take['events'][-1]['at_us'] if self.take['events'] else 0,
                 round(max(0, now-self.started)*1000000))
        data = asdict(event)
        self.take['events'].append(dict(at_us=at, event=data))
        key = (event.source, event.part, event.contact, event.serial)
        if event.kind == 0:self.live[key] = data
        elif event.kind == 1:self.live.pop(key, None)
        elif event.kind == 2:self.live={k:v for k,v in self.live.items() if k[0]!=event.source}
        elif event.kind == 127 or (event.kind == 5 and event.flags):self.live.clear()

    def capture_hardware(self,event,ticks,now):
        if not self.active:return
        if self.hardware_origin is None:self.hardware_origin=(ticks,now)
        first,origin=self.hardware_origin
        if ticks<first:raise ValueError('板端计时器复位，录制已失去连续时间基准')
        self.take['capture_scope']='Host transmissions plus expansion accepted-event telemetry; hardware sample timestamps, not acoustic latency'
        self.capture(event,origin+(ticks-first)/48000)

    def stop(self, now):
        if not self.active:return self.take
        at = max(self.take['events'][-1]['at_us'] if self.take['events'] else 0,
                 round(max(0, now-self.started)*1000000))
        for data in self.live.values():
            off = dict(data, kind=1, velocity=0)
            self.take['events'].append(dict(at_us=at, event=off))
        self.live.clear()
        self.take['duration_us'] = at
        self.active = False
        return validate(self.take)


class Playback:
    def __init__(self):
        self.active = False
        self.position = 0

    def start(self, take, now, speed=1.0):
        validate(take)
        if not math.isfinite(speed) or not .25 <= speed <= 4:raise ValueError('回放速度范围0.25–4')
        self.take = copy.deepcopy(take)
        self.started = now
        self.speed = speed
        self.position = 0
        self.active = True

    def due(self, now, limit=8):
        if not self.active:return []
        at = round(max(0, (now-self.started)*1000000*self.speed))
        events = self.take['events']
        result = []
        while self.position < len(events) and len(result) < limit and events[self.position]['at_us'] <= at:
            result.append(events[self.position]['event'])
            self.position += 1
        if self.position == len(events) and at >= self.take['duration_us']:self.active = False
        return result
