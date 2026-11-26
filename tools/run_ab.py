"""A/B runner: same as run_and_watch.py but the exe and the cache are arguments.

usage: python run_ab.py <seconds> <log> <exe> <cache_dir> [data_dir]

`seconds` 0 or less runs until the title exits. Your own dump goes in
VICTORY_GAME_DIR (or `victory.toml`); nothing game-side lives in this repo.
Everything is a child of this process, so the run is not reaped.
"""
import ctypes, os, re, subprocess, sys, time
from ctypes import wintypes as wt
from datetime import datetime

if len(sys.argv) < 5:
    sys.exit(__doc__)

DURATION = int(sys.argv[1])
LOG = sys.argv[2]
EXE = sys.argv[3]
CACHE = sys.argv[4]
DATA = sys.argv[5] if len(sys.argv) > 5 else os.environ.get(
    "VICTORY_DATA_DIR", os.path.join(os.path.dirname(os.path.abspath(EXE)), "..", "..", "data"))
GAME_DIR = os.environ.get("VICTORY_GAME_DIR", "")
if not GAME_DIR:
    sys.exit("set VICTORY_GAME_DIR to your own dump of the title")
GAME = os.path.join(GAME_DIR, "game_scarlett_master.exe")
SHOTS = os.environ.get("SHOTS_DIR", os.path.join(os.path.expanduser("~"), "victory-shots"))

env = dict(os.environ)
env.update({
    "VICTORY_GAME_DIR": GAME_DIR,
    "VICTORY_CACHE_DIR": CACHE,
    "VICTORY_DATA_DIR": DATA,
    "VICTORY_HAIR": "1",
    "VICTORY_PIPELINE_WAIT_MS": "24",
    "VICTORY_CARD_BUFFERS_MIN_MB": "0",
})
# Anything the caller passes as VICTORY_* wins over the defaults above.
for k, v in os.environ.items():
    if k.startswith("VICTORY_"):
        env[k] = v

u = ctypes.windll.user32


def game_window():
    found = []
    P = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def cb(h, l):
        n = u.GetWindowTextLengthW(h)
        if n:
            b = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(h, b, n + 1)
            if b.value.startswith('Americas'):
                found.append((h, b.value))
        return True

    u.EnumWindows(P(cb), 0)
    return found


def frame_line():
    try:
        data = open(LOG, 'rb').read()[-600000:].decode('utf-8', 'replace')
    except OSError:
        return ''
    data = re.sub(r'\x1b\[[0-9;]*m', '', data)
    lines = [l for l in data.splitlines() if 'fps,' in l]
    return lines[-1] if lines else ''


os.makedirs(SHOTS, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)
log = open(LOG, 'wb')
CONSOLE = os.environ.get("CONSOLE", "series-x")
p = subprocess.Popen([EXE, 'run', GAME, '--execute', '--console', CONSOLE],
                     stdout=log, stderr=subprocess.STDOUT, env=env)
# No extra window of ours on top: the numbers go on the HUD panel (hud.py),
# which is click-through, never takes the focus, and reads NVML directly.
hud = None
if os.environ.get("HUD", "1") != "0":
    hud = subprocess.Popen([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                         "hud.py"), LOG, str(p.pid)])
print(f"started pid={p.pid} exe={EXE} console={CONSOLE} hud={hud.pid if hud else 'off'}", flush=True)

t0 = time.time()
clicked = 0
last_shot = 0.0
while DURATION <= 0 or time.time() - t0 < DURATION:
    time.sleep(5)
    if p.poll() is not None:
        print(f"[{int(time.time()-t0)}s] process exited code={p.returncode}", flush=True)
        break
    elapsed = time.time() - t0
    ln = frame_line()
    m = re.search(r'([\d.]+) fps, ([\d.]+) ms/frame.*?(\d+) draws/frame', ln)
    draws = int(m.group(3)) if m else 0
    if draws <= 12 and elapsed > 40 and clicked < int(os.environ.get("CLICK_LIMIT", "0")):
        w = game_window()
        if w:
            h = w[0][0]
            r = wt.RECT()
            u.GetWindowRect(h, ctypes.byref(r))
            u.SetForegroundWindow(h)
            time.sleep(0.8)
            # first pass: the account tile, relative to the window; later: the middle, plus Enter
            if clicked < 4:
                x = int(r.left + (r.right - r.left) * 0.91)
                y = int(r.top + (r.bottom - r.top) * 0.94)
            else:
                x = (r.left + r.right) // 2
                y = (r.top + r.bottom) // 2
            u.SetCursorPos(x, y)
            time.sleep(0.3)
            u.mouse_event(0x0002, 0, 0, 0, 0)
            time.sleep(0.15)
            u.mouse_event(0x0004, 0, 0, 0, 0)
            time.sleep(0.2)
            u.keybd_event(0x0D, 0, 0, 0)
            time.sleep(0.05)
            u.keybd_event(0x0D, 0, 2, 0)
            clicked += 1
            print(f"[{int(elapsed)}s] click {clicked} at ({x},{y}) win={r.left},{r.top},{r.right},{r.bottom} draws={draws}", flush=True)
    if elapsed - last_shot > 25:
        last_shot = elapsed
        try:
            from PIL import ImageGrab
            ImageGrab.grab().save(os.path.join(SHOTS, f"AB_{datetime.now().strftime('%H%M%S')}.png"))
        except Exception as e:
            print('shot failed', e, flush=True)
        if m:
            print(f"[{int(elapsed)}s] {m.group(1)} fps {m.group(2)} ms {draws} draws", flush=True)
        else:
            print(f"[{int(elapsed)}s] no frame line", flush=True)

print("stopping", flush=True)
if p.poll() is None:
    p.terminate()
    try:
        p.wait(20)
    except subprocess.TimeoutExpired:
        p.kill()
log.close()
if hud is not None and os.environ.get("HUD_KEEP") != "1":
    hud.terminate()
print("done", flush=True)
