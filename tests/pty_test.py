"""Drive the big clock in a real pty: draw, then q to leave, then c to cancel."""
import os
import pty
import select
import subprocess
import sys
import time

TIMER = (os.environ.get("NL_TIMER_BIN") or
          os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "nl-timer"))


def run(args, keys, wait_before=1.5):
    master, slave = pty.openpty()
    env = dict(os.environ, TERM="xterm-256color", COLUMNS="80", LINES="24")
    proc = subprocess.Popen([TIMER] + args, stdin=slave, stdout=slave, stderr=slave,
                            env=env, start_new_session=True)
    os.close(slave)
    chunks = []
    deadline = time.time() + wait_before
    while time.time() < deadline:
        ready, _, _ = select.select([master], [], [], 0.1)
        if ready:
            try:
                chunks.append(os.read(master, 65536))
            except OSError:
                break
    for key in keys:
        try:
            os.write(master, key)
        except OSError:
            break
        time.sleep(0.6)
    end = time.time() + 8
    while time.time() < end and proc.poll() is None:
        ready, _, _ = select.select([master], [], [], 0.1)
        if ready:
            try:
                chunks.append(os.read(master, 65536))
            except OSError:
                break
    try:
        proc.wait(timeout=6)
    except subprocess.TimeoutExpired:
        proc.kill()
    try:
        while True:
            ready, _, _ = select.select([master], [], [], 0.05)
            if not ready:
                break
            chunks.append(os.read(master, 65536))
    except OSError:
        pass
    os.close(master)
    return proc.returncode, b"".join(chunks).decode("utf-8", "replace")


fails = []

code, out = run(["20s", "-l", "ptytest"], [b"q"], wait_before=1.5)
if "\x1b[?1049h" not in out:
    fails.append("q-case never entered the alternate screen")
if "█" not in out:
    fails.append("q-case drew no block art")
if "\x1b[?1049l" not in out:
    fails.append("q-case never restored the screen")
if "ptytest" not in out:
    fails.append("q-case did not show the label")
if code != 0:
    fails.append(f"q-case exit {code}")
if "still running" not in out:
    fails.append("q-case should report the timer still running")
print("q case: exit", code, "| keys seen:", "q" ,
      "| screen restored:", "\x1b[?1049l" in out)

code, out = run(["90s", "-l", "cancelme"], [b"c"], wait_before=1.2)
if "cancelled" not in out:
    fails.append("c-case did not report a cancel")
if code != 130:
    fails.append(f"c-case exit {code}, expected 130")
print("c case: exit", code, "| cancelled line:", "cancelled" in out)

code, out = run(["4s", "-l", "firenow"], [], wait_before=1.0)
if "finished" not in out:
    fails.append("fire case never reported the finish")
print("fire case: exit", code, "| finished line:", "finished" in out)

subprocess.run([TIMER, "clear"], capture_output=True)

if fails:
    for failure in fails:
        print("FAIL", failure)
    sys.exit(1)
print("pty: all big clock cases pass")
