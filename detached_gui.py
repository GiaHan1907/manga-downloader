"""Spawn the Tkinter GUI outside the launcher/terminal process tree."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        return 2

    gui_script = Path(sys.argv[1]).resolve()
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists() or not gui_script.exists():
        return 1

    detached_process = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
    new_process_group = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    subprocess.Popen(
        [str(pythonw), str(gui_script)],
        cwd=str(gui_script.parent),
        creationflags=detached_process | new_process_group,
        close_fds=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
