"""Alarm behaviour: one notification per firing, and dismissal stops the sound."""
import os
import subprocess
import sys
import time

TIMER = (os.environ.get("NL_TIMER_BIN") or
          os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "nl-timer"))
LOG = os.path.expanduser("~/.local/state/nl-timer/fired.log")
fails = []


def sh(command):
    return subprocess.run(command, shell=True, capture_output=True, text=True)


def paplays():
    out = subprocess.run(["pgrep", "-x", "paplay"], capture_output=True, text=True).stdout
    return [pid for pid in out.split() if pid]


def wait_for(predicate, timeout, step=0.1):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(step)
    return False


def fired_lines():
    if not os.path.exists(LOG):
        return []
    return [line.split("\t") for line in open(LOG).read().splitlines()]


def wait_quiet():
    """No sound left over from an earlier phase."""
    wait_for(lambda: not paplays(), 30)


def fire_one(label, extra=""):
    """Schedule a short timer and return the log row for that firing."""
    wait_quiet()
    before = len(fired_lines())
    sh(f"{TIMER} 2s -l {label} -d {extra}")
    if not wait_for(lambda: len(fired_lines()) > before, 15):
        fails.append(f"{label}: never fired")
        return None
    row = fired_lines()[-1]
    if len(row) < 5 or not row[4].isdigit():
        fails.append(f"{label}: notification id not logged: {row}")
    return row


# ---- 1. exactly one notification, critical, never expires
monitor = subprocess.Popen(
    ["timeout", "16", "dbus-monitor", "--session",
     "interface='org.freedesktop.Notifications'"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
time.sleep(1.0)
row = fire_one("one-shot", "--repeat 1")
time.sleep(6)
monitor.terminate()
try:
    bus = monitor.communicate(timeout=5)[0]
except subprocess.TimeoutExpired:
    monitor.kill()
    bus = ""

notify_calls = bus.count("member=Notify")
if notify_calls != 1:
    fails.append(f"{notify_calls} Notify calls for one firing, expected 1")
if "byte 2" not in bus:
    fails.append("notification was not critical urgency (hint byte 2)")
if "int32 0" not in bus:
    fails.append("notification did not ask to never expire (int32 0)")
if "finished" in bus:
    fails.append("a second notification was still being sent")
print(f"notify calls: {notify_calls} | id logged: {row[4] if row else '?'}")

# ---- 2. dismissing the notification stops the alarm mid-sound
row = fire_one("dismissme", "--repeat 10 --sound alarm-clock-elapsed")
if row:
    if not wait_for(lambda: bool(paplays()), 6):
        fails.append("the alarm sound never started")
    else:
        time.sleep(0.4)
        pid = row[4]
        out = sh(f"gdbus call --session --dest org.freedesktop.Notifications "
                 f"--object-path /org/freedesktop/Notifications "
                 f"--method org.freedesktop.Notifications.CloseNotification {pid}")
        print("close call:", (out.stdout or out.stderr).strip() or "ok")
        if not wait_for(lambda: not paplays(), 3):
            fails.append("dismissing the notification did not stop the alarm sound")
        else:
            print("sound stopped on dismissal")
        if not wait_for(lambda: not sh("pgrep -x notify-send").stdout.strip(), 3):
            fails.append("notify-send stayed running after dismissal")
        if not wait_for(lambda: not sh("pgrep -f 'nl-timer --_run'").stdout.strip(), 4):
            fails.append("the timer daemon stayed running after dismissal")

# ---- 3. undismissed: the sound finishes on its own and nothing leaks
row = fire_one("nodismiss", "--repeat 1")
if not wait_for(lambda: not paplays(), 20):
    fails.append("sound did not finish on its own")
if not wait_for(lambda: not sh("pgrep -f 'nl-timer --_run'").stdout.strip(), 8):
    fails.append("the timer daemon did not exit after firing")
leftover = sh("pgrep -a -x notify-send").stdout.strip()
if leftover:
    fails.append(f"notify-send leaked: {leftover}")
print("undismissed case finished without leaks")

sh(f"{TIMER} clear")
if fails:
    for failure in fails:
        print("FAIL", failure)
    sys.exit(1)
print("alarm: all cases pass")
