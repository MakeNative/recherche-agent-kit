#!/usr/bin/env python3
"""Holt eine Quelle in die Bibliothek: Rohtext, meta.json, Auffälligkeiten.

Chunking macht `chunken.py`, die Karte schreibt der `kartenschreiber`.
Dieses Skript urteilt nicht — es beschafft (P-04).

    quelle_holen.py <url|github-repo> --tier 1 --kategorie 1-offiziell-anthropic/docs-code
                    [--titel T] [--haken H] [--themen a,b] [--lizenz L] [--slug S]
                    [--id A-07] [--neu-holen]

Besonderheiten:
  * Mintlify-Doku (platform.claude.com, code.claude.com) liefert zu jeder Seite
    eine Markdown-Fassung unter <url>.md. Die wird bevorzugt, weil sie stabiler
    ist als HTML-Abschälen.
  * github.com/<owner>/<repo> wird flach geklont und alle Markdown-Dateien
    werden zu einer Quelle zusammengefasst.
  * Umleitungen werden aufgelöst und das Ziel wird zitiert (Q-07).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gemeinsam as g  # noqa: E402

KOPF = {"User-Agent": "recherche-kit/0.1 (+lokale Dokumentrecherche)"}
ZEITLIMIT = 60

# Muster nach Q-06: Text, der wie eine Anweisung an ein Modell aussieht.
# Absichtlich eng gefasst. Fachdoku redet dauernd über System-Prompts und
# Agenten — ein Muster, das darauf anspringt, erzeugt nur Rauschen und macht
# das Signal wertlos.
INJEKTION = [
    re.compile(p, re.I)
    for p in (
        r"ignor(e|ing|iere)\s+(all\s+|alle\s+)?(the\s+|die\s+)?(previous|prior|above|vorherige|obige)"
        r"[^.\n]{0,20}(instruction|anweisung|prompt|regel)",
        r"disregard\s+(all\s+)?(the\s+)?(previous|prior|above)",
        r"vergiss\s+(alle\s+)?(vorherigen|obigen)\s+(anweisungen|regeln)",
        r"you\s+are\s+now\s+(an?|the)\s+\w+",
        r"du\s+bist\s+(ab\s+jetzt|jetzt)\s+(ein|eine|der|die)\b",
        r"<\s*/\s*(system|instructions)\s*>",
        r"\[\s*(end|ende)\s+of\s+(instructions|prompt)\s*\]",
        r"(new|neue)\s+(instructions|anweisungen)\s*:",
    )
]


class NurText(HTMLParser):
    """Sehr einfacher HTML-nach-Text-Wandler. Überschriften bleiben Markdown."""

    SPRINGEN = {"script", "style", "nav", "footer", "header", "svg", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.teile: list[str] = []
        self.tiefe_springen = 0
        self.ueberschrift = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SPRINGEN:
            self.tiefe_springen += 1
        elif m := re.fullmatch(r"h([1-6])", tag):
            self.ueberschrift = int(m.group(1))
            self.teile.append("\n\n" + "#" * self.ueberschrift + " ")
        elif tag in ("p", "div", "section", "article", "li", "tr", "pre", "blockquote"):
            self.teile.append("\n\n")
        elif tag == "br":
            self.teile.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SPRINGEN and self.tiefe_springen:
            self.tiefe_springen -= 1
        elif re.fullmatch(r"h[1-6]", tag):
            self.ueberschrift = 0
            self.teile.append("\n")

    def handle_data(self, daten):
        if self.tiefe_springen:
            return
        if self.ueberschrift:
            self.teile.append(re.sub(r"\s+", " ", daten))
        else:
            self.teile.append(daten)

    def text(self) -> str:
        roh = "".join(self.teile)
        roh = re.sub(r"[ \t]+", " ", roh)
        roh = re.sub(r"\n{3,}", "\n\n", roh)
        return "\n".join(z.rstrip() for z in roh.splitlines()).strip()


def holen(url: str) -> tuple[str, str, str]:
    """Liefert (text, endgueltige_url, inhaltstyp)."""
    anfrage = urllib.request.Request(url, headers=KOPF)
    with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT) as antwort:
        rohdaten = antwort.read()
        endurl = antwort.geturl()
        typ = antwort.headers.get("Content-Type", "")
    kodierung = "utf-8"
    if m := re.search(r"charset=([\w-]+)", typ):
        kodierung = m.group(1)
    text = rohdaten.decode(kodierung, errors="replace")
    if "html" in typ.lower() or text.lstrip()[:200].lower().startswith("<!doctype html"):
        p = NurText()
        p.feed(text)
        text = p.text()
    return text, endurl, typ


def markdown_variante(url: str) -> str | None:
    """Mintlify-Seiten liefern <url>.md. Nur für endungslose Doku-Pfade versuchen."""
    pfad = url.split("?", 1)[0].rstrip("/")
    if re.search(r"\.\w{2,5}$", pfad.rsplit("/", 1)[-1]):
        return None
    return pfad + ".md"


def repo_holen(url: str, ziel: Path) -> tuple[str, list[str]]:
    """Klont flach und fasst alle Markdown-Dateien zu einem Rohtext zusammen."""
    if not shutil.which("git"):
        g.fehler("git nicht gefunden — für GitHub-Quellen nötig.")
    tmp = Path(tempfile.mkdtemp(prefix="recherche-kit-"))
    try:
        lauf = subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", url, str(tmp / "repo")],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if lauf.returncode != 0:
            g.fehler(f"git clone fehlgeschlagen: {lauf.stderr.strip()[:400]}")
        repo = tmp / "repo"
        dateien = sorted(
            (p for p in repo.rglob("*") if p.suffix.lower() in (".md", ".mdx", ".qmd")),
            key=lambda p: (len(p.relative_to(repo).parts), str(p).lower()),
        )
        if not dateien:
            g.fehler("Im Repo wurden keine Markdown-Dateien gefunden.")
        teile, namen = [], []
        for d in dateien:
            rel = d.relative_to(repo).as_posix()
            namen.append(rel)
            inhalt = d.read_text(encoding="utf-8", errors="replace").strip()
            # Jede Datei wird ein Abschnitt erster Ebene, damit Chunk-IDs
            # den Dateipfad tragen (K-05).
            teile.append(f"# {rel}\n\n{inhalt}")
        lizenz = next(
            (p for p in repo.iterdir() if p.name.lower().startswith("licen")), None
        )
        hinweis = ""
        if lizenz:
            hinweis = f"\n\n# LIZENZ\n\n{lizenz.read_text(errors='replace').strip()}"
        return "\n\n".join(teile) + hinweis, namen
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def auffaelligkeiten(text: str) -> list[dict]:
    treffer = []
    for nr, zeile in enumerate(text.splitlines(), 1):
        for muster in INJEKTION:
            if muster.search(zeile):
                treffer.append({"zeile": nr, "ausschnitt": zeile.strip()[:160]})
                break
        if len(treffer) >= 50:
            break
    return treffer


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url")
    ap.add_argument("--tier", type=int, required=True, choices=[1, 2, 3, 4, 5])
    ap.add_argument("--kategorie", required=True)
    ap.add_argument("--titel")
    ap.add_argument("--haken", default="")
    ap.add_argument("--themen", default="")
    ap.add_argument("--lizenz")
    ap.add_argument("--slug")
    ap.add_argument("--id")
    ap.add_argument("--neu-holen", action="store_true")
    a = ap.parse_args()

    w = g.wurzel()
    vorhandene = g.quellen(w)

    ist_repo = bool(re.match(r"https?://github\.com/[^/]+/[^/]+/?$", a.url.rstrip("/")))

    namen: list[str] = []
    md_fassung = None  # genutzte .md-Fassung, falls vorhanden
    if ist_repo:
        text, namen = repo_holen(a.url, w)
        endurl, typ = a.url, "text/markdown (git clone)"
    else:
        text = endurl = typ = None
        if md := markdown_variante(a.url):
            try:
                text, endurl, typ = holen(md)
                if "<html" in text[:500].lower() or len(text) < 50:
                    text = None
                else:
                    md_fassung = endurl
                    # Zitiert wird die Menschenseite, nicht die .md-Fassung (Q-07).
                    endurl = a.url
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
                text = None
        if text is None:
            try:
                text, endurl, typ = holen(a.url)
            except urllib.error.HTTPError as e:
                g.fehler(f"HTTP {e.code} für {a.url}")
            except (urllib.error.URLError, TimeoutError) as e:
                g.fehler(f"Nicht erreichbar: {a.url} — {e}")

    if not text.strip():
        g.fehler(f"Leerer Inhalt von {a.url}")

    titel = a.titel or (
        a.url.rstrip("/").rsplit("/", 2)[-2:][0] + "/" + a.url.rstrip("/").rsplit("/", 1)[-1]
        if ist_repo
        else None
    )
    if not titel:
        m = re.search(r"^#\s+(.+)$", text, re.M)
        titel = m.group(1).strip() if m else a.url.rstrip("/").rsplit("/", 1)[-1]

    schluessel = a.slug or g.slug(titel)
    quelle_id = a.id

    # Bestehende Quelle erkennen, damit --neu-holen nicht doppelt anlegt.
    # Zuerst über die URL, denn der Titel und damit der Slug kann sich ändern.
    def gleiche_url(q: dict) -> bool:
        return a.url.rstrip("/") in {
            str(q.get(f) or "").rstrip("/") for f in ("url", "url_angefragt", "url_markdown")
        }

    treffer = next((q for q in vorhandene if gleiche_url(q)), None) or next(
        (q for q in vorhandene if q.get("slug") == schluessel and q.get("kategorie") == a.kategorie),
        None,
    )
    if treffer:
        # Am bestehenden Ordner bleiben, sonst entstehen Waisen.
        schluessel = treffer.get("slug", schluessel)
        a.kategorie = treffer.get("kategorie", a.kategorie)
        titel = a.titel or treffer.get("titel", titel)
    if treffer and not a.neu_holen and not a.id:
        g.fehler(
            f"Quelle {treffer['id']} liegt schon unter {a.kategorie}/{schluessel}. "
            "Mit --neu-holen aktualisieren."
        )
    if treffer:
        quelle_id = treffer["id"]
    if not quelle_id:
        quelle_id = g.naechste_id(vorhandene, a.tier)

    ordner = w / "wissen" / "quellen" / a.kategorie / schluessel
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "raw.md").write_text(text, encoding="utf-8")

    auff = auffaelligkeiten(text)
    satz = {
        "id": quelle_id,
        "slug": schluessel,
        "titel": titel,
        "url": endurl or a.url,
        "url_angefragt": a.url if (endurl and endurl != a.url) else None,
        "url_markdown": md_fassung,
        "tier": a.tier,
        "kategorie": a.kategorie,
        "veroeffentlicht": None,
        "abgerufen": g.heute(),
        "status": "aktuell",
        "abgleich_am": None,
        "haken": a.haken,
        "themen": [t.strip() for t in a.themen.split(",") if t.strip()],
        "lizenz": a.lizenz,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "zeichen": len(text),
        "chunks": 0,
        "dateien": namen[:200] or None,
        "inhaltstyp": typ,
        "auffaelligkeiten": auff,
    }
    if treffer:
        for feld in ("veroeffentlicht", "status", "abgleich_am", "themen", "haken", "lizenz"):
            if not satz.get(feld) and treffer.get(feld):
                satz[feld] = treffer[feld]
        vorhandene = [q for q in vorhandene if q["id"] != quelle_id]
    vorhandene.append(satz)
    g.quellen_schreiben(w, vorhandene)

    g.spur(
        w, "quelle",
        id=quelle_id, tier=a.tier, kategorie=a.kategorie,
        zeichen=len(text), neu=treffer is None,
        auffaelligkeiten=len(auff), markdown_fassung=bool(md_fassung),
    )

    print(f"{quelle_id}  {titel}")
    print(f"  Stufe {a.tier}  ·  {len(text):,} Zeichen  ·  {ordner.relative_to(w)}")
    if md_fassung:
        print(f"  Markdown-Fassung gelesen: {md_fassung}  ·  zitiert wird {endurl}")
    elif endurl and endurl != a.url:
        print(f"  Umleitung aufgelöst: {a.url} → {endurl}  (Q-07)")
    if namen:
        print(f"  {len(namen)} Markdown-Dateien zusammengefasst")
    if auff:
        print(f"  {len(auff)} Auffälligkeit(en) nach Q-06 — siehe meta/sources.jsonl")
    (ordner / "meta.json").write_text(
        json.dumps(satz, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("  Nächster Schritt: chunken.py " + quelle_id)


if __name__ == "__main__":
    main()
