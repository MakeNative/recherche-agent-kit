#!/usr/bin/env python3
"""SessionStart: zeigt den Stand des Dokumentprojekts, falls man in einem steht.

Kurz halten. Diese Ausgabe landet in jedem Sitzungskontext; was hier steht,
kostet in jeder Sitzung Platz (K-02).
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def wurzel(start: Path) -> Path | None:
    for k in (start, *start.parents):
        if (k / "wissen").is_dir():
            return k
    return None


def jsonl(pfad: Path) -> list[dict]:
    if not pfad.exists():
        return []
    raus = []
    for zeile in pfad.read_text(encoding="utf-8", errors="replace").splitlines():
        zeile = zeile.strip()
        if zeile.startswith("{"):
            try:
                raus.append(json.loads(zeile))
            except json.JSONDecodeError:
                pass
    return raus


def main():
    w = wurzel(Path.cwd())
    if w is None:
        return

    quellen = jsonl(w / "wissen" / "sources.jsonl")
    if not quellen:
        print("recherche-kit: Projekt eingerichtet, Bibliothek noch leer. "
              "Nächster Schritt: /recherche-kit:quelle-aufnehmen")
        return

    tot = [q["id"] for q in quellen if q.get("status") in ("ueberholt", "widersprochen")]
    unklar = sum(1 for q in quellen if q.get("status") == "unklar")
    ohne_abgleich = sum(1 for q in quellen if int(q.get("tier", 9)) > 1 and not q.get("abgleich_am"))

    claims = [c for d in (w / "claims").glob("*.jsonl") for c in jsonl(d)] if (w / "claims").is_dir() else []
    offen = sum(1 for c in claims if c.get("status") == "offen")
    zu_pruefen = sum(1 for c in claims if c.get("status") == "pruefen")

    kapitel = sorted((w / "kapitel").glob("*.qmd")) if (w / "kapitel").is_dir() else []
    leer = sum(1 for k in kapitel if len(k.read_text(errors="replace").strip()) < 80)
    marken = sum(
        len(re.findall(r"<!--\s*beispiel:", k.read_text(errors="replace"))) for k in kapitel
    )

    zeilen = [
        f"recherche-kit · {len(quellen)} Quellen · "
        f"{len(claims)} Aussagen ({offen} offen, {zu_pruefen} zu prüfen) · "
        f"{len(kapitel) - leer}/{len(kapitel)} Kapitel geschrieben"
    ]
    if tot:
        zeilen.append(f"  überholt oder widersprochen: {', '.join(tot[:8])} — belegen nichts (Q-04)")
    if ohne_abgleich:
        zeilen.append(f"  {ohne_abgleich} Drittquelle(n) ohne Frische-Abgleich: /recherche-kit:frische")
    if unklar:
        zeilen.append(f"  {unklar} Quelle(n) mit Status `unklar`")
    if marken:
        zeilen.append(f"  {marken} offene Beispielmarke(n)")

    for name, hinweis in (
        ("quellen-report.md", "Quellenbefunde offen"),
        ("stil-report.md", "Stilbefunde offen"),
    ):
        pfad = w / "gates" / name
        if pfad.exists():
            text = pfad.read_text(errors="replace")
            if m := re.search(r"(\d+) Befunde", text):
                if int(m.group(1)) > 0:
                    zeilen.append(f"  {hinweis}: {m.group(1)} in gates/{name}")

    zeilen.append("  Leseweg: INDEX → CARD → Rohtext über Chunk-ID (K-01)")
    print("\n".join(zeilen))


if __name__ == "__main__":
    main()
