# -*- coding: utf-8 -*-
"""Drive BlastEm via PostMessage (no focus needed) + robust screenshots."""
import ctypes, sys, time
from ctypes import wintypes

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()
WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x0100, 0x0101, 0x0102

VK = {'up':0x26,'down':0x28,'left':0x25,'right':0x27,'enter':0x0D,
      'a':0x41,'s':0x53,'d':0x44,'q':0x51,'w':0x57,'e':0x45,
      'f':0x46,'space':0x20,'esc':0x1B,'tab':0x09}

SCAN = {'up':0x48,'down':0x50,'left':0x4B,'right':0x4D,'enter':0x1C,
        'a':0x1E,'s':0x1F,'d':0x20,'q':0x10,'w':0x11,'e':0x12,
        'f':0x21,'space':0x39,'esc':0x01,'tab':0x0F}

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

def send_vk(hwnd, vk, scan, down=True):
    lparam = (scan << 16) | 1
    if not down:
        lparam |= (1 << 30) | (1 << 31)
    user32.PostMessageW(hwnd, WM_KEYDOWN if down else WM_KEYUP, vk, lparam)

def press(hwnd, key, delay=0.10):
    vk, scan = VK[key], SCAN[key]
    send_vk(hwnd, vk, scan, True)
    time.sleep(delay)
    send_vk(hwnd, vk, scan, False)
    time.sleep(0.06)

def focus_and_keep(hwnd, dwell=0.25):
    # ALT-key trick to bypass foreground lock
    user32.keybd_event(0x12, 0, 0, 0)
    user32.SetForegroundWindow(hwnd)
    user32.keybd_event(0x12, 0, 2, 0)
    time.sleep(dwell)

def grab(hwnd, out):
    from PIL import ImageGrab
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    focus_and_keep(hwnd)
    img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
    img.save(out)
    return (r.left, r.top, r.right, r.bottom)

if __name__ == "__main__":
    hwnd = find_blastem()
    if not hwnd:
        print("NO_WINDOW"); sys.exit(1)
    args = sys.argv[1:]
    if args and args[0] == "shot":
        print("saved", args[1], grab(hwnd, args[1]))
        sys.exit(0)
    for k in args:
        press(hwnd, k)
    print("posted:", args)
