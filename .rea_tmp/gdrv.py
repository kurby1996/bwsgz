# -*- coding: utf-8 -*-
"""Final driver: game window = title contains 'ROMANCE II'; console = 'blastem.exe'."""
import ctypes, time, sys
from ctypes import wintypes
from PIL import ImageGrab

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
user32.SetProcessDPIAware()

VK = {'up':0x26,'down':0x28,'left':0x25,'right':0x27,'enter':0x0D,
      'a':0x41,'s':0x53,'d':0x44,'q':0x51,'w':0x57,'e':0x45,
      'f':0x46,'space':0x20,'esc':0x1B,'backtick':0xC0,'l':0x4C}
SCAN = {'up':0x48,'down':0x50,'left':0x4B,'right':0x4D,'enter':0x1C,
        'a':0x1E,'s':0x1F,'d':0x20,'q':0x10,'w':0x11,'e':0x12,
        'f':0x21,'space':0x39,'esc':0x01,'backtick':0x29,'l':0x26}

def find_window(part):
    res = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, l):
        n = user32.GetWindowTextLengthW(h)
        if n:
            buf = ctypes.create_unicode_buffer(n+1)
            user32.GetWindowTextW(h, buf, n+1)
            if part.lower() in buf.value.lower() and user32.IsWindowVisible(h):
                res.append((h, buf.value))
        return True
    user32.EnumWindows(cb, 0)
    return res

def focus(hwnd, dwell=0.3):
    fg = user32.GetForegroundWindow()
    tid_fg = user32.GetWindowThreadProcessId(fg, None)
    tid_me = kernel32.GetCurrentThreadId()
    tid_tgt = user32.GetWindowThreadProcessId(hwnd, None)
    user32.AttachThreadInput(tid_me, tid_fg, True)
    user32.AttachThreadInput(tid_me, tid_tgt, True)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.SetFocus(hwnd)
    user32.AttachThreadInput(tid_me, tid_fg, False)
    user32.AttachThreadInput(tid_me, tid_tgt, False)
    time.sleep(dwell)

def game_hwnd():
    wins = find_window("ROMANCE II")
    if not wins:
        raise RuntimeError("game window not found")
    return wins[0][0]

def console_hwnd():
    wins = find_window("blastem.exe")
    if not wins:
        raise RuntimeError("console not found")
    return wins[0][0]

def tap(key, hold=0.12, pre=0.25):
    hwnd = game_hwnd()
    focus(hwnd, pre)
    vk, scan = VK[key], SCAN[key]
    user32.keybd_event(vk, scan, 0, 0)
    time.sleep(hold)
    user32.keybd_event(vk, scan, 2, 0)
    time.sleep(0.1)

def shot(out):
    hwnd = game_hwnd()
    focus(hwnd, 0.15)
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom)).save(out)
    return out

def console_cmd(s, wait=0.8):
    """Type a command into the debugger console."""
    hwnd = console_hwnd()
    focus(hwnd, 0.3)
    for ch in s:
        vk = user32.VkKeyScanW(ord(ch))
        if vk == -1: continue
        vk &= 0xFF
        user32.keybd_event(vk, 0, 0, 0); time.sleep(0.02)
        user32.keybd_event(vk, 0, 2, 0); time.sleep(0.04)
    user32.keybd_event(0x0D, 0, 0, 0); time.sleep(0.04)
    user32.keybd_event(0x0D, 0, 2, 0)
    time.sleep(wait)

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "shot":
        print("saved", shot(args[1]))
    elif args and args[0] == "cmd":
        console_cmd(args[1])
        print("sent", args[1])
    else:
        for k in args:
            tap(k)
        print("sent", args)
