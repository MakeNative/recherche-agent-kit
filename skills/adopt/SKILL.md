---
name: adopt
description: "Richtet ein Dokumentprojekt für die Pipeline ein: Bibliotheksstruktur, CLAUDE.md mit Routing-Imports, Quarto-Gerüst, Stilvertrag-Vorlage, Glossar. Einmal je Projekt, danach jederzeit zum Auffrischen. Triggers on: /recherche-kit:adopt [projektname]"
disable-model-invocation: true
argument-hint: "[projektname]"
---

Du richtest ein Projekt ein, in dem später ein belegtes Langdokument entsteht.
Diese Skill legt Struktur an und stellt Fragen — sie recherchiert nichts.

Läuft im Hauptkontext, weil sie Entscheidungen über Benennung und Zuschnitt
trifft und dafür fragen muss (P-01).

## Vorbedingungen

Brich ab, wenn `wissen/sources.jsonl` schon existiert und mehr als eine Zeile
hat — dann ist das Projekt eingerichtet. Zum Auffrischen einzelner Dateien
sag, was du ersetzen würdest, und frag vorher.

Lies `${CLAUDE_PLUGIN_ROOT}/docs/BIBLIOTHEK.md` und
`${CLAUDE_PLUGIN_ROOT}/docs/REGELWERK.md`, bevor du anlegst.

## Was du anlegst

```
wissen/quellen/1-offiziell-anthropic/{docs-api-en,docs-api-de,docs-code,engineering,cookbook,releases}/
wissen/quellen/1-offiziell-andere/
wissen/quellen/{2-praxis-repos,3-forschung,4-community,5-markt}/
wissen/sources.jsonl          leer
wissen/GLOSSAR.md             Gerüst
claims/  kapitel/  gates/
stil.json                     aus docs/BIBLIOTHEK.md übernehmen
CLAUDE.md
_quarto.yml

.claude/recherche-log/        Laufprotokoll, Grundlage für `evaluieren`
.claude/agent-memory/recherche-kit-{kartenschreiber,frische-pruefer,writer,verdichter,lauf-auswerter}/
```

Das Protokoll und die Memory-Verzeichnisse gehören in die `.gitignore` des
Dokumentprojekts, falls der Inhalt nicht geteilt werden soll — sie enthalten
Laufdaten, keine Quellen.

`laien-leser` bekommt **kein** Memory-Verzeichnis, obwohl er `memory: project`
hat. Ein Laie, der sich über Läufe hinweg etwas merkt, ist kein Laie mehr und
verliert seine Messfähigkeit. Lege den Ordner nicht an.

`INDEX.md`, `THEMEN.md` und `FRISCHE.md` legst du **nicht** an — die sind
generiert (K-03) und entstehen beim ersten Lauf.

## CLAUDE.md

Genau diese Form. Die `@`-Zeilen laden die Routing-Dateien beim Start; mehr
gehört nicht hinein, weil alles hier in jedem Kontext liegt.

```markdown
# <Projektname>

Belegtes Langdokument, gebaut mit dem Plugin `recherche-kit`.

## Leseweg für Quellen

Index → Karte → erst dann Rohtext über die Chunk-ID (K-01). Nie eine ganze
Rohdatei laden, nie den Index umgehen.

## Harte Regel

Aussagen über aktuellen Funktionsumfang, Zahlen, Preise und Limits nur aus
Quellen der Stufe 1. Drittquellen tragen Erfahrung, Vorgehen und Urteil (Q-01).

## Routing

@wissen/INDEX.md
@wissen/THEMEN.md
@wissen/GLOSSAR.md

## Regelwerk

Vollständig in `${CLAUDE_PLUGIN_ROOT}/docs/REGELWERK.md`. Bei Befunden immer
die Regel-ID nennen.
```

Hinweis: `INDEX.md` und `THEMEN.md` existieren beim ersten Start noch nicht.
Lege beide als leere Datei mit einer Kommentarzeile an, damit der Import nicht
ins Leere zeigt.

## _quarto.yml

Buch und Präsentation aus einem Quellstand. Kapitelliste bleibt zunächst leer
und wird von `outline` gefüllt.

```yaml
project:
  type: book
book:
  title: "<Titel>"
  author: "<Autor>"
  date: today
  chapters:
    - index.qmd
format:
  html:
    toc: true
    number-sections: true
  pdf:
    documentclass: scrreprt
    lang: de
```

Die revealjs-Variante legt `rendern` an, nicht du — sie braucht die Kernsätze.

## Was du fragst

Nur was du nicht erschließen kannst, und in einer Runde:

1. Projektname und Titel des Dokuments
2. Autorenname für das Impressum
3. Sprache des Dokuments
4. Soll `git init` laufen, falls noch kein Repo da ist

Alles andere — Zitierstil, Zahlen-Policy, Ansprache, Zielgruppe — gehört in
`REQUIREMENTS.md` und wird **nicht** hier geklärt. Lege die Datei mit den
offenen Fragen als Liste an und sag dem Nutzer, dass sie vor dem ersten Kapitel
beantwortet sein muss.

## Zum Schluss

Schreib eine kurze Übersicht: was liegt jetzt wo, was ist der nächste Befehl
(`/recherche-kit:quelle-aufnehmen`), und was in `REQUIREMENTS.md` noch offen ist.
