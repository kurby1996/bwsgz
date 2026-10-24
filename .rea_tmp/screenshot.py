# -*- coding: utf-8 -*-
"""Screenshot helper: capture a window (BlastEm) or full screen to PNG."""
import sys
import ctypes
from ctypes import wintypes
import PIL.ImageGrab as ig  # may not exist; fallback below

def get_blastem_rect():
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    hwnd = user32.FindWindowW(None, "BlastEm")
    if not hwnd:
        # enumerate windows to find one with BlastEm in title
        result = []
        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def cb(h, l):
            n = user32.GetWindowTextLengthW(h)
            if n:
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(h, buf, n + 1)
                if "blast" in buf.value.lower():
                    result.append((h, buf.value))
            return True
        user32.EnumWindows(cb, 0)
        if not result:
            return None
        hwnd = result[0][0]
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "screen.png"
    r = get_blastem_rect()
    try:
        img = ig.grab(bbox=(r.left, r.top, r.right, r.bottom))
    except Exception:
        import PIL.ImageGrab as ig2
        img = ig2.grab()
    img.save(out)
    print(f"saved {out} bbox={r.left},{r.top},{r.right},{r.bottom}")

if __name__ == "__main__":
    main()
