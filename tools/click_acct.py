"""手动点过账户界面：置顶 Americas 窗口，点右下账户磁贴 + Enter。

usage: python click_acct.py [次数] [模式]
 模式 0: 右下 (0.91, 0.94) 账户磁贴    模式 1: 中下 (0.5, 0.94) + Enter
"""
import ctypes, sys, time
from ctypes import wintypes as wt

u = ctypes.windll.user32
n = int(sys.argv[1]) if len(sys.argv) > 1 else 3


def find():
    out = []
    P = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def cb(h, l):
        ln = u.GetWindowTextLengthW(h)
        if ln:
            b = ctypes.create_unicode_buffer(ln + 1)
            u.GetWindowTextW(h, b, ln + 1)
            if b.value.startswith('Americas'):
                out.append(h)
        return True

    u.EnumWindows(P(cb), 0)
    return out


w = find()
if not w:
    print('窗口没找到')
    raise SystemExit(1)
h = w[0]
print('window', hex(h))
u.ShowWindow(h, 9)
u.SetWindowPos(h, -1, 0, 0, 0, 0, 0x0003)   # TOPMOST, 不改变位置大小
u.SetForegroundWindow(h)
time.sleep(1.0)

r = wt.RECT()
u.GetWindowRect(h, ctypes.byref(r))
W, H = r.right - r.left, r.bottom - r.top
print('rect', r.left, r.top, W, H)

for i in range(n):
    fx, fy = (0.91, 0.94) if i < 4 else (0.5, 0.94)
    x, y = int(r.left + W * fx), int(r.top + H * fy)
    u.SetCursorPos(x, y)
    time.sleep(0.15)
    u.mouse_event(0x0002, 0, 0, 0, 0)   # LEFTDOWN
    time.sleep(0.06)
    u.mouse_event(0x0004, 0, 0, 0, 0)   # LEFTUP
    print(f'click {i+1} at {x},{y}')
    time.sleep(1.6)
    if i >= 4:
        u.keybd_event(0x0D, 0, 0, 0)    # Enter
        u.keybd_event(0x0D, 0, 2, 0)
        print(f'  enter {i+1}')
        time.sleep(1.6)
print('done')
