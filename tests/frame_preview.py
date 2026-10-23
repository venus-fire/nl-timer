import importlib.util
import importlib.machinery
import os
import re
import sys

spec = importlib.util.spec_from_loader(
    "nlt", importlib.machinery.SourceFileLoader("nlt", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nl-timer")))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

sample = {"id": "3f2a", "label": "tea", "seconds": 600,
          "created_epoch": 1000.0, "target_epoch": 1600.0}

for now, cols, title in ((1300.0, 80, "mid-run 80x24"), (1590.0, 80, "last 10s"),
                         (1601.0, 80, "after target"), (1300.0, 44, "narrow 44")):
    print(f"=== {title} " + "=" * 20)
    frame = m.build_frame(sample, now, cols, 24, blink=True)
    for line in frame:
        print(re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line).rstrip())
    print()
