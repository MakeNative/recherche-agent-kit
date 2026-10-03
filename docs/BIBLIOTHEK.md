# Bibliothek — Struktur und Datenformate

Gilt im Dokumentprojekt, nicht im Plugin. `skills/adopt` legt diese Struktur an.

## Verzeichnisse

```
<dokumentprojekt>/
├── CLAUDE.md                   importiert per @ die drei Routing-Dateien
├── REQUIREMENTS.md
├── STILVERTRAG.md              Prosa für Menschen
├── stil.json                   Schwellen für stil_pruefen.py
├── _quarto.yml
├── OUTLINE.md
│
├── wissen/
│   ├── INDEX.md                generiert — K-02, K-03
│   ├── THEMEN.md               generiert — Thema → Quellen-IDs
│   ├── GLOSSAR.md              Begriff, de/en, Aliasse, veraltete Namen
│   ├── FRISCHE.md              generiert — Abgleichprotokoll
│   ├── LUECKEN.md
│   ├── sources.jsonl           einzige Wahrheit über Quellen
│   └── quellen/<kategorie>/<slug>/
│       ├── meta.json
│       ├── CARD.md             nur Stufe 2–5
│       ├── raw.md
│       └── chunks.jsonl
│
├── claims/<kapitel-slug>.jsonl
├── kapitel/<nr>-<slug>.qmd
└── gates/{quellen,verstaendnis,luecken}-report.md
```

Kategorien unter `wissen/quellen/`:

```
1-offiziell-anthropic/   docs-api-en, docs-api-de, docs-code, engineering, cookbook, releases
1-offiziell-andere/      codex, cursor, copilot, windsurf
2-praxis-repos/
3-forschung/
4-community/
5-markt/
```

Die Zahl im Kategorienamen **ist** die Autoritätsstufe nach Q-01 und sortiert
gleichzeitig.

## meta.json

```json
{
  "id": "A-07",
  "titel": "Claude Code — Memory",
  "url": "https://code.claude.com/docs/en/memory",
  "url_angefragt": "https://docs.claude.com/en/docs/claude-code/memory",
  "tier": 1,
  "kategorie": "1-offiziell-anthropic/docs-code",
  "veroeffentlicht": null,
  "abgerufen": "2026-10-03",
  "status": "aktuell",
  "abgleich_am": null,
  "haken": "CLAUDE.md, @-Imports, Importtiefe, Ladereihenfolge",
  "themen": ["kontext", "bibliothek"],
  "lizenz": null,
  "sha256": "…",
  "chunks": 12,
  "auffaelligkeiten": []
}
```

- `url` ist das aufgelöste Ziel, `url_angefragt` die ursprünglich angefragte
  Adresse, falls umgeleitet wurde — Q-07.
- `status`: `aktuell` · `ueberholt` · `widersprochen` · `unklar`
- `haken` ist **kein** Inhalt, sondern Routing: worüber beantwortet diese
  Quelle Fragen. Diese Zeile landet im Index, mehr nicht — K-02.
- `auffaelligkeiten` sammelt Fundstellen nach Q-06.

## chunks.jsonl

Eine Zeile pro Abschnitt:

```json
{"chunk_id":"A-07#memory/imports","pfad":["Memory","Imports"],"zeilen":[120,156],"ueberschrift":"Imports","zeichen":1840}
```

Chunk-IDs sind stabil nach K-05: Quellen-ID, `#`, dann der mit `/` verbundene
slugifizierte Überschriftenpfad.

## CARD.md

Nur für Stufe 2–5. 10 bis 20 Zeilen, nach dieser Form:

