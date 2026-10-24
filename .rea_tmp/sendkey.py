# -*- coding: utf-8 -*-
"""Send keys to BlastEm window (SDL reads keyboard state via focus)."""
import ctypes
import time
from ctypes import wintypes

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

def find_blastem():
    hwnd = user32.FindWindowW(None, "BlastEm")
    if hwnd:
        return hwnd
    result = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, l):
        n = user32.GetWindowTextLengthW(h)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(h, buf, n + 1)
            if "blast" in buf.value.lower():
                result.append(h)
        return True
    user32.EnumWindows(cb, 0)
    return result[0] if result else None

VK = {'up':0x26,'down':0x28,'left':0x25,'right':0x27,'enter':0x0D,
      'a':0x41,'b':0x42,'c':0x43,'s':0x53,'d':0x44,'q':0x51,'w':0x57,'e':0x45,'x':0x58,'z':0x5A,'space':0x20}

def press(key, hold=0.09):
    vk = VK[key]
    user32.keybd_event(vk, 0, 0, 0)
    time.sleep(hold)
    user32.keybd_event(vk, 0, 2, 0)  # KEYEVENTF_KEYUP
    time.sleep(0.05)

if __name__ == "__main__":
    import sys
    hwnd = find_blastem()
    if not hwnd:
        print("NO_WINDOW"); sys.exit(1)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.4)
    for k in sys.argv[1:]:
        press(k)
    print("sent:", sys.argv[1:])
