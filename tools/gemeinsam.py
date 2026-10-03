"""Gemeinsame Helfer für die recherche-kit Werkzeuge.

Nur Standardbibliothek. Kein pip install, keine zweite Datenhaltung (K-04).
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

STATUS_QUELLE = ("aktuell", "ueberholt", "widersprochen", "unklar")
STATUS_CLAIM = ("belegt", "offen", "widersprochen", "pruefen")
TYP_CLAIM = ("funktion", "erfahrung", "urteil", "zahl")

# Aussagetypen, die nach Q-01 eine Quelle der Stufe 1 verlangen.
TYP_BRAUCHT_TIER1 = ("funktion", "zahl")


def heute() -> str:
    return date.today().isoformat()


def wurzel(start: Path | None = None) -> Path:
    """Findet die Wurzel des Dokumentprojekts: der Ordner, der `wissen/` enthält."""
    p = (start or Path.cwd()).resolve()
    for kandidat in (p, *p.parents):
        if (kandidat / "wissen").is_dir():
            return kandidat
    fehler(
        "Kein Dokumentprojekt gefunden. Erwartet wird ein Ordner mit `wissen/` "
        "oberhalb des Arbeitsverzeichnisses. Lege ihn mit der Skill `adopt` an."
    )


def fehler(text: str, code: int = 2):
    print(f"FEHLER: {text}", file=sys.stderr)
    raise SystemExit(code)


def warnung(text: str):
    print(f"WARNUNG: {text}", file=sys.stderr)


def jsonl_lesen(pfad: Path) -> list[dict]:
    if not pfad.exists():
        return []
    zeilen = []
    for nr, roh in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1):
        roh = roh.strip()
        if not roh or roh.startswith("#"):
            continue
        try:
            zeilen.append(json.loads(roh))
        except json.JSONDecodeError as e:
            fehler(f"{pfad}:{nr} ist kein gültiges JSON — {e}")
    return zeilen


def jsonl_schreiben(pfad: Path, saetze: list[dict]):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("w", encoding="utf-8") as f:
        for s in saetze:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")


def jsonl_anhaengen(pfad: Path, satz: dict):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("a", encoding="utf-8") as f:
        f.write(json.dumps(satz, ensure_ascii=False) + "\n")


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.replace("ß", "ss")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "ohne-titel"


def token_schaetzung(text: str) -> int:
    """Grobe Schätzung. Vier Zeichen je Token reicht für die Grenze aus K-02."""
    return len(text) // 4


def leerraum_normal(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def quellen(w: Path) -> list[dict]:
    return jsonl_lesen(w / "wissen" / "sources.jsonl")


def quellen_index(w: Path) -> dict[str, dict]:
    return {q["id"]: q for q in quellen(w)}


def quellen_schreiben(w: Path, saetze: list[dict]):
    saetze.sort(key=lambda q: (str(q.get("tier", 9)), q.get("id", "")))
    jsonl_schreiben(w / "wissen" / "sources.jsonl", saetze)


def quellordner(w: Path, q: dict) -> Path:
    return w / "wissen" / "quellen" / q["kategorie"] / q["slug"]


def naechste_id(vorhandene: list[dict], tier: int) -> str:
    """IDs sind kurz und sprechend: A-07 für Stufe 1, B-03 für Stufe 2, usw."""
    buchstabe = "ABCDE"[max(1, min(5, int(tier))) - 1]
    benutzt = {
        int(m.group(1))
        for q in vorhandene
        if (m := re.fullmatch(rf"{buchstabe}-(\d+)", str(q.get("id", ""))))
    }
    n = 1
    while n in benutzt:
        n += 1
    return f"{buchstabe}-{n:02d}"


def chunks_lesen(w: Path, q: dict) -> list[dict]:
    return jsonl_lesen(quellordner(w, q) / "chunks.jsonl")


def chunk_text(w: Path, q: dict, chunk: dict) -> str:
    datei = quellordner(w, q) / "raw.md"
    if not datei.exists():
        return ""
    zeilen = datei.read_text(encoding="utf-8", errors="replace").splitlines()
    von, bis = chunk["zeilen"]
    return "\n".join(zeilen[von - 1 : bis])


def bericht_schreiben(w: Path, name: str, inhalt: str) -> Path:
    pfad = w / "gates" / name
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(inhalt, encoding="utf-8")
    return pfad


SPUR = Path(".claude") / "recherche-log" / "lauf.jsonl"


def spur(w: Path, ereignis: str, **felder):
    """Schreibt eine Zeile in das Laufprotokoll.

    Das Protokoll ist die Datengrundlage für `evaluieren`. Ohne es beruht die
    Bewertung der Pipeline auf Erinnerung, und Erinnerung ist gnädig.

    Darf nie den Aufrufer stören: ein fehlgeschlagener Protokolleintrag ist
    kein Grund, einen Lauf abzubrechen.
    """
    from datetime import datetime

    try:
        pfad = w / SPUR
        pfad.parent.mkdir(parents=True, exist_ok=True)
        satz = {
            "zeit": datetime.now().isoformat(timespec="seconds"),
            "ereignis": ereignis,
            **felder,
        }
        with pfad.open("a", encoding="utf-8") as f:
            f.write(json.dumps(satz, ensure_ascii=False) + "\n")
    except Exception:
        pass


def spur_lesen(w: Path, ereignis: str | None = None) -> list[dict]:
    saetze = jsonl_lesen(w / SPUR)
    return [s for s in saetze if ereignis is None or s.get("ereignis") == ereignis]
