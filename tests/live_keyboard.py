"""Root-only opt-in test using a disposable uinput keyboard. No keyboard events saved to disk."""
import fcntl
import os
from pathlib import Path
import select
import struct
import time

EV = struct.Struct('@llHHi')
fd = os.open('/dev/uinput', os.O_WRONLY | os.O_NONBLOCK)
try:
    for kind in (0, 1): fcntl.ioctl(fd, 0x40045564, kind)
    for key in range(1, 256): fcntl.ioctl(fd, 0x40045565, key)
    fcntl.ioctl(fd, 0x405c5503, struct.pack('@HHHH80sI', 3, 0x1234, 0x5678, 1, b'Attention integration keyboard', 0))
    fcntl.ioctl(fd, 0x5501)
    time.sleep(.7)
    virtual = next(p.parent.parent for p in Path('/sys/class/input').glob('event*/device/name') if p.read_text().strip() == 'keyd virtual keyboard')
    out = os.open('/dev/input/' + virtual.name, os.O_RDONLY | os.O_NONBLOCK)
    def emit(key, value):
        os.write(fd, EV.pack(0,0,1,key,value) + EV.pack(0,0,0,0,0))
        time.sleep(.025)
    def drain():
        result=[]
        while select.select([out],[],[],.1)[0]:
            raw=os.read(out, EV.size * 64)
            for offset in range(0,len(raw),EV.size):
                _,_,kind,key,value=EV.unpack(raw[offset:offset+EV.size])
                if kind==1: result.append((key,value))
        return result
    drain()
    emit(58,1); emit(58,0)
    events=drain()
    assert (194,1) in events and (194,0) in events, events
    emit(58,1)
    for key in (36,37,38,39): emit(key,1); emit(key,0)
    emit(58,0)
    events=drain()
    for key in (103,108,105,106): assert (key,1) in events and (key,0) in events, events
    assert not any(key in (36,37,38,39,58,194) for key,_ in events),events
    emit(58,1); time.sleep(.35); emit(58,0)
    assert not any(key==194 for key,_ in drain()), 'Long hold incorrectly tapped'
    os.close(out)
    print('PASS: CapsLock tap emits F24; held J/K/L/semicolon emit Up/Down/Left/Right; long hold has no tap')
finally:
    fcntl.ioctl(fd,0x5502)
    os.close(fd)
