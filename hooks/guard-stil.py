#!/usr/bin/env python3
"""PostToolUse: misst den Stil, sobald ein Kapitel geschrieben wurde.

Der Text ist zu diesem Zeitpunkt schon da — hier wird nichts verhindert, sondern
sofort zurückgemeldet. Das ist der Unterschied zu einem Bericht, den jemand
später liest: der Writer sieht seinen Befund, während er noch am Kapitel ist.

Exit 2 trägt die Befunde zurück an das Modell. Ohne Befund still.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WERKZEUG = Path(__file__).resolve().parent.parent / "tools" / "stil_pruefen.py"


def wurzel(start: Path) -> Path | None:
    for k in (start, *start.parents):
        if (k / "wissen").is_dir():
            return k
    return None


def main():
    try:
        daten = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if daten.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        sys.exit(0)

    pfad_roh = (daten.get("tool_input") or {}).get("file_path") or ""
    if not pfad_roh:
        sys.exit(0)

    pfad = Path(pfad_roh)
    teile = pfad.as_posix()
    if not (teile.endswith((".qmd", ".md")) and ("/kapitel/" in teile or teile.startswith("kapitel/"))):
        sys.exit(0)
    if not pfad.exists() or not WERKZEUG.exists():
        sys.exit(0)

    w = wurzel(Path(daten.get("cwd") or ".").resolve()) or wurzel(pfad.resolve().parent)
    if w is None:
        sys.exit(0)

    try:
        lauf = subprocess.run(
            [sys.executable, str(WERKZEUG), str(pfad), "--ausloeser", "hook"],
            cwd=w, capture_output=True, text=True, timeout=25,
        )
    except Exception:
        sys.exit(0)

    if lauf.returncode == 1 and lauf.stdout.strip():
        zeilen = [z for z in lauf.stdout.splitlines() if z.strip()]
        print(
            "Stilbefunde in dieser Datei (gemessen, nicht beurteilt):\n"
            + "\n".join(zeilen[:12])
            + "\n\nS-01 und S-02 löst Streichen. S-03 ist eine Glossarlücke, "
            "S-04 braucht ein Beispiel — keins davon löst mehr Text.",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
