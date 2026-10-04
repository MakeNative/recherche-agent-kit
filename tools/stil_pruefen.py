#!/usr/bin/env python3
"""Prüft Kapiteltext gegen die messbaren Regeln des Stilvertrags.

    stil_pruefen.py [datei ...] [--still]

Geprüft wird nur, was mechanisch prüfbar ist (P-04):
  S-01  Satzlänge
  S-02  verbotene Phrasen und Füllwendungen
  S-03  Fachbegriff ohne Glossareintrag
  S-04  Abschnitt ohne Beispiel oder konkrete Handlung
        dazu Absatzlänge aus stil.json

Schwellen kommen aus `stil.json` im Dokumentprojekt. Fehlt die Datei, gelten
die Vorgaben unten. Exit 1 bei Befunden.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gemeinsam as g  # noqa: E402

VORGABE = {
    "satz_max_woerter": 28,
    "absatz_max_saetze": 6,
    "phrasen_verboten": [
        "nicht nur", "sondern auch", "in der heutigen", "es ist wichtig zu",
        "zusammenfassend", "wie bereits erwähnt", "tauchen wir ein",
        "revolutionär", "bahnbrechend", "nahtlos", "mühelos", "eine Vielzahl von",
        "spielt eine wichtige Rolle", "nicht zu unterschätzen", "in diesem Kapitel werden wir",
    ],
    "abschnitt_braucht_beispiel": True,
    "beispiel_marker": ["Beispiel", "Zum Beispiel", "Konkret", "In der Praxis", "Angenommen", "```"],
    "glossar_pflicht": True,
}

SATZ_ENDE = re.compile(r"(?<=[.!?])\s+")
UEBERSCHRIFT = re.compile(r"^(#{1,6})\s+(.+)$")
# Kandidaten für Fachbegriffe: CamelCase, snake_case, Backticks, bekannte Kürzel.
JARGON = re.compile(
    r"`([^`\n]{2,40})`|\b([A-Z][a-z]+[A-Z][A-Za-z]*)\b|\b(\w+_\w+)\b|"
    r"\b(MCP|LLM|API|CLI|SDK|TDD|RAG|IDE|CI|PR|Hook|Subagent|Agent|Token|Prompt|Repo)\b"
)


def einstellungen(w: Path) -> dict:
    pfad = w / "stil.json"
    s = dict(VORGABE)
    if pfad.exists():
        try:
            s.update(json.loads(pfad.read_text(encoding="utf-8")))
        except json.JSONDecodeError as e:
            g.fehler(f"stil.json ist kein gültiges JSON — {e}")
    return s


def glossarbegriffe(w: Path) -> set[str]:
    pfad = w / "wissen" / "GLOSSAR.md"
    if not pfad.exists():
        return set()
    text = pfad.read_text(encoding="utf-8", errors="replace")
    begriffe = set()
    # Fettbegriffe überall erkennen — auch in Tabellenzellen, deren Zeile mit
    # `|` beginnt. Die frühere Variante verlangte Zeilenanfang und übersah
    # dadurch jedes Glossar in Tabellenform.
    for m in re.finditer(r"\*\*(.+?)\*\*", text):
        begriffe.add(m.group(1).strip().lower())
    for m in re.finditer(r"^\s*\|\s*([^|]{2,40}?)\s*\|", text, re.M):
        t = m.group(1).strip().lower()
        if t and not set(t) <= set("-: "):
            begriffe.add(t)
    for m in re.finditer(r"^#{2,6}\s+(.+)$", text, re.M):
        begriffe.add(m.group(1).strip().lower())
    # Aliasse in Klammern mitnehmen: **Subagent** (engl. subagent, Agent)
    # Klammerlisten können lang werden (Sammeleinträge mit vielen Aliassen),
    # und Aliasse dürfen Schrägstriche tragen (.git/, .claude/settings.json) —
    # deshalb Grenze 200 und Trennung nur an Komma/Semikolon.
    for m in re.finditer(r"\(([^)]{2,200})\)", text):
        for teil in re.split(r"[,;]", m.group(1)):
            teil = re.sub(r"^(engl\.|dt\.|auch|früher|veraltet)\s*", "", teil.strip(), flags=re.I)
            if 2 <= len(teil) <= 40:
                begriffe.add(teil.strip().lower())
    return begriffe


def absaetze(zeilen: list[str]) -> list[tuple[int, str, str]]:
    """Liefert (startzeile, abschnitt, absatztext) ohne Code, Tabellen, Zitate."""
    ergebnis = []
    im_zaun = False
    abschnitt = "(ohne Überschrift)"
    puffer: list[str] = []
    start = 1
    for nr, zeile in enumerate(zeilen + [""], 1):
        if zeile.lstrip().startswith(("```", "~~~")):
            im_zaun = not im_zaun
            continue
        if im_zaun:
            continue
        if m := UEBERSCHRIFT.match(zeile):
            if puffer:
                ergebnis.append((start, abschnitt, " ".join(puffer)))
                puffer = []
            abschnitt = m.group(2).strip()
            continue
        if not zeile.strip() or zeile.lstrip().startswith(("|", ">", ":", "<!--")):
            if puffer:
                ergebnis.append((start, abschnitt, " ".join(puffer)))
                puffer = []
            continue
        if not puffer:
            start = nr
        puffer.append(zeile.strip())
    return ergebnis


def abschnitte_mit_text(zeilen: list[str]) -> dict[str, list[str]]:
    gruppen: dict[str, list[str]] = {}
    im_zaun = False
    aktuell = "(ohne Überschrift)"
    for zeile in zeilen:
        if zeile.lstrip().startswith(("```", "~~~")):
            im_zaun = not im_zaun
            gruppen.setdefault(aktuell, []).append(zeile)
            continue
        if not im_zaun and (m := UEBERSCHRIFT.match(zeile)):
            aktuell = m.group(2).strip()
            gruppen.setdefault(aktuell, [])
            continue
        gruppen.setdefault(aktuell, []).append(zeile)
    return gruppen


def pruefen(datei: Path, s: dict, begriffe: set[str]) -> list[dict]:
    zeilen = datei.read_text(encoding="utf-8", errors="replace").splitlines()
    b: list[dict] = []

    def befund(regel, zeile, text):
        b.append({"regel": regel, "ort": f"{datei.name}:{zeile}", "text": text})

    for start, abschnitt, absatz in absaetze(zeilen):
        saetze = [x for x in SATZ_ENDE.split(absatz) if x.strip()]
        if len(saetze) > s["absatz_max_saetze"]:
            befund("S-01", start, f"Absatz mit {len(saetze)} Sätzen in „{abschnitt}\"")
        for satz in saetze:
            woerter = len(re.findall(r"\b[\wäöüÄÖÜß-]+\b", satz))
            if woerter > s["satz_max_woerter"]:
                befund("S-01", start, f"Satz mit {woerter} Wörtern: „{satz[:90]}…\"")
        for phrase in s["phrasen_verboten"]:
            if phrase.lower() in absatz.lower():
                befund("S-02", start, f"Verbotene Wendung „{phrase}\"")

    if s.get("abschnitt_braucht_beispiel"):
        for abschnitt, inhalt in abschnitte_mit_text(zeilen).items():
            text = "\n".join(inhalt)
            if len(g.leerraum_normal(text)) < 200:
                continue
            if not any(m.lower() in text.lower() for m in s["beispiel_marker"]):
                befund("S-04", 1, f"Abschnitt „{abschnitt}\" ohne Beispiel oder Handlung")

    if s.get("glossar_pflicht") and begriffe:
        gemeldet = set()
        for nr, zeile in enumerate(zeilen, 1):
            for m in JARGON.finditer(zeile):
                begriff = next(x for x in m.groups() if x)
                k = begriff.strip().lower()
                if k in begriffe or k in gemeldet or len(k) < 2:
                    continue
                gemeldet.add(k)
                befund("S-03", nr, f"Fachbegriff „{begriff}\" steht nicht im Glossar")
    return b


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dateien", nargs="*")
    ap.add_argument("--still", action="store_true", help="nur Exitcode, keine Ausgabe")
    a = ap.parse_args()

    w = g.wurzel()
    s = einstellungen(w)
    begriffe = glossarbegriffe(w)

    dateien = [Path(d) for d in a.dateien] or sorted((w / "kapitel").glob("*.qmd"))
    dateien = [d for d in dateien if d.exists() and d.suffix in (".qmd", ".md")]
    if not dateien:
        if not a.still:
            print("Keine Kapiteldateien gefunden — nichts zu prüfen.")
        raise SystemExit(0)

    befunde = [x for d in dateien for x in pruefen(d, s, begriffe)]

    z = [
        "<!-- GENERIERT von stil_pruefen.py -->",
        "# Gate: Stil",
        "",
        f"Stand {g.heute()} · {len(dateien)} Dateien · {len(befunde)} Befunde",
        "",
    ]
    if befunde:
        nach_regel: dict[str, list[dict]] = {}
        for x in befunde:
            nach_regel.setdefault(x["regel"], []).append(x)
        for regel in sorted(nach_regel):
            z.append(f"## {regel} — {len(nach_regel[regel])}")
            z.append("")
            z += [f"- `{x['ort']}` — {x['text']}" for x in nach_regel[regel]]
            z.append("")
        z += [
            "Befunde zu S-01 und S-02 behebt der `verdichter` durch Streichen (P-05).",
            "S-03 ist eine Glossarlücke, S-04 ein Fall für den `beispiel-agent`.",
            "",
        ]
    else:
        z += ["Kein Befund.", ""]
    g.bericht_schreiben(w, "stil-report.md", "\n".join(z))

    nach_regel: dict[str, int] = {}
    for x in befunde:
        nach_regel[x["regel"]] = nach_regel.get(x["regel"], 0) + 1
    zeichen = sum(len(d.read_text(encoding="utf-8", errors="replace")) for d in dateien)
    g.spur(
        w, "gate",
        werkzeug="stil_pruefen",
        dateien=[d.name for d in dateien],
        zeichen=zeichen,
        befunde=len(befunde),
        nach_regel=nach_regel,
        ausloeser="hook" if a.still else "lauf",
    )

    if not a.still:
        print(f"{len(dateien)} Dateien, {len(befunde)} Befunde → gates/stil-report.md")
        for x in befunde[:15]:
            print(f"  {x['regel']}  {x['ort']}  {x['text'][:90]}")
        if len(befunde) > 15:
            print(f"  … {len(befunde) - 15} weitere im Bericht")
    raise SystemExit(1 if befunde else 0)


if __name__ == "__main__":
    main()
