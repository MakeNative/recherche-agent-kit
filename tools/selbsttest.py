#!/usr/bin/env python3
"""Fährt die ganze Strecke an einer Mini-Quelle, in einem Wegwerf-Projekt.

    selbsttest.py [--offline] [--behalten]

Geprüft wird nicht nur, dass die Skripte durchlaufen, sondern auch dass sie
**ablehnen, was sie ablehnen sollen**: ein erfundenes Zitat, eine
Funktionsaussage aus einer Drittquelle, eine Zahl ohne Fußnote.

Exit 0 nur, wenn jede Erwartung erfüllt ist.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WERKZEUGE = Path(__file__).parent

FIXTURE = """# Mini-Doku

Eine Beispielseite für den Selbsttest.

## Imports

Imported files can recursively import other files, with a maximum depth of
four hops. Relative paths resolve against the importing file.

## Exit codes

A hook that exits with code 2 blocks the tool call.
"""

ERGEBNIS: list[tuple[bool, str]] = []


def pruefe(bedingung: bool, text: str):
    ERGEBNIS.append((bool(bedingung), text))
    print(("  ok    " if bedingung else "  FEHLT ") + text)


def lauf(skript: str, *args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(WERKZEUGE / skript), *args],
        cwd=cwd, capture_output=True, text=True, timeout=600,
    )


def projekt_anlegen(basis: Path) -> Path:
    w = basis / "testprojekt"
    for d in ("wissen/quellen/1-offiziell-anthropic/docs-code",
              "wissen/quellen/2-praxis-repos", "claims", "kapitel", "gates"):
        (w / d).mkdir(parents=True, exist_ok=True)
    (w / "wissen" / "GLOSSAR.md").write_text(
        "# Glossar\n\n- **Hook** (engl. hook) — ein Skript, das Claude Code an "
        "einem festen Punkt aufruft.\n- **Token** — Texteinheit der Abrechnung.\n"
        "- **Import** — das Nachladen einer Datei.\n",
        encoding="utf-8",
    )
    (w / "stil.json").write_text(
        json.dumps({"satz_max_woerter": 20, "phrasen_verboten": ["nicht nur", "bahnbrechend"]},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return w


def quelle_offline(w: Path) -> str:
    ordner = w / "wissen" / "quellen" / "1-offiziell-anthropic" / "docs-code" / "mini-doku"
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "raw.md").write_text(FIXTURE, encoding="utf-8")
    import hashlib

    satz = {
        "id": "A-01", "slug": "mini-doku", "titel": "Mini-Doku",
        "url": "https://example.invalid/mini", "url_angefragt": None, "tier": 1,
        "kategorie": "1-offiziell-anthropic/docs-code", "veroeffentlicht": None,
        "abgerufen": "2026-10-03", "status": "aktuell", "abgleich_am": None,
        "haken": "Imports, Importtiefe, Exit-Codes", "themen": ["kontext"],
        "lizenz": None, "sha256": hashlib.sha256(FIXTURE.encode()).hexdigest(),
        "zeichen": len(FIXTURE), "chunks": 0, "dateien": None,
        "inhaltstyp": "text/markdown (fixture)", "auffaelligkeiten": [],
    }
    (w / "wissen" / "sources.jsonl").write_text(
        json.dumps(satz, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (ordner / "meta.json").write_text(json.dumps(satz, ensure_ascii=False, indent=2), encoding="utf-8")
    return "A-01"


# Agenten, die Fremdmaterial lesen und deshalb nach P-03 nicht schreiben dürfen.
OHNE_SCHREIBRECHT = (
    "kartenschreiber", "frische-pruefer", "claim-sammler", "quellen-pruefer",
    "laien-leser", "luecken-finder", "beispiel-agent",
    "perspektive-entwickler", "perspektive-laie", "perspektive-entscheider",
)


def definitionen_pruefen():
    """Statische Prüfung der Agenten- und Skill-Dateien im Plugin-Repo.

    Prüft, was ohne installiertes Plugin prüfbar ist: Frontmatter-Felder und
    vor allem die Werkzeugrechte. Eine Rechtebeschränkung, die nur im
    Prompttext steht und nicht im Frontmatter, hält nicht.
    """
    import re as _re

    wurzel = WERKZEUGE.parent
    agenten = sorted((wurzel / "agents").glob("*.md"))
    skills = sorted((wurzel / "skills").glob("*/SKILL.md"))

    pruefe(len(agenten) == 13, f"13 Agentendateien vorhanden ({len(agenten)})")
    pruefe(len(skills) == 12, f"12 Skilldateien vorhanden ({len(skills)})")

    # laien-leser darf kein Memory haben: ein Laie, der lernt, misst nicht mehr.
    lt = (wurzel / "agents" / "laien-leser.md").read_text(encoding="utf-8")
    lfm = _re.match(r"^---\n(.*?)\n---\n", lt, _re.S).group(1)
    pruefe(
        not _re.search(r"^memory:", lfm, _re.M),
        "laien-leser: kein memory im Frontmatter",
    )

    namen = set()
    for p in agenten:
        t = p.read_text(encoding="utf-8")
        m = _re.match(r"^---\n(.*?)\n---\n", t, _re.S)
        if not m:
            pruefe(False, f"{p.name}: Frontmatter fehlt")
            continue
        fm = m.group(1)
        name = (n.group(1).strip() if (n := _re.search(r"^name:\s*(\S+)", fm, _re.M)) else "")
        namen.add(name)
        pruefe(bool(name), f"{p.name}: name gesetzt")
        pruefe(
            bool(_re.search(r"^description:\s*\"?\S", fm, _re.M)),
            f"{p.name}: description gesetzt",
        )
        pruefe(name == p.stem, f"{p.name}: name entspricht dem Dateinamen")

        if name in OHNE_SCHREIBRECHT:
            verboten = (
                _re.search(r"^disallowedTools:\s*(.+)$", fm, _re.M).group(1)
                if _re.search(r"^disallowedTools:\s*(.+)$", fm, _re.M)
                else ""
            )
            erlaubt = (
                _re.search(r"^tools:\s*(.+)$", fm, _re.M).group(1)
                if _re.search(r"^tools:\s*(.+)$", fm, _re.M)
                else ""
            )
            for werkzeug in ("Write", "Edit"):
                in_verboten = _re.search(rf"\b{werkzeug}\b", verboten)
                nicht_erlaubt = not _re.search(rf"\b{werkzeug}\b", erlaubt)
                pruefe(
                    bool(in_verboten) and nicht_erlaubt,
                    f"{name}: {werkzeug} im Frontmatter gesperrt (P-03)",
                )

    fehlend = set(OHNE_SCHREIBRECHT) - namen
    pruefe(not fehlend, f"alle schreibrechtlosen Agenten vorhanden ({sorted(fehlend)})")

    # Der verdichter braucht Edit, darf aber kein Write haben (P-05):
    # ohne Write kann er keine Datei anlegen oder ganz ersetzen.
    vt = (wurzel / "agents" / "verdichter.md").read_text(encoding="utf-8")
    vfm = _re.match(r"^---\n(.*?)\n---\n", vt, _re.S).group(1)
    pruefe(
        bool(_re.search(r"^tools:.*\bEdit\b", vfm, _re.M)),
        "verdichter: Edit erlaubt",
    )
    pruefe(
        bool(_re.search(r"^disallowedTools:.*\bWrite\b", vfm, _re.M)),
        "verdichter: Write gesperrt (P-05)",
    )

    for p in skills:
        t = p.read_text(encoding="utf-8")
        m = _re.match(r"^---\n(.*?)\n---\n", t, _re.S)
        if not m:
            pruefe(False, f"skills/{p.parent.name}: Frontmatter fehlt")
            continue
        fm = m.group(1)
        pruefe(
            "Triggers on:" in fm,
            f"skills/{p.parent.name}: description nennt 'Triggers on:'",
        )
        pruefe(
            bool(_re.search(r"^disable-model-invocation:\s*true", fm, _re.M)),
            f"skills/{p.parent.name}: disable-model-invocation gesetzt",
        )

    # Skills, die Agenten parallel fächern, müssen den Ausfall behandeln (P-07).
    # Ein toter Agent, der als „nichts gefunden" durchgeht, ist der stillste
    # denkbare Fehler.
    for name in ("quelle-aufnehmen", "frische", "fragen", "recherche", "kapitel", "gates"):
        t = (wurzel / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        pruefe("P-07" in t, f"skills/{name}: behandelt den Ausfall eines Agenten (P-07)")

    # Agenten, die zitieren, müssen auf Q-08 verpflichtet sein: ein Zitat ohne
    # Chunk-ID ist unprüfbar, und unprüfbare Zitate werden erfunden.
    for name in ("kartenschreiber", "frische-pruefer", "claim-sammler"):
        t = (wurzel / "agents" / f"{name}.md").read_text(encoding="utf-8")
        pruefe("Q-08" in t, f"{name}: verlangt Chunk-ID für jedes Zitat (Q-08)")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true", help="ohne Netz, mit eingebauter Quelle")
    ap.add_argument("--behalten", action="store_true", help="Testprojekt nicht löschen")
    ap.add_argument("--nur-definitionen", action="store_true", help="nur agents/ und skills/ prüfen")
    a = ap.parse_args()

    if a.nur_definitionen:
        print("Definitionen\n")
        definitionen_pruefen()
        ok = sum(1 for b, _ in ERGEBNIS if b)
        print(f"\n{ok} von {len(ERGEBNIS)} Erwartungen erfüllt")
        for t in (t for b, t in ERGEBNIS if not b):
            print(f"  - {t}")
        raise SystemExit(0 if all(b for b, _ in ERGEBNIS) else 1)

    basis = Path(tempfile.mkdtemp(prefix="recherche-kit-selbsttest-"))
    w = projekt_anlegen(basis)
    print(f"Testprojekt: {w}\n")

    try:
        print("0. Definitionen von Agenten und Skills")
        definitionen_pruefen()

        print("\n1. Quelle aufnehmen")
        if a.offline:
            qid = quelle_offline(w)
            pruefe(True, "Quelle aus Fixture angelegt (offline)")
        else:
            r = lauf("quelle_holen.py", "https://code.claude.com/docs/en/memory",
                     "--tier", "1", "--kategorie", "1-offiziell-anthropic/docs-code",
                     "--titel", "Claude Code — Memory", "--haken", "CLAUDE.md, Imports",
                     "--themen", "kontext", cwd=w)
            pruefe(r.returncode == 0, f"quelle_holen.py läuft durch ({r.returncode})")
            if r.returncode != 0:
                print("    " + (r.stderr or "").strip()[:400])
                qid = quelle_offline(w)
                pruefe(True, "auf Fixture ausgewichen, Netz nicht verfügbar")
            else:
                qid = json.loads(
                    (w / "wissen" / "sources.jsonl").read_text().splitlines()[0]
                )["id"]

        print("\n2. Chunken")
        r = lauf("chunken.py", qid, cwd=w)
        pruefe(r.returncode == 0, "chunken.py läuft durch")
        quelle = json.loads((w / "wissen" / "sources.jsonl").read_text().splitlines()[0])
        chunks_datei = (w / "wissen" / "quellen" / quelle["kategorie"] / quelle["slug"]
                        / "chunks.jsonl")
        chunks = [json.loads(z) for z in chunks_datei.read_text().splitlines() if z.strip()]
        pruefe(len(chunks) >= 2, f"mindestens zwei Abschnitte erkannt ({len(chunks)})")
        pruefe(all(c["chunk_id"].startswith(qid + "#") for c in chunks),
               "Chunk-IDs tragen die Quellen-ID (K-05)")

        print("\n3. Index bauen")
        (w / "wissen" / "quellen" / quelle["kategorie"] / quelle["slug"] / "CARD.md").write_text(
            "# Mini  ·  Stufe 1\n\n**Worum es geht:** Testkarte.\n", encoding="utf-8"
        )
        r = lauf("index_bauen.py", cwd=w)
        pruefe(r.returncode == 0, "index_bauen.py läuft durch")
        pruefe((w / "wissen" / "INDEX.md").exists(), "INDEX.md geschrieben")
        pruefe((w / "wissen" / "THEMEN.md").exists(), "THEMEN.md geschrieben")

        print("\n4. Indexgrenze greift (K-02)")
        r = lauf("index_bauen.py", "--grenze", "1", cwd=w)
        pruefe(r.returncode != 0, "zu großer Index wird abgelehnt")

        print("\n5. Gute Aussage wird akzeptiert")
        # Zitat wörtlich aus dem größten Abschnitt entnehmen.
        roh = (w / "wissen" / "quellen" / quelle["kategorie"] / quelle["slug"]
               / "raw.md").read_text(encoding="utf-8").splitlines()
        ziel = max(chunks, key=lambda c: c.get("zeichen", 0))
        text = " ".join(roh[ziel["zeilen"][0] - 1 : ziel["zeilen"][1]]).split()
        zitat = " ".join(text[2:9]) if len(text) > 9 else " ".join(text)
        gut = {
            "claim_id": "T01-001", "aussage": "Eine belegte Testaussage.",
            "typ": "funktion", "quelle": qid, "chunk_id": ziel["chunk_id"],
            "zitat": zitat, "status": "belegt", "stand": "2026-10-03",
        }
        claims = w / "claims" / "test.jsonl"
        claims.write_text(json.dumps(gut, ensure_ascii=False) + "\n", encoding="utf-8")
        r = lauf("claims_pruefen.py", "test", cwd=w)
        pruefe(r.returncode == 0, "wörtliches Zitat aus Stufe 1 wird akzeptiert")
        if r.returncode != 0:
            print("    " + r.stdout.strip()[:400])

        print("\n6. Erfundenes Zitat wird abgelehnt (Q-03)")
        schlecht = dict(gut, claim_id="T01-002", zitat="dieser Satz steht dort nicht")
        claims.write_text(
            "\n".join(json.dumps(x, ensure_ascii=False) for x in (gut, schlecht)) + "\n",
            encoding="utf-8",
        )
        r = lauf("claims_pruefen.py", "test", cwd=w)
        pruefe(r.returncode == 1, "nicht wörtliches Zitat wird gemeldet")
        pruefe("Q-03" in (w / "gates" / "quellen-report.md").read_text(),
               "Befund trägt die Regel-ID Q-03")

        print("\n7. Funktionsaussage aus Drittquelle wird abgelehnt (Q-01)")
        zweite = dict(quelle, id="B-01", slug="dritt", tier=2,
                      kategorie="2-praxis-repos", titel="Drittquelle")
        ordner2 = w / "wissen" / "quellen" / "2-praxis-repos" / "dritt"
        ordner2.mkdir(parents=True, exist_ok=True)
        (ordner2 / "raw.md").write_text("# Dritt\n\nfour hops laut Blogpost.\n", encoding="utf-8")
        (w / "wissen" / "sources.jsonl").write_text(
            json.dumps(quelle, ensure_ascii=False) + "\n"
            + json.dumps(zweite, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        lauf("chunken.py", "B-01", cwd=w)
        c2 = [json.loads(z) for z in (ordner2 / "chunks.jsonl").read_text().splitlines() if z.strip()]
        dritt = {
            "claim_id": "T01-003", "aussage": "Funktionsaussage aus Stufe 2.",
            "typ": "funktion", "quelle": "B-01", "chunk_id": c2[0]["chunk_id"],
            "zitat": "four hops laut Blogpost", "status": "belegt", "stand": "2026-10-03",
        }
        claims.write_text(json.dumps(dritt, ensure_ascii=False) + "\n", encoding="utf-8")
        r = lauf("claims_pruefen.py", "test", cwd=w)
        pruefe(r.returncode == 1, "Stufe 2 trägt keine Funktionsaussage")
        pruefe("Q-01" in (w / "gates" / "quellen-report.md").read_text(),
               "Befund trägt die Regel-ID Q-01")

        print("\n8. Überholte Quelle belegt nicht (Q-04)")
        zweite_alt = dict(zweite, status="ueberholt")
        (w / "wissen" / "sources.jsonl").write_text(
            json.dumps(quelle, ensure_ascii=False) + "\n"
            + json.dumps(zweite_alt, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        claims.write_text(
            json.dumps(dict(dritt, typ="erfahrung"), ensure_ascii=False) + "\n", encoding="utf-8"
        )
        r = lauf("claims_pruefen.py", "test", cwd=w)
        pruefe("Q-04" in (w / "gates" / "quellen-report.md").read_text(),
               "überholte Quelle wird gemeldet")

        print("\n9. Kapiteltext: Zahl ohne Fußnote (Q-02)")
        claims.write_text(json.dumps(gut, ensure_ascii=False) + "\n", encoding="utf-8")
        (w / "kapitel" / "01-test.qmd").write_text(
            "# Test\n\nDas Fenster fasst 1000000 Token.\n\n"
            "Eine belegte Aussage steht hier.[^T01-001]\n\n"
            "[^T01-001]: Quelle A-01\n",
            encoding="utf-8",
        )
        r = lauf("claims_pruefen.py", "test", "--kapitel-text", cwd=w)
        bericht = (w / "gates" / "quellen-report.md").read_text()
        pruefe("Zahl ohne Fußnote" in bericht, "Zahl ohne Fußnote wird gemeldet")

        print("\n10. Stilgate")
        (w / "kapitel" / "02-stil.qmd").write_text(
            "# Stil\n\nDieser Satz ist nicht nur absichtlich sehr lang gebaut, "
            "sondern enthält darüber hinaus eine verbotene Wendung und noch "
            "viele weitere Wörter, damit die Schwelle sicher überschritten wird "
            "und das Gate etwas zu melden hat.\n",
            encoding="utf-8",
        )
        r = lauf("stil_pruefen.py", str(w / "kapitel" / "02-stil.qmd"), cwd=w)
        pruefe(r.returncode == 1, "stil_pruefen.py meldet Befunde")
        sbericht = (w / "gates" / "stil-report.md").read_text()
        pruefe("S-01" in sbericht, "Satzlänge wird gemeldet (S-01)")
        pruefe("S-02" in sbericht, "verbotene Wendung wird gemeldet (S-02)")

        print("\n11. Saubere Datei besteht das Stilgate")
        (w / "kapitel" / "03-sauber.qmd").write_text(
            "# Sauber\n\nDer Hook blockiert den Aufruf. Beispiel: Exit-Code 2 "
            "bricht ab.\n", encoding="utf-8"
        )
        r = lauf("stil_pruefen.py", str(w / "kapitel" / "03-sauber.qmd"), cwd=w)
        pruefe(r.returncode == 0, "sauberer Text erzeugt keinen Befund")
        if r.returncode != 0:
            print("    " + r.stdout.strip()[:400])

        print("\n12. Laufprotokoll")
        spur = w / ".claude" / "recherche-log" / "lauf.jsonl"
        pruefe(spur.exists(), "Protokoll wurde angelegt")
        if spur.exists():
            saetze = [
                json.loads(z) for z in spur.read_text(encoding="utf-8").splitlines() if z.strip()
            ]
            arten = {s.get("ereignis") for s in saetze}
            pruefe(len(saetze) >= 5, f"mindestens fünf Einträge ({len(saetze)})")
            pruefe("gate" in arten, "Gate-Läufe sind protokolliert")
            pruefe(
                all("zeit" in s and "ereignis" in s for s in saetze),
                "jeder Eintrag hat Zeit und Ereignis",
            )
            mit_regeln = [s for s in saetze if s.get("nach_regel")]
            pruefe(
                bool(mit_regeln),
                "mindestens ein Eintrag nennt die verletzten Regeln",
            )

    finally:
        print("\n" + "─" * 60)
        ok = sum(1 for b, _ in ERGEBNIS if b)
        print(f"{ok} von {len(ERGEBNIS)} Erwartungen erfüllt")
        gefehlt = [t for b, t in ERGEBNIS if not b]
        if gefehlt:
            print("\nNicht erfüllt:")
            for t in gefehlt:
                print(f"  - {t}")
        if a.behalten:
            print(f"\nTestprojekt bleibt liegen: {w}")
        else:
            shutil.rmtree(basis, ignore_errors=True)

    raise SystemExit(0 if all(b for b, _ in ERGEBNIS) else 1)


if __name__ == "__main__":
    main()
