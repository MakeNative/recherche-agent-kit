#!/usr/bin/env python3
"""Zerlegt den Rohtext einer Quelle in zitierbare Abschnitte.

    chunken.py <quellen-id> [<quellen-id> ...]
    chunken.py --alle

Chunk-IDs sind stabil nach K-05: `<quellen-id>#<slug/pfad/der/ueberschriften>`.
Code-Blöcke werden erkannt, damit `#` darin keine Überschrift auslöst.
Abschnitte ohne eigene Überschrift hängen am letzten Abschnitt.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gemeinsam as g  # noqa: E402

UEBERSCHRIFT = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
ZAUN = re.compile(r"^\s*(```|~~~)")

# Sehr große Abschnitte werden weiter geteilt, damit ein Agent nicht
# versehentlich 200 KB lädt (K-01).
MAX_ZEICHEN = 12_000


def zerlegen(zeilen: list[str], quelle_id: str) -> list[dict]:
    abschnitte: list[dict] = []
    pfad: list[str] = []
    im_zaun = False
    aktuell: dict | None = None

    def abschliessen(bis: int):
        if aktuell is not None:
            aktuell["zeilen"][1] = bis
            abschnitte.append(aktuell)

    for nr, zeile in enumerate(zeilen, 1):
        if ZAUN.match(zeile):
            im_zaun = not im_zaun
        if not im_zaun and (m := UEBERSCHRIFT.match(zeile)):
            abschliessen(nr - 1)
            ebene, titel = len(m.group(1)), m.group(2).strip()
            pfad = pfad[: ebene - 1]
            while len(pfad) < ebene - 1:
                pfad.append("ohne-titel")
            pfad.append(titel)
            aktuell = {
                "chunk_id": f"{quelle_id}#" + "/".join(g.slug(t) for t in pfad),
                "pfad": list(pfad),
                "ueberschrift": titel,
                "ebene": ebene,
                "zeilen": [nr, nr],
            }
    abschliessen(len(zeilen))

    if not abschnitte and zeilen:
        abschnitte = [
            {
                "chunk_id": f"{quelle_id}#volltext",
                "pfad": ["Volltext"],
                "ueberschrift": "Volltext",
                "ebene": 1,
                "zeilen": [1, len(zeilen)],
            }
        ]
    return abschnitte


def teilen_wenn_gross(abschnitte: list[dict], zeilen: list[str]) -> list[dict]:
    ergebnis = []
    for a in abschnitte:
        von, bis = a["zeilen"]
        text = "\n".join(zeilen[von - 1 : bis])
        if len(text) <= MAX_ZEICHEN:
            a["zeichen"] = len(text)
            ergebnis.append(a)
            continue
        # In gleich große Teile schneiden, Zeilengrenzen respektieren.
        teile = max(2, -(-len(text) // MAX_ZEICHEN))
        schritt = max(1, (bis - von + 1) // teile)
        start = von
        teil_nr = 1
        while start <= bis:
            ende = min(bis, start + schritt - 1)
            t = dict(a)
            t["chunk_id"] = f"{a['chunk_id']}~{teil_nr}"
            t["zeilen"] = [start, ende]
            t["zeichen"] = len("\n".join(zeilen[start - 1 : ende]))
            t["teil"] = teil_nr
            ergebnis.append(t)
            start = ende + 1
            teil_nr += 1
    return ergebnis


def eindeutig(abschnitte: list[dict]) -> list[dict]:
    """Gleiche Überschriftenpfade bekommen einen Zähler, damit IDs eindeutig bleiben."""
    gesehen: dict[str, int] = {}
    for a in abschnitte:
        basis = a["chunk_id"]
        n = gesehen.get(basis, 0)
        gesehen[basis] = n + 1
        if n:
            a["chunk_id"] = f"{basis}@{n + 1}"
    return abschnitte


def eine_quelle(w: Path, q: dict) -> int:
    ordner = g.quellordner(w, q)
    roh = ordner / "raw.md"
    if not roh.exists():
        g.warnung(f"{q['id']}: raw.md fehlt — erst quelle_holen.py laufen lassen.")
        return 0
    zeilen = roh.read_text(encoding="utf-8", errors="replace").splitlines()
    abschnitte = eindeutig(teilen_wenn_gross(zerlegen(zeilen, q["id"]), zeilen))
    g.jsonl_schreiben(ordner / "chunks.jsonl", abschnitte)
    return len(abschnitte)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--alle", action="store_true")
    a = ap.parse_args()

    w = g.wurzel()
    alle = g.quellen(w)
    if a.alle:
        auswahl = alle
    elif a.ids:
        index = {q["id"]: q for q in alle}
        fehlend = [i for i in a.ids if i not in index]
        if fehlend:
            g.fehler(f"Unbekannte Quellen-ID(s): {', '.join(fehlend)}")
        auswahl = [index[i] for i in a.ids]
    else:
        g.fehler("Entweder Quellen-IDs angeben oder --alle.")

    geaendert = {q["id"]: eine_quelle(w, q) for q in auswahl}
    for q in alle:
        if q["id"] in geaendert:
            q["chunks"] = geaendert[q["id"]]
            ordner = g.quellordner(w, q)
            if (ordner / "meta.json").exists():
                (ordner / "meta.json").write_text(
                    json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8"
                )
    g.quellen_schreiben(w, alle)

    for qid, n in geaendert.items():
        print(f"{qid}: {n} Abschnitte")
    print("Nächster Schritt: Karte schreiben (Stufe 2–5), dann index_bauen.py")


if __name__ == "__main__":
    main()
