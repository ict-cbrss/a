"""Backups: one zip of the working files, and restoring it.

Git keeps every committed version of timetable/TTable.txt and config/, and
start_term files the old term under archive/. This covers what git does not
hold: the student file and the files on someone's computer between commits.
"""
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path


def backup(out_dir, ttable, scourse=None, config_dir=None, when=None):
    """Zip TTable.txt, SCourse.txt and config/ into out_dir/backup-<term>-<time>.zip."""
    term = ""
    if config_dir and (Path(config_dir) / "school.json").exists():
        term = json.loads((Path(config_dir) / "school.json").read_text(encoding="utf-8")).get("term", "")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", term).strip("-").lower()
    when = when or datetime.now()
    name = f"backup-{slug + '-' if slug else ''}{when:%Y%m%d-%H%M}.zip"
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(ttable, "TTable.txt")
        if scourse and Path(scourse).exists():
            z.write(scourse, "SCourse.txt")
        if config_dir:
            for f in sorted(Path(config_dir).iterdir()):
                if f.is_file():
                    z.write(f, f"config/{f.name}")
    return path


def restore(zip_path, out_dir):
    """Unpack a backup into out_dir (TTable.txt, SCourse.txt, config/). Nothing else is touched."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if not n.startswith("/") and ".." not in n]
        z.extractall(out, names)
    return [out / n for n in names]