```markdown
# <Titel>  ·  <id>  ·  Stufe <n>  ·  abgerufen <datum>

**Worum es geht:** ein Satz.

**Kernaussagen**
1. <Aussage> — „<wörtliches Zitat>" (`<chunk_id>`)
2. …

**Frische:** <aktuell | ueberholt | widersprochen | unklar> — Begründung,
bei Widerspruch mit Gegenbeleg aus Stufe 1.

**Brauchbar für:** <Themen oder Kapitel>
**Nicht brauchbar für:** <was man hier nicht nachschlagen darf, meist
Funktionsaussagen nach Q-01>
```

## claims/<kapitel>.jsonl

```json
{
  "claim_id": "K03-004",
  "aussage": "CLAUDE.md kann weitere Dateien per @pfad importieren, rekursiv bis vier Ebenen tief.",
  "typ": "funktion",
  "quelle": "A-07",
  "chunk_id": "A-07#memory/imports",
  "zitat": "maximum depth of four hops",
  "status": "belegt",
  "schwierig": true,
  "stand": "2026-10-03"
}
```

- `typ`: `funktion` · `erfahrung` · `urteil` · `zahl`
  `funktion` und `zahl` verlangen Stufe 1 nach Q-01.
- `status`: `belegt` · `offen` · `widersprochen` · `pruefen`
  `pruefen` setzt `frische_lauf.py`, wenn sich der belegende Chunk geändert hat.
- `schwierig` steuert, ob der `beispiel-agent` ein Alltagsbeispiel liefert — S-05.

## .claude/recherche-log/lauf.jsonl

Laufprotokoll, angehängt von den Werkzeugen und von `guard-tier.py`. Einzige
Datengrundlage für `evaluieren` — ohne es beruht die Bewertung der Pipeline auf
Erinnerung.

```json
{"zeit":"2026-10-03T13:41:02","ereignis":"gate","werkzeug":"claims_pruefen","kapitel":"03-bibliothek","geprueft":42,"befunde":3,"nach_regel":{"Q-03":2,"Q-01":1}}
{"zeit":"2026-10-03T13:41:58","ereignis":"blockade","hook":"guard-tier","datei":"03-bibliothek.jsonl","anzahl":1,"regeln":["Q-01"],"beispiel":"K03-7: typ `funktion` verlangt …"}
{"zeit":"2026-10-03T13:42:10","ereignis":"quelle","id":"A-08","tier":1,"zeichen":50496,"neu":true,"auffaelligkeiten":0}
{"zeit":"2026-10-03T13:50:00","ereignis":"frische","angewendet":true,"geprueft":12,"geaendert":["A-03"],"claims_auf_pruefen":4}
```

Ereignistypen: `quelle` · `gate` · `frische` · `blockade` · `hinweis`.

Ein fehlgeschlagener Protokolleintrag bricht nie einen Lauf ab. Protokollieren
ist Beobachtung, nicht Teil der Arbeit.

## .claude/agent-memory/recherche-kit-&lt;agent&gt;/

Für die Agenten mit `memory: project`: `kartenschreiber`, `frische-pruefer`,
`writer`, `verdichter`, `lauf-auswerter`.

Hierher gehört nur, was über einen Lauf hinaus gilt und aus dem Protokoll
belegt ist. Gepflegt wird es von `evaluieren`, nicht von den Agenten selbst.

`laien-leser` hat bewusst **kein** Memory — siehe seine Beschreibung.

## stil.json

Schwellen für `stil_pruefen.py`. Fehlt die Datei, gelten die Vorgaben im Skript.

```json
{
  "satz_max_woerter": 28,
  "absatz_max_saetze": 6,
  "phrasen_verboten": [
    "nicht nur", "sondern auch", "in der heutigen", "es ist wichtig zu",
    "zusammenfassend", "wie bereits erwähnt", "tauchen wir ein",
    "revolutionär", "bahnbrechend", "nahtlos", "mühelos"
  ],
  "abschnitt_braucht_beispiel": true,
  "beispiel_marker": ["Beispiel", "Zum Beispiel", "Konkret", "In der Praxis", "```"],
  "glossar_pflicht": true
}
```
