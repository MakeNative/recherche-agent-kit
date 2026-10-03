#!/usr/bin/env python3
"""Erzeugt INDEX.md und THEMEN.md aus sources.jsonl und den Karten.

    index_bauen.py [--grenze 3000]

Beide Dateien sind Build-Artefakte (K-03) und werden nie von Hand bearbeitet.
Das Skript bricht ab, wenn INDEX.md die Token-Grenze aus K-02 überschreitet —
dann gehört Inhalt in die Karten, nicht in den Index.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gemeinsam as g  # noqa: E402

GRENZE = 3000

KOPF = """<!-- GENERIERT von index_bauen.py — nicht von Hand bearbeiten (K-03). -->
# Quellenindex

Leseweg: diese Zeile → `CARD.md` der Quelle → erst dann Rohtext über die
Chunk-ID (K-01). Die Spalte „Beantwortet Fragen zu" ist Routing, kein Inhalt.

Stufen nach Q-01: 1 offizielle Doku · 2 Praxis-Repos · 3 Forschung ·
4 Community · 5 Marktdaten. Nur Stufe 1 trägt Funktions- und Zahlenaussagen.

"""

STATUS_ZEICHEN = {
    "aktuell": "ok",
    "ueberholt": "ÜBERHOLT",
    "widersprochen": "WIDERSPRUCH",
    "unklar": "unklar",
}


def karte_haken(w: Path, q: dict) -> str:
    """Fällt `haken` in sources.jsonl leer aus, als Notlösung die Karte anlesen."""
    if q.get("haken"):
        return q["haken"]
    karte = g.quellordner(w, q) / "CARD.md"
    if karte.exists():
        if m := re.search(r"^\*\*Worum es geht:\*\*\s*(.+)$", karte.read_text(encoding="utf-8"), re.M):
            return m.group(1).strip().rstrip(".")[:90]
    return "— (haken fehlt)"


def index_bauen(w: Path, qs: list[dict]) -> str:
    nach_kategorie: dict[str, list[dict]] = defaultdict(list)
    for q in qs:
        nach_kategorie[q.get("kategorie", "ohne-kategorie")].append(q)

    zeilen = [KOPF]
    for kategorie in sorted(nach_kategorie):
        zeilen.append(f"## {kategorie}\n")
        zeilen.append("| ID | Titel | St | Abgerufen | Stand | Beantwortet Fragen zu |")
        zeilen.append("|---|---|---|---|---|---|")
        for q in sorted(nach_kategorie[kategorie], key=lambda x: x["id"]):
            status = STATUS_ZEICHEN.get(q.get("status", "unklar"), q.get("status", "?"))
            auff = " ⚠" if q.get("auffaelligkeiten") else ""
            zeilen.append(
                f"| {q['id']} | {q.get('titel', '?')}{auff} | {q.get('tier', '?')} | "
                f"{q.get('abgerufen', '?')} | {status} | {karte_haken(w, q)} |"
            )
        zeilen.append("")

    gesamt = len(qs)
    ueberholt = sum(1 for q in qs if q.get("status") in ("ueberholt", "widersprochen"))
    auffaellig = sum(1 for q in qs if q.get("auffaelligkeiten"))
    zeilen.append("---\n")
    zeilen.append(
        f"{gesamt} Quellen · {ueberholt} überholt oder widersprochen · "
        f"{auffaellig} mit Auffälligkeit nach Q-06 (⚠)"
    )
    zeilen.append("")
    zeilen.append("Pfad einer Quelle: `wissen/quellen/<kategorie>/<slug>/`")
    return "\n".join(zeilen) + "\n"


def themen_bauen(w: Path, qs: list[dict]) -> str:
    nach_thema: dict[str, list[str]] = defaultdict(list)
    ohne = []
    for q in qs:
        themen = q.get("themen") or []
        if not themen:
            ohne.append(q["id"])
        for t in themen:
            nach_thema[t].append(q["id"])

    zeilen = [
        "<!-- GENERIERT von index_bauen.py — nicht von Hand bearbeiten (K-03). -->",
        "# Themenkarte",
        "",
        "Route über die Frage, nicht über das Dokument. Suche hier dein Thema,",
        "nimm die Quellen-IDs und lies dann deren Karten (K-01).",
        "",
        "## Thema → Quellen",
        "",
    ]
    for t in sorted(nach_thema):
        zeilen.append(f"- **{t}** — {', '.join(sorted(nach_thema[t]))}")
    if not nach_thema:
        zeilen.append("- noch keine Themen gesetzt (`themen` in meta.json)")
    zeilen.append("")

    claim_dir = w / "claims"
    if claim_dir.is_dir():
        zeilen += ["## Kapitel → tatsächlich belegte Quellen", ""]
        for datei in sorted(claim_dir.glob("*.jsonl")):
            claims = g.jsonl_lesen(datei)
            benutzt = sorted({c["quelle"] for c in claims if c.get("quelle")})
            offen = sum(1 for c in claims if c.get("status") == "offen")
            zeilen.append(
                f"- **{datei.stem}** — {len(claims)} Aussagen, {offen} offen"
                + (f" · Quellen: {', '.join(benutzt)}" if benutzt else "")
            )
        zeilen.append("")

    if ohne:
        zeilen += [
            "## Ohne Thema",
            "",
            "Diese Quellen sind über die Themenkarte nicht findbar:",
            "",
            f"{', '.join(sorted(ohne))}",
            "",
        ]
    return "\n".join(zeilen) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--grenze", type=int, default=GRENZE)
    a = ap.parse_args()

    w = g.wurzel()
    qs = g.quellen(w)
    if not qs:
        g.fehler("sources.jsonl ist leer — erst Quellen aufnehmen.")

    index = index_bauen(w, qs)
    token = g.token_schaetzung(index)
    if token > a.grenze:
        g.fehler(
            f"INDEX.md wäre {token} Token groß, Grenze ist {a.grenze} (K-02).\n"
            "       Kürze die `haken`-Felder in sources.jsonl — inhaltliche "
            "Zusammenfassungen gehören in CARD.md, nicht in den Index.",
            code=3,
        )

    (w / "wissen" / "INDEX.md").write_text(index, encoding="utf-8")
    (w / "wissen" / "THEMEN.md").write_text(themen_bauen(w, qs), encoding="utf-8")

    print(f"INDEX.md   {len(qs)} Quellen, ~{token} Token (Grenze {a.grenze})")
    print("THEMEN.md  geschrieben")
    fehlt = [q["id"] for q in qs if not q.get("haken")]
    if fehlt:
        print(f"Ohne `haken` und damit schlecht routbar: {', '.join(fehlt)}")


if __name__ == "__main__":
    main()
