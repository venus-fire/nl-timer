# nl-timer

Natural language timers for a Linux desktop. One stdlib Python file, no
dependencies, a big block clock in the terminal, and an alarm you silence by
dismissing the notification.

```
$ timer 10m
3f2a  "tea"  10m  ->  today 4:26:00 PM
```

then the clock view takes over until it fires.

## Install

The repo is the install. There is no separate copy to keep in sync: clone it
where it should live, then symlink it into `PATH`.

```sh
git clone https://github.com/venus-fire/nl-timer.git ~/.local/share/nl-timer
ln -sf ../share/nl-timer/nl-timer ~/.local/bin/nl-timer
ln -sf ../share/nl-timer/nl-timer ~/.local/bin/timer
ln -sf ../share/nl-timer/nl-timer ~/.local/bin/tmr
```

Updating is `git -C ~/.local/share/nl-timer pull`, and editing the file in the
repo edits the installed tool. `~/.local/bin` needs to be on your `PATH`. Requires Python 3.11 or newer, a
notification server that speaks `org.freedesktop.Notifications`, and one of
`paplay`, `pw-play`, `canberra-gtk-play` or `ffplay` for sound.

## Usage

```
timer 10m                    ten minutes from now
timer in 1 hour 30 minutes   durations, spelled or numeric
timer 1h30m                  glued
timer set 12:15              a clock time, next occurrence
timer until 5pm              am/pm or 24 hour
timer half past five         spoken clock forms
timer quarter to six         also ten o'clock, nine thirty am
timer noon                   noon or midnight
timer twenty five minutes    number words
timer 90                     a bare number means minutes
timer remind me in 20 minutes
```

```
timer 10m -l tea             with a label
timer 10m -d                 schedule only, skip the clock view
timer 10m -n                 dry run, print the resolved target
timer watch                  big clock for the next timer
timer watch 3f2a             big clock for one timer
timer list                   what is running
timer cancel 3f2a            by id, a prefix is enough
timer clear                  cancel everything
```

Flags: `-l/--label`, `-d/--detach`, `-f/--foreground`, `-n/--dry-run`,
`-s/--silent`, `--sound`, `--repeat`, `--volume`, `--today`, `--tomorrow`.

Clock times mean the nearest occurrence, so `timer set 12:15` at 1pm arms
tomorrow's 12:15. It says so: the resolved time is always printed, and
anything more than 12 hours out gets an explicit warning. `--today` refuses a
time that already passed, `--tomorrow` forces the next day.

Anything the parser cannot fully account for is an error rather than a guess,
so `timer 10m banana` refuses instead of quietly arming ten minutes.

## The clock view

```
                    tea
       █████ █████    █████ █████
       █   █ █     ██ █   █ █   █
       █   █ █████    █   █ █   █
       █   █     █ ██ █   █ █   █
       █████ █████    █████ █████

                ends 4:26 PM
       ███████████████░░░░░░░░░░░░░░░

          q leaves this view   c cancels the timer
```

Digits turn yellow under a minute and red at zero. The progress bar fills as
the timer runs. Narrow terminals lose the hour field rather than overflowing.

The clock is only a viewer. The timer is a detached process that does not care
whether you are watching, so:

- `q` leaves with the timer still armed, and prints what is left
- `c` cancels the timer
- `ctrl-c` cancels it only under `-f`
- closing the terminal kills the view and nothing else

## Settings

`~/.config/nl-timer/config.toml`, created on first change.

```toml
sound = "alarm-clock-elapsed"
sound_repeats = 3
volume = 100
notify = true
bigclock = "auto"
```

```
timer config                 show all of it
timer config sound none      silence the alarm
timer config volume 40
timer config bigclock off    never open the clock view
timer sounds                 list the installed sound files
timer sound bell             shorthand
timer 10m --sound tea.oga --volume 30 --repeat 2
```

`sound` takes a name from `timer sounds`, an absolute path, or `none`.
Settings are snapshotted into each timer when it is scheduled, so changing the
config later does not change timers already running.

## How the alarm behaves

A firing raises exactly one critical notification, and it never expires on its
own. Dismissing it stops the alarm sound immediately, mid-note.

That works because `notify-send -w` blocks until the notification is closed and
`-p` prints its id, so the alarm can watch that process and cut the player the
moment it exits. If nobody dismisses, the sound plays its repeats and stops,
and the notification stays on screen.

Every firing is appended to `~/.local/state/nl-timer/fired.log` with the
timestamp, timer id, label, what was asked for, and the notification id.

## Tests

```sh
./nl-timer --selftest            # 67 cases: parsing, geometry, config
python3 tests/pty_test.py        # drives the clock view in a real pty
python3 tests/alarm_test.py       # one notification, dismissal kills the sound
python3 tests/frame_preview.py    # dump frames as text
```

The alarm test needs a live desktop session, since it posts real notifications
and closes them over D-Bus.

## Why not a language model

`cactus-needle` was installed and benchmarked against a `set_timer` tool
schema on x86_64 CPU. It is a genuinely interesting design, and it is not
usable here.

- 8 to 10 seconds per query when it generated, against microseconds of regex
- "10 minutes" became 10 hours, "5 minutes and 30 seconds" became 5 hours 30
  minutes, "timer set 12:15" came back as a 12 hour 15 minute delay
- the confidence head was inverted, 0.79 on empty output and 0.068 on a
  correct parse, so it cannot gate a fallback
- it bled state between unrelated queries even with `stateless=True`

What it did do well is extract a label from "remind me in half an hour to take
the pasta off", which the regex parser cannot do at all. That is the one thing
worth revisiting, but not at ten seconds and forty percent wrong.

## Known gaps

- Timers do not survive a reboot. Records stay behind with dead PIDs and
  `timer list` prunes them.
- With `notify = false` there is nothing to dismiss, so the sound runs its full
  repeats.
- `%-I` and `%-d` in `strftime` are glibc only. This would need changes on
  macOS.
