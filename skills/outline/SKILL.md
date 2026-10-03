---
name: outline
description: "Erarbeitet die Gliederung mit einem Kernsatz je Kapitel, legt die Kapitelform fest und trägt die Kapitel in _quarto.yml ein. Wichtigster Freigabepunkt — danach wird parallel gearbeitet. Triggers on: /recherche-kit:outline [--ueberarbeiten]"
disable-model-invocation: true
argument-hint: "[--ueberarbeiten]"
---

Du erarbeitest die Gliederung **mit dem Nutzer**, nicht für ihn. Das ist der
teuerste Punkt zum Umbauen: danach laufen Kapitel parallel, und eine Änderung
an der Struktur wirft mehrere Kapitel zurück.

Diese Skill fragt mehr als jede andere. Das ist richtig.

## Vorbedingungen

- `wissen/INDEX.md` existiert und enthält Quellen
- `wissen/FRISCHE.md` liegt vor, sonst gliederst du auf veraltetem Stand
- `REQUIREMENTS.md` ist beantwortet — besonders Zielgruppe, Ansprache und
  Zahlen-Policy. Fehlt das, frag zuerst danach; die Gliederung hängt daran.

## Der Kernsatz

Jedes Kapitel bekommt **einen** Satz, der das ganze Kapitel trägt. Er ist
später der Titel einer Folie, deshalb muss er für sich allein stehen können.

Ein guter Kernsatz behauptet etwas. „Agenten brauchen eine Wissensbibliothek,
weil kein Kontextfenster die Quellen fasst" ist ein Kernsatz. „Über
Wissensbibliotheken" ist eine Überschrift.

Prüfe jeden Kernsatz gegen drei Fragen:

1. Behauptet er etwas, dem man widersprechen könnte?
2. Lässt er sich mit den vorhandenen Quellen belegen? Schau in `THEMEN.md`.
3. Versteht ihn jemand ohne Vorwissen?

Scheitert ein Kernsatz an Frage 2, ist das Kapitel nicht schreibbar — entweder
Quellen beschaffen oder Kapitel streichen. Sag das deutlich, statt es
hoffnungsvoll stehenzulassen.

## Die Kapitelform

Gilt für alle Kapitel gleich, damit Leser unterschiedlich tief einsteigen können:

1. Kernsatz
2. Worum es geht — ohne Fachbegriffe, Ausstiegspunkt für Laien
3. Die Sache selbst
4. Beispiel
5. Erster Schritt — konkret, nicht „probieren Sie es aus"

Leg sie als Abschnitt in `OUTLINE.md` fest, damit `writer` und `luecken-finder`
dieselbe Form prüfen.

## Reihenfolge der Kapitel

Nach Abhängigkeit, nicht nach Wichtigkeit. Ein Kapitel darf nur Begriffe
benutzen, die ein früheres erklärt hat — sonst bricht S-03 überall.

Prüfe am Ende: wenn jemand genau bis Kapitel n liest und aufhört, hat er dann
etwas Brauchbares? Wenn die Antwort erst bei Kapitel 9 ja lautet, ist die
Reihenfolge falsch.

## Was du fragst

- Welche Kapitel fehlen, welche sind zu viel
- Bei jedem Kernsatz: trifft er, was gemeint ist
- Wo im Dokument die Kandidaten aus `wissen/FRISCHE.md` landen sollen
- Ob ein Kapitel zweigeteilt werden soll, weil es zwei Zielgruppen bedient

Zeig die Gliederung als Liste mit Kernsätzen und frag in einer Runde, nicht
Kapitel für Kapitel.

## Ergebnis

`OUTLINE.md` mit je Kapitel: Nummer, Slug, Kernsatz, geplante Themen, erwartete
Quellen-IDs aus `THEMEN.md`, offene Punkte.

Dann die Kapitelliste in `_quarto.yml` eintragen und ein leeres
`kapitel/<nr>-<slug>.qmd` je Kapitel anlegen, damit Quarto schon rendert.

```bash
quarto render --to html 2>&1 | tail -5
```

Läuft das nicht, repariere es jetzt. Ein Renderfehler nach zwanzig fertigen
Kapiteln ist teurer.

## Zum Schluss

```
KAPITEL:              <n>
OHNE QUELLENDECKUNG:  <slugs — brauchen Recherche oder entfallen>
ZWEIFELHAFTE KERNSÄTZE: <slugs mit Grund>
QUARTO:               rendert | Fehler: <…>
FREIGABE NÖTIG:       ja — danach läuft es parallel
NÄCHSTER SCHRITT:     /recherche-kit:fragen alle
```

Hol die Freigabe ausdrücklich ein. Fang nicht mit `fragen` an, weil es
naheliegt.
