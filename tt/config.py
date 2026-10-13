"""School configuration: the cycle layout and class display names.

A config directory holds:
  school.json     blocks (weeks of the cycle), weekday names, period names and
                  times (a period may span several TASS period numbers), and the
                  order years print in.
  classnames.csv  code,name,block - display name for a TASS class code; block
                  is blank for all blocks or a block number (1-based) when the
                  name changes per block, as main lessons do.
Both are optional; without them the editor shows Day N / PN and class codes.
"""
import csv
import json
from pathlib import Path

DEFAULT = {"school": "", "term": "", "weekdays": [], "blocks": [], "periods": [], "year_order": []}


def load(directory):
    cfg = dict(DEFAULT)
    cfg["names"] = []
    if not directory:
        return cfg
    directory = Path(directory)
    school = directory / "school.json"
    if school.exists():
        cfg.update(json.loads(school.read_text(encoding="utf-8")))
    names = directory / "classnames.csv"
    if names.exists():
        with names.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row["code"]:
                    cfg["names"].append([row["code"], row["name"], int(row["block"]) if row.get("block") else None])
    return cfg
