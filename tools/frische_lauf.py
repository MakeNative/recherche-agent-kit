#!/usr/bin/env python3
"""Holt Quellen neu und meldet, welche Aussagen dadurch wackeln.

    frische_lauf.py [--tier 1] [--ids A-01,A-07] [--anwenden]

Ohne `--anwenden` wird nur verglichen und berichtet — nichts überschrieben.
Das ist Absicht: ein Neuabruf macht Zitate ungültig, und das soll eine
bewusste Entscheidung sein.

Mit `--anwenden`:
  1. Rohtext neu holen und neu chunken
  2. jede Aussage dieser Quelle gegen den neuen Stand prüfen
  3. wackelnde Aussagen auf `pruefen` setzen, mit Notiz
  4. `wissen/FRISCHE.md` schreiben

Schreibt immer `wissen/FRISCHE.md`. Exit 1, wenn sich etwas geändert hat.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gemeinsam as g  # noqa: E402
import quelle_holen as qh  # noqa: E402


def text_holen(q: dict) -> str | None:
    url = q.get("url") or ""
    if re.match(r"https?://github\.com/[^/]+/[^/]+/?$", url.rstrip("/")):
        try:
            text, _ = qh.repo_holen(url, Path.cwd())
            return text
        except SystemExit:
            return None
    for kandidat in filter(None, (qh.markdown_variante(url), url)):
        try:
            text, _, _ = qh.holen(kandidat)
            if text.strip() and "<html" not in text[:500].lower():
                return text
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
            continue
    return None


def claims_der_quelle(w: Path, qid: str) -> list[tuple[Path, dict]]:
    treffer = []
    cdir = w / "claims"
    if not cdir.is_dir():
        return treffer
    for datei in sorted(cdir.glob("*.jsonl")):
        for c in g.jsonl_lesen(datei):
            if c.get("quelle") == qid:
                treffer.append((datei, c))
    return treffer


def claims_neu_bewerten(w: Path, q: dict) -> list[dict]:
    """Setzt Aussagen auf `pruefen`, deren Chunk oder Zitat nicht mehr passt."""
    chunks = {c["chunk_id"]: c for c in g.chunks_lesen(w, q)}
    betroffen: list[dict] = []
    nach_datei: dict[Path, list[dict]] = {}

    for datei, _ in claims_der_quelle(w, q["id"]):
        nach_datei.setdefault(datei, g.jsonl_lesen(datei))

    for datei, claims in nach_datei.items():
        geaendert = False
        for c in claims:
            if c.get("quelle") != q["id"] or c.get("status") == "offen":
                continue
            ch = chunks.get(c.get("chunk_id", ""))
            grund = None
            if not ch:
                grund = f"Chunk `{c.get('chunk_id')}` existiert nicht mehr (K-05)"
            else:
                text = g.leerraum_normal(g.chunk_text(w, q, ch)).lower()
                if g.leerraum_normal(c.get("zitat", "")).lower() not in text:
                    grund = "Zitat steht nicht mehr wörtlich im Abschnitt (Q-03)"
            if grund:
                c["status"] = "pruefen"
                c["frische_notiz"] = f"{g.heute()}: {grund}"
                geaendert = True
                betroffen.append(
                    {"kapitel": datei.stem, "claim": c.get("claim_id", "?"), "grund": grund}
                )
        if geaendert:
            g.jsonl_schreiben(datei, claims)
    return betroffen


def bericht(zeilen: list[dict], angewendet: bool) -> str:
    z = [
        "<!-- GENERIERT von frische_lauf.py -->",
        "# Frische",
        "",
        f"Stand {g.heute()} · {len(zeilen)} Quellen geprüft · "
        f"{sum(1 for x in zeilen if x['geaendert'])} geändert"
        + ("" if angewendet else " · **Probelauf, nichts überschrieben**"),
        "",
        "| ID | Titel | St | Abgerufen | Geändert | Betroffene Aussagen |",
        "|---|---|---|---|---|---|",
    ]
    for x in sorted(zeilen, key=lambda y: y["id"]):
        z.append(
            f"| {x['id']} | {x['titel']} | {x['tier']} | {x['abgerufen']} | "
            f"{'ja' if x['geaendert'] else 'nein' if x['erreichbar'] else 'nicht erreichbar'} | "
            f"{len(x['betroffen'])} |"
        )
    z.append("")

    unerreichbar = [x for x in zeilen if not x["erreichbar"]]
    if unerreichbar:
        z += [
            "## Nicht erreichbar",
            "",
            "Diese Quellen konnten nicht geholt werden. Sie gelten weiter als",
            "gültig, aber ihr Stand ist unbestätigt (Q-05).",
            "",
        ]
        z += [f"- {x['id']} — {x['titel']}" for x in unerreichbar]
        z.append("")

    betroffen = [(x, b) for x in zeilen for b in x["betroffen"]]
    if betroffen:
        z += ["## Aussagen auf `pruefen`", ""]
        for x, b in betroffen:
            z.append(f"- `{b['kapitel']}` · `{b['claim']}` · Quelle {x['id']} — {b['grund']}")
        z.append("")
        z += [
            "## Nächster Schritt",
            "",
            "Die Skill `recherche` belegt diese Aussagen neu oder streicht sie.",
            "Betroffene Kapitel gehen danach durch `kapitel` und `gates`.",
            "",
        ]
    elif angewendet:
        z += ["Kein Beleg ist durch den Neuabruf ungültig geworden.", ""]
    return "\n".join(z)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tier", type=int, default=1, help="nur diese Stufe prüfen (0 = alle)")
    ap.add_argument("--ids", default="")
    ap.add_argument("--anwenden", action="store_true")
    a = ap.parse_args()

    w = g.wurzel()
    alle = g.quellen(w)
    if not alle:
        g.fehler("sources.jsonl ist leer.")

    gewaehlt = {s.strip() for s in a.ids.split(",") if s.strip()}
    auswahl = [
        q
        for q in alle
        if (q["id"] in gewaehlt if gewaehlt else (a.tier == 0 or int(q.get("tier", 9)) == a.tier))
    ]
    if not auswahl:
        g.fehler("Keine Quelle passt zur Auswahl.")

    zeilen = []
    for q in auswahl:
        neu = text_holen(q)
        eintrag = {
            "id": q["id"],
            "titel": q.get("titel", "?"),
            "tier": q.get("tier", "?"),
            "abgerufen": q.get("abgerufen", "?"),
            "erreichbar": neu is not None,
            "geaendert": False,
            "betroffen": [],
        }
        if neu is None:
            g.warnung(f"{q['id']}: nicht erreichbar")
            zeilen.append(eintrag)
            continue

        hash_neu = hashlib.sha256(neu.encode("utf-8")).hexdigest()
        eintrag["geaendert"] = hash_neu != q.get("sha256")
        if eintrag["geaendert"] and a.anwenden:
            ordner = g.quellordner(w, q)
            (ordner / "raw.md").write_text(neu, encoding="utf-8")
            subprocess.run(
                [sys.executable, str(Path(__file__).parent / "chunken.py"), q["id"]],
                cwd=w,
                capture_output=True,
                text=True,
            )
            q["sha256"] = hash_neu
            q["zeichen"] = len(neu)
            q["abgerufen"] = g.heute()
            q["auffaelligkeiten"] = qh.auffaelligkeiten(neu)
            eintrag["betroffen"] = claims_neu_bewerten(w, q)
            if (ordner / "meta.json").exists():
                (ordner / "meta.json").write_text(
                    json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8"
                )
        zeilen.append(eintrag)

    if a.anwenden:
        g.quellen_schreiben(w, alle)

    pfad = w / "wissen" / "FRISCHE.md"
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(bericht(zeilen, a.anwenden), encoding="utf-8")

    geaendert = [x for x in zeilen if x["geaendert"]]
    g.spur(
        w, "frische",
        angewendet=a.anwenden,
        geprueft=len(zeilen),
        geaendert=[x["id"] for x in geaendert],
        unerreichbar=[x["id"] for x in zeilen if not x["erreichbar"]],
        claims_auf_pruefen=sum(len(x["betroffen"]) for x in zeilen),
    )
    print(f"{len(zeilen)} Quellen geprüft, {len(geaendert)} geändert → wissen/FRISCHE.md")
    for x in geaendert:
        print(f"  {x['id']}  {x['titel'][:60]}  betroffene Aussagen: {len(x['betroffen'])}")
    if geaendert and not a.anwenden:
        print("Probelauf. Mit --anwenden werden Rohtexte und Chunks erneuert.")
    raise SystemExit(1 if geaendert else 0)


if __name__ == "__main__":
    main()
