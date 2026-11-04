"""Local marker selection and dwell gate; never generates musical events."""
import math


def red_marker(data, width, height, stride):
    """Locate one compact red marker in an RGBA8888 thumbnail, or reject it.

    This is an explicit colored-marker interface, not general human recognition.
    Multiple markers, large red backgrounds and grid boundaries are ambiguous.
    """
    if width < 16 or height < 16 or stride < width*4 or len(data) < stride*height:
        return None
    mask = set()
    for y in range(height):
        for x in range(width):
            i = y*stride+x*4
            r,g,b = data[i],data[i+1],data[i+2]
            if r >= 120 and r*2 > g*3 and r*2 > b*3:
                mask.add(y*width+x)
    components = []
    minimum = max(8,width*height//400)
    while mask:
        seed=mask.pop();pending=[seed];component=[seed]
        while pending:
            point=pending.pop();x=point%width;y=point//width
            neighbors=[]
            if x:neighbors.append(point-1)
            if x+1<width:neighbors.append(point+1)
            if y:neighbors.append(point-width)
            if y+1<height:neighbors.append(point+width)
            for neighbor in neighbors:
                if neighbor in mask:
                    mask.remove(neighbor);pending.append(neighbor);component.append(neighbor)
        if len(component)>=minimum:components.append(component)
    if len(components)!=1:return None
    points=components[0]
    if len(points)>width*height*.15:return None
    xs=[p%width for p in points];ys=[p//width for p in points]
    area=(max(xs)-min(xs)+1)*(max(ys)-min(ys)+1)
    if len(points)/area<.45:return None
    x=(sum(xs)/len(xs)+.5)/width;y=(sum(ys)/len(ys)+.5)/height
    gx=x*4;gy=y*2
    if min(gx%1,1-gx%1,gy%1,1-gy%1)<.12:return None
    return dict(part=int(gy)*4+int(gx),x=x,y=y,pixels=len(points))


class SelectionGate:
    def __init__(self,dwell=.8,max_gap=.3):
        self.dwell=dwell;self.max_gap=max_gap;self.reset()

    def reset(self):
        self.part=None;self.since=None;self.last=None;self.blocked=None

    def observe(self,part,now):
        if not math.isfinite(now):self.reset();return
        if part is not None and (type(part) is not int or not 0<=part<8):
            self.reset();return
        discontinuity=self.last is not None and not 0<=now-self.last<=self.max_gap
        if discontinuity:self.part=None;self.since=None
        self.last=now
        if part is None:
            self.part=None;self.since=None;self.blocked=None;return
        if part==self.blocked:return
        self.blocked=None
        if part!=self.part:self.part=part;self.since=now

    def candidate(self,now):
        if not math.isfinite(now) or self.last is None or self.since is None:return None
        if not 0<=now-self.last<=self.max_gap or now-self.since<self.dwell:return None
        return self.part

    def consume(self):
        self.blocked=self.part;self.part=None;self.since=None


def apply_selection(desk,seat,part):
    """Change only future input mapping; never acquire a track or release notes."""
    if type(seat) is not int or seat not in desk.seat_parts or type(part) is not int or not 0<=part<8:
        return False,'演奏席或角色无效'
    if any(key[0]==seat for key in desk.held) or any(key[0]==seat for key in desk.midi_sustain):
        return False,'请先松开该席位的音符和延音踏板'
    owner=desk.states.get(part,{}).get('owner',0)
    if desk.port is not None and owner not in (0,seat):
        return False,'该轨道由其他演奏者控制，请先协商归还'
    desk.seat_parts[seat]=part
    if desk.source()==seat:desk.part.setCurrentIndex(part)
    return True,'已改变后续演奏映射；按键时仍按正常规则申请接管'
