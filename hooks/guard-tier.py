#!/usr/bin/env python3
"""PreToolUse: verhindert, dass eine Funktionsaussage auf einer Drittquelle steht.

Das ist Q-01 als Mechanik. Eine Regel im Prompt erodiert über einen langen Lauf;
ein Hook nicht.

Blockiert (Exit 2):
  * Aussage mit typ `funktion` oder `zahl`, deren Quelle nicht Stufe 1 ist
  * Aussage, deren Quelle `ueberholt` oder `widersprochen` ist (Q-04)
  * Aussage, deren Quelle gar nicht in sources.jsonl steht

Warnt (Exit 0 mit Hinweis):
  * Kapiteltext mit Fußnote auf eine Aussage, die nicht `belegt` ist

Bei allem Unerwarteten wird durchgelassen. Ein Hook, der Arbeit blockiert, weil
er selbst einen Fehler hat, wird abgeschaltet — und dann schützt er nichts mehr.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

TIER1_PFLICHT = ("funktion", "zahl")
TOT = ("ueberholt", "widersprochen")
# Q-01-Verdacht: funktionsförmige Aussage (Backticks, Pfad, Dateiname, Flag)
# aus Stufe 2–5, als `urteil`/`erfahrung` etikettiert. Das typ-Feld setzt
# dieselbe Instanz, die schreibt — darum prüft der Hook die Form der Aussage,
# nicht nur das Etikett. Entschärfen: `q01_ok: true` + `q01_grund`.
Q01_VERDACHT = re.compile(
    r"`[^`\n]+`"
    r"|(?<![\w.])\.?\w[\w.-]*/[\w./-]+"
    r"|\b[\w-]+\.(?:md|mdc|json|toml|yaml|yml|txt|py|qmd)\b"
    r"|(?<!\w)--\w"
)


def spur(w: Path, **felder):
    """Jede Blockade wird protokolliert. Ein Hook, der still blockt, ist nicht
    auswertbar — und `evaluieren` muss sehen können, ob die Regel greift oder
    nur im Weg steht."""
    try:
        pfad = w / ".claude" / "recherche-log" / "lauf.jsonl"
        pfad.parent.mkdir(parents=True, exist_ok=True)
        with pfad.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {"zeit": datetime.now().isoformat(timespec="seconds"), **felder},
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:
        pass


def wurzel(start: Path) -> Path | None:
    for k in (start, *start.parents):
        if (k / "wissen" / "sources.jsonl").exists():
            return k
    return None


def quellen(w: Path) -> dict[str, dict]:
    idx = {}
    for zeile in (w / "wissen" / "sources.jsonl").read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#"):
            continue
        try:
            q = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        if q.get("id"):
            idx[q["id"]] = q
    return idx


def neuer_text(eingabe: dict) -> str:
    for feld in ("content", "new_string"):
        if isinstance(eingabe.get(feld), str):
            return eingabe[feld]
    bearbeitungen = eingabe.get("edits")
    if isinstance(bearbeitungen, list):
        return "\n".join(
            b.get("new_string", "") for b in bearbeitungen if isinstance(b, dict)
        )
    return ""


def claims_pruefen(text: str, qidx: dict[str, dict]) -> list[str]:
    verstoesse = []
    for nr, zeile in enumerate(text.splitlines(), 1):
        zeile = zeile.strip()
        if not zeile.startswith("{"):
            continue
        try:
            c = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        if c.get("status") == "offen":
            continue
        qid = c.get("quelle")
        if not qid:
            continue
        cid = c.get("claim_id", f"Zeile {nr}")
        q = qidx.get(qid)
        if q is None:
            verstoesse.append(
                f"{cid}: Quelle `{qid}` steht nicht in sources.jsonl. "
                f"Erst über /recherche-kit:quelle-aufnehmen aufnehmen (Q-02)."
            )
            continue
        if q.get("status") in TOT:
            verstoesse.append(
                f"{cid}: Quelle {qid} ist `{q['status']}` und darf nichts belegen (Q-04). "
                f"Neu belegen oder Aussage streichen."
            )
        if c.get("typ") in TIER1_PFLICHT and int(q.get("tier", 9)) != 1:
            verstoesse.append(
                f"{cid}: typ `{c['typ']}` verlangt eine Quelle der Stufe 1, "
                f"{qid} ist Stufe {q.get('tier')} (Q-01). "
                f"Entweder einen Stufe-1-Beleg suchen oder `status` auf `offen` setzen."
            )
        elif (
            int(q.get("tier", 9)) != 1
            and not c.get("q01_ok")
            and isinstance(c.get("aussage"), str)
            and Q01_VERDACHT.search(c["aussage"])
        ):
            verstoesse.append(
                f"{cid}: funktionsförmige Aussage aus Stufe {q.get('tier')}, deklariert als "
                f"`{c.get('typ')}` (Q-01-Verdacht). Stufe-1-Beleg suchen, oder nach Prüfung "
                f"`q01_ok: true` mit `q01_grund` setzen."
            )
    return verstoesse


def kapitel_warnen(w: Path, text: str) -> list[str]:
    status: dict[str, str] = {}
    cdir = w / "claims"
    if not cdir.is_dir():
        return []
    for datei in cdir.glob("*.jsonl"):
        for zeile in datei.read_text(encoding="utf-8", errors="replace").splitlines():
            zeile = zeile.strip()
            if not zeile.startswith("{"):
                continue
            try:
                c = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            if c.get("claim_id"):
                status[c["claim_id"]] = c.get("status", "?")

    hinweise = []
    for ref in sorted({m.group(1) for m in re.finditer(r"\[\^([A-Za-z0-9][\w-]*)\]", text)}):
        if re.search(rf"\[\^{re.escape(ref)}\]:", text):
            pass  # hat eine Definition, trotzdem Status prüfen
        s = status.get(ref)
        if s is None:
            hinweise.append(f"Fußnote `{ref}` zeigt auf keine bekannte Aussage.")
        elif s != "belegt":
            hinweise.append(f"Fußnote `{ref}` zeigt auf eine Aussage mit status `{s}`.")
    return hinweise


def main():
    try:
        daten = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if daten.get("tool_name") not in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        sys.exit(0)

    eingabe = daten.get("tool_input") or {}
    pfad_roh = eingabe.get("file_path") or eingabe.get("notebook_path") or ""
    if not pfad_roh:
        sys.exit(0)

    pfad = Path(pfad_roh)
    w = wurzel(Path(daten.get("cwd") or ".").resolve()) or wurzel(
        pfad.resolve().parent if pfad.is_absolute() else Path.cwd()
    )
    if w is None:
        sys.exit(0)

    text = neuer_text(eingabe)
    if not text:
        sys.exit(0)

    teile = pfad.as_posix()

    if "/claims/" in teile or teile.startswith("claims/"):
        try:
            verstoesse = claims_pruefen(text, quellen(w))
        except Exception:
            sys.exit(0)
        if verstoesse:
            regeln = sorted({m.group(0) for v in verstoesse if (m := re.search(r"Q-\d\d", v))})
            spur(
                w,
                ereignis="blockade",
                hook="guard-tier",
                datei=pfad.name,
                anzahl=len(verstoesse),
                regeln=regeln,
                beispiel=verstoesse[0][:200],
            )
            print(
                "Blockiert nach Regelwerk Q-01/Q-02/Q-04 — "
                f"{len(verstoesse)} Aussage(n) dürfen so nicht geschrieben werden:\n"
                + "\n".join(f"  - {v}" for v in verstoesse),
                file=sys.stderr,
            )
            sys.exit(2)

    elif teile.endswith((".qmd", ".md")) and ("/kapitel/" in teile or teile.startswith("kapitel/")):
        try:
            hinweise = kapitel_warnen(w, text)
        except Exception:
            sys.exit(0)
        if hinweise:
            spur(
                w,
                ereignis="hinweis",
                hook="guard-tier",
                datei=pfad.name,
                anzahl=len(hinweise),
                beispiel=hinweise[0][:200],
            )
            print(
                "Hinweis zu den Belegen in diesem Kapitel (nicht blockiert):\n"
                + "\n".join(f"  - {h}" for h in hinweise[:10]),
                file=sys.stderr,
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
