#!/usr/bin/env python3
"""Prüft Aussagen gegen ihre Belege und Kapitel gegen ihre Aussagen.

    claims_pruefen.py [kapitel-slug ...] [--kapitel-text]

Prüft nach Regelwerk:
  Q-01  funktion/zahl nur aus Stufe 1
  Q-02  Quellen-ID, Chunk-ID und Zitat vorhanden
  Q-03  Zitat kommt wörtlich im Chunk vor
  Q-04  überholte oder widersprochene Quellen belegen nicht
  Q-05  Abrufdatum und Stand vorhanden
  K-05  Chunk-ID existiert

Mit --kapitel-text zusätzlich über `kapitel/*.qmd`:
  jede Fußnote zeigt auf eine belegte Aussage, und jeder Satz mit einer Zahl
  trägt eine Fußnote.

Exit 0 wenn ohne Befund, 1 mit Befunden, 2 bei Abbruch.
Schreibt `gates/quellen-report.md`.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gemeinsam as g  # noqa: E402

PFLICHT = ("claim_id", "aussage", "typ", "quelle", "chunk_id", "zitat", "status", "stand")
FUSSNOTE = re.compile(r"\[\^([A-Za-z0-9][\w-]*)\]")
ZAHL = re.compile(r"(?<![\w.])\d[\d.,]*\s*(%|Prozent|Mio|Mrd|€|\$|USD|EUR|Token|Sterne|Seiten|MB|KB|GB|x|mal)\b|(?<![\w.])\d{2,}(?![\w.])")
SATZ_ENDE = re.compile(r"(?<=[.!?])\s+")


def chunk_karte(w: Path, q: dict) -> dict[str, dict]:
    return {c["chunk_id"]: c for c in g.chunks_lesen(w, q)}


def claims_pruefen(w: Path, dateien: list[Path]) -> list[dict]:
    qidx = g.quellen_index(w)
    cache: dict[str, dict[str, dict]] = {}
    befunde: list[dict] = []

    def befund(regel, kapitel, claim_id, text):
        befunde.append({"regel": regel, "kapitel": kapitel, "claim": claim_id, "text": text})

    for datei in dateien:
        kapitel = datei.stem
        gesehen_ids = set()
        for c in g.jsonl_lesen(datei):
            cid = c.get("claim_id", "?")
            if cid in gesehen_ids:
                befund("Q-02", kapitel, cid, "Claim-ID doppelt vergeben")
            gesehen_ids.add(cid)

            if c.get("status") == "offen":
                # Offene Aussagen sind kein Fehler, aber sie dürfen nicht in
                # ein Kapitel. Das prüft der Kapitel-Durchlauf.
                continue

            fehlend = [f for f in PFLICHT if not c.get(f)]
            if fehlend:
                befund("Q-02", kapitel, cid, f"Felder fehlen: {', '.join(fehlend)}")
                continue
            if c["typ"] not in g.TYP_CLAIM:
                befund("Q-02", kapitel, cid, f"Unbekannter typ `{c['typ']}`")
            if c["status"] not in g.STATUS_CLAIM:
                befund("Q-02", kapitel, cid, f"Unbekannter status `{c['status']}`")

            q = qidx.get(c["quelle"])
            if not q:
                befund("Q-02", kapitel, cid, f"Quelle `{c['quelle']}` steht nicht in sources.jsonl")
                continue
            if q.get("status") in ("ueberholt", "widersprochen"):
                befund(
                    "Q-04", kapitel, cid,
                    f"Quelle {q['id']} ist `{q['status']}` und darf nichts belegen",
                )
            if c["typ"] in g.TYP_BRAUCHT_TIER1 and int(q.get("tier", 9)) != 1:
                befund(
                    "Q-01", kapitel, cid,
                    f"typ `{c['typ']}` verlangt Stufe 1, {q['id']} ist Stufe {q.get('tier')}",
                )
            if not q.get("abgerufen"):
                befund("Q-05", kapitel, cid, f"Quelle {q['id']} ohne Abrufdatum")

            if q["id"] not in cache:
                cache[q["id"]] = chunk_karte(w, q)
            chunks = cache[q["id"]]
            ch = chunks.get(c["chunk_id"])
            if not ch:
                befund(
                    "K-05", kapitel, cid,
                    f"Chunk `{c['chunk_id']}` existiert nicht — Quelle neu gechunkt?",
                )
                continue

            text = g.leerraum_normal(g.chunk_text(w, q, ch)).lower()
            zitat = g.leerraum_normal(c["zitat"]).lower()
            if zitat and zitat not in text:
                befund(
                    "Q-03", kapitel, cid,
                    f"Zitat nicht wörtlich in `{c['chunk_id']}`: „{c['zitat'][:80]}…"
                    if len(c["zitat"]) > 80 else f"Zitat nicht wörtlich in `{c['chunk_id']}`: „{c['zitat']}\"",
                )
    return befunde


def kapitel_pruefen(w: Path) -> list[dict]:
    befunde: list[dict] = []
    alle_claims: dict[str, dict] = {}
    for datei in sorted((w / "claims").glob("*.jsonl")) if (w / "claims").is_dir() else []:
        for c in g.jsonl_lesen(datei):
            if c.get("claim_id"):
                alle_claims[c["claim_id"]] = c

    kap_dir = w / "kapitel"
    if not kap_dir.is_dir():
        return befunde

    for datei in sorted(kap_dir.glob("*.qmd")):
        text = datei.read_text(encoding="utf-8", errors="replace")
        # Fußnoten-Definitionen am Ende zählen nicht als Verweis.
        verweise = {
            m.group(1)
            for m in FUSSNOTE.finditer(text)
            if not re.match(rf"^\[\^{re.escape(m.group(1))}\]:", text[m.start():])
        }
        for v in sorted(verweise):
            c = alle_claims.get(v)
            if not c:
                befunde.append(
                    {"regel": "Q-02", "kapitel": datei.name, "claim": v,
                     "text": "Fußnote zeigt auf eine Aussage, die in keiner claims-Datei steht"}
                )
            elif c.get("status") != "belegt":
                befunde.append(
                    {"regel": "Q-02", "kapitel": datei.name, "claim": v,
                     "text": f"Aussage ist `{c.get('status')}` und darf noch nicht im Kapitel stehen"}
                )

        im_zaun = False
        for nr, zeile in enumerate(text.splitlines(), 1):
            if zeile.lstrip().startswith(("```", "~~~")):
                im_zaun = not im_zaun
                continue
            if im_zaun or zeile.lstrip().startswith(("|", ">", "#")):
                continue
            for satz in SATZ_ENDE.split(zeile):
                if ZAHL.search(satz) and not FUSSNOTE.search(satz):
                    befunde.append(
                        {"regel": "Q-02", "kapitel": f"{datei.name}:{nr}", "claim": "—",
                         "text": f"Zahl ohne Fußnote: „{g.leerraum_normal(satz)[:110]}\""}
                    )
    return befunde


def bericht(befunde: list[dict], geprueft: int) -> str:
    z = [
        "<!-- GENERIERT von claims_pruefen.py -->",
        "# Gate: Quellen",
        "",
        f"Stand {g.heute()} · {geprueft} Aussagen geprüft · {len(befunde)} Befunde",
        "",
    ]
    if not befunde:
        z += ["Kein Befund. Jede geprüfte Aussage trägt Quelle, Chunk und wörtliches Zitat.", ""]
        return "\n".join(z)

    nach_regel: dict[str, list[dict]] = {}
    for b in befunde:
        nach_regel.setdefault(b["regel"], []).append(b)

    z += ["## Nach Regel", ""]
    for regel in sorted(nach_regel):
        z.append(f"### {regel} — {len(nach_regel[regel])} Befunde")
        z.append("")
        for b in nach_regel[regel]:
            z.append(f"- `{b['kapitel']}` · `{b['claim']}` — {b['text']}")
        z.append("")
    z += [
        "## Nächster Schritt",
        "",
        "Grenzfälle entscheidet der `quellen-pruefer`. Alles mit Q-01 oder Q-04 ist",
        "kein Grenzfall: dort fehlt eine Quelle der Stufe 1, und die Aussage",
        "entfällt oder wird neu belegt (S-06).",
        "",
    ]
    return "\n".join(z)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("kapitel", nargs="*")
    ap.add_argument("--kapitel-text", action="store_true")
    a = ap.parse_args()

    w = g.wurzel()
    cdir = w / "claims"
    if not cdir.is_dir():
        g.fehler("Kein `claims/` Verzeichnis — erst die Skill `recherche` laufen lassen.")
    dateien = (
        [cdir / f"{k}.jsonl" for k in a.kapitel] if a.kapitel else sorted(cdir.glob("*.jsonl"))
    )
    fehlend = [d for d in dateien if not d.exists()]
    if fehlend:
        g.fehler("Nicht gefunden: " + ", ".join(str(d.name) for d in fehlend))

    anzahl = sum(len(g.jsonl_lesen(d)) for d in dateien)
    befunde = claims_pruefen(w, dateien)
    if a.kapitel_text:
        befunde += kapitel_pruefen(w)

    pfad = g.bericht_schreiben(w, "quellen-report.md", bericht(befunde, anzahl))

    nach_regel: dict[str, int] = {}
    for b in befunde:
        nach_regel[b["regel"]] = nach_regel.get(b["regel"], 0) + 1
    g.spur(
        w, "gate",
        werkzeug="claims_pruefen",
        kapitel=a.kapitel or "alle",
        kapiteltext=a.kapitel_text,
        geprueft=anzahl,
        befunde=len(befunde),
        nach_regel=nach_regel,
    )

    print(f"{anzahl} Aussagen geprüft, {len(befunde)} Befunde → {pfad.relative_to(w)}")
    for b in befunde[:15]:
        print(f"  {b['regel']}  {b['kapitel']}  {b['claim']}  {b['text'][:90]}")
    if len(befunde) > 15:
        print(f"  … {len(befunde) - 15} weitere im Bericht")
    raise SystemExit(1 if befunde else 0)


if __name__ == "__main__":
    main()
