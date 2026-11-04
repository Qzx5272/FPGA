"""Read-only identity burst through FTDI D2XX; no EEPROM or bit-mode writes.
API reference: https://ftdichip.com/document/programming-guides/
Requires the user's installed x64 vendor DLL; it is not redistributed.
"""
import ctypes as c,time,sys,json,datetime
from pathlib import Path
band=Path(__file__).resolve().parents[1];sys.path.insert(0,str(band/'host'))
from protocol import Event,Decoder
dll=c.WinDLL('D:/Gowin/Gowin_V1.9.12.03_x64/Programmer/bin/data/DLL/ftdi/x64/ftd2xx64.dll')
handle=c.c_void_p();DWORD=c.c_ulong
def function(name,args):
    f=getattr(dll,name);f.argtypes=args;f.restype=DWORD;return f
openex=function('FT_OpenEx',[c.c_void_p,DWORD,c.POINTER(c.c_void_p)])
close=function('FT_Close',[c.c_void_p])
baud=function('FT_SetBaudRate',[c.c_void_p,DWORD])
format=function('FT_SetDataCharacteristics',[c.c_void_p,c.c_ubyte,c.c_ubyte,c.c_ubyte])
flow=function('FT_SetFlowControl',[c.c_void_p,c.c_ushort,c.c_ubyte,c.c_ubyte])
timeouts=function('FT_SetTimeouts',[c.c_void_p,DWORD,DWORD])
purge=function('FT_Purge',[c.c_void_p,DWORD])
read=function('FT_Read',[c.c_void_p,c.c_void_p,DWORD,c.POINTER(DWORD)])
write=function('FT_Write',[c.c_void_p,c.c_void_p,DWORD,c.POINTER(DWORD)])
def check(status):
    if status:raise RuntimeError('D2XX status '+str(status))
serial=c.create_string_buffer(b'2025071717B');check(openex(serial,1,c.byref(handle)))
raw=bytearray();decoder=Decoder();frames=[]
try:
    check(baud(handle,1000000));check(format(handle,8,0,0));check(flow(handle,0,0,0));check(timeouts(handle,10,100));check(purge(handle,3))
    packet=Event(18).encode();buffer=c.create_string_buffer(packet);done=DWORD()
    for i in range(100):
        check(write(handle,buffer,len(packet),c.byref(done)))
        if done.value!=len(packet):raise RuntimeError('Partial D2XX write')
    until=time.monotonic()+.5;buffer=c.create_string_buffer(4096)
    while time.monotonic()<until:
        check(read(handle,buffer,4096,c.byref(done)));block=buffer.raw[:done.value];raw.extend(block);frames.extend(decoder.feed(block))
finally:close(handle)
name='link_d2xx_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
record=dict(status='passed' if frames and decoder.bad_crc==0 else 'failed',requests=100,valid_frames=len(frames),bad_crc=decoder.bad_crc,bytes=len(raw),method='FTDI D2XX identity queries only')
(band/'evidence'/(name+'.raw')).write_bytes(raw)
(band/'evidence'/(name+'.json')).write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
