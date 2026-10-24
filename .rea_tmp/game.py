# -*- coding: utf-8 -*-
"""Reliable gamepad driver for BlastEm: force focus + real key events."""
import ctypes, time
from ctypes import wintypes
from PIL import ImageGrab

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
user32.SetProcessDPIAware()

VK = {'up':0x26,'down':0x28,'left':0x25,'right':0x27,'enter':0x0D,
      'a':0x41,'s':0x53,'d':0x44,'q':0x51,'w':0x57,'e':0x45,
      'f':0x46,'space':0x20,'esc':0x1B,'tab':0x09,'backtick':0xC0,'l':0x4C}
SCAN = {'up':0x48,'down':0x50,'left':0x4B,'right':0x4D,'enter':0x1C,
        'a':0x1E,'s':0x1F,'d':0x20,'q':0x10,'w':0x11,'e':0x12,
        'f':0x21,'space':0x39,'esc':0x01,'tab':0x0F,'backtick':0x29,'l':0x26}

def find_blastem():
    res = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, l):
        n = user32.GetWindowTextLengthW(h)
        if n:
            buf = ctypes.create_unicode_buffer(n+1)
            user32.GetWindowTextW(h, buf, n+1)
            if "blastem" in buf.value.lower() and user32.IsWindowVisible(h):
                res.append(h)
        return True
    user32.EnumWindows(cb, 0)
    return res[0] if res else None

HWND = None

def focus(dwell=0.35):
    global HWND
    if HWND is None or not user32.IsWindow(HWND):
        HWND = find_blastem()
        if not HWND:
            raise RuntimeError("BlastEm window not found")
    fg = user32.GetForegroundWindow()
    tid_fg = user32.GetWindowThreadProcessId(fg, None)
    tid_me = kernel32.GetCurrentThreadId()
    tid_tgt = user32.GetWindowThreadProcessId(HWND, None)
    if tid_fg != tid_tgt:
        user32.AttachThreadInput(tid_me, tid_fg, True)
        user32.AttachThreadInput(tid_me, tid_tgt, True)
        user32.BringWindowToTop(HWND)
        user32.SetForegroundWindow(HWND)
        user32.SetFocus(HWND)
        user32.AttachThreadInput(tid_me, tid_fg, False)
        user32.AttachThreadInput(tid_me, tid_tgt, False)
    else:
        user32.SetFocus(HWND)
    time.sleep(dwell)
    return HWND

def tap(key, hold=0.11):
    focus()
    vk, scan = VK[key], SCAN[key]
    user32.keybd_event(vk, scan, 0, 0)
    time.sleep(hold)
    user32.keybd_event(vk, scan, 2, 0)
    time.sleep(0.09)

def tap_many(keys, gap=0.12):
    for k in keys:
        tap(k)
        time.sleep(gap)

def shot(out):
    focus(0.15)
    r = wintypes.RECT()
    user32.GetWindowRect(HWND, ctypes.byref(r))
    img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
    img.save(out)
    return out

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if args and args[0] == "shot":
        print("saved", shot(args[1]))
    else:
        tap_many(args)
        print("sent", args)
