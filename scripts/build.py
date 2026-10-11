"""Rebuild the database, figures, documentation and validated static website."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
environment = os.environ.copy()
environment.setdefault("MPLCONFIGDIR", str(ROOT / "build" / "matplotlib"))
environment.setdefault("XDG_CACHE_HOME", str(ROOT / "build" / "cache"))

for script in ("osalr/build_osalr.py", "scripts/make_figures.py", "scripts/build_site.py"):
    subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT, env=environment, check=True)
