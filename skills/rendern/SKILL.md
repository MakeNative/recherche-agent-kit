---
name: rendern
description: "Rendert das Dokument als Quarto-Buch, PDF und revealjs-Präsentation aus einem Quellstand. Baut die Folien aus den Kernsätzen der Kapitel. Triggers on: /recherche-kit:rendern [html|pdf|slides|alle]"
disable-model-invocation: true
argument-hint: "[html|pdf|slides|alle]"
---

Du rendert, was fertig ist. Die Präsentation ist kein neues Dokument, sondern
ein zweites Ausgabeformat derselben Quelle.

## Vorbedingungen

- `luecken` hat freigegeben, oder der Nutzer rendert ausdrücklich einen
  Zwischenstand. Frag nachdem, wenn unklar
- `quarto --version` läuft. Fehlt Quarto, sag das und nenne den
  Installationsweg, statt einen Fehler zu zeigen
- Für PDF ist eine TeX-Installation nötig. Fehlt sie, rendere HTML und sag es

## Buch und PDF

```bash
quarto render --to html
quarto render --to pdf
```

Fußnoten prüfen: in jedem Kapitel müssen die `[^claim_id]` Definitionen am Ende
stehen und im gerenderten Ergebnis auflösen. Quarto meldet unaufgelöste
Fußnoten nicht als Fehler — prüf gezielt:

```bash
grep -o '\[\^[^]]*\]' kapitel/*.qmd | sort | uniq -c | sort -n | head -20
```

Eine Claim-ID, die nur einmal vorkommt, hat entweder keinen Verweis oder keine
Definition.

## Präsentation

Die Folien entstehen aus den Kernsätzen, nicht aus dem Kapiteltext. Ein Kapitel
wird nicht eine Folie — es wird ein Abschnitt mit Titelfolie und zwei bis fünf
Inhaltsfolien.

Lege `slides.qmd` an:

```yaml
---
title: "<Titel>"
author: "<Autor>"
format:
  revealjs:
    slide-number: true
    footer: "Stand <datum>"
    incremental: false
---
```

Je Kapitel:

1. **Titelfolie** — der Kernsatz als Überschrift, nichts weiter darauf
2. **Inhaltsfolien** — zwei bis fünf Aussagen des Kapitels, je drei bis sieben
   Wörter auf einer Zeile. Keine Sätze auf Folien
3. **Beispielfolie** — das Beispiel aus dem Kapitel, gekürzt
4. **Schrittfolie** — der erste konkrete Schritt

Fußnoten auf Folien weglassen, aber eine **Quellenfolie am Ende** je Abschnitt
oder gesammelt am Schluss: Quellen-IDs mit Titel und URL. Belege verschwinden
nicht, nur weil das Format kürzer ist (Q-02).

```bash
quarto render slides.qmd --to revealjs
```

## Was du beim Rendern nicht tust

- Keinen Inhalt für die Folien neu schreiben. Steht etwas nicht im Kapitel,
  gehört es nicht auf die Folie
- Keine Aussage auf einer Folie, die im Dokument `offen` ist
- Nichts kürzen, indem du eine Einschränkung weglässt. Eine Folie ohne die
  Einschränkung behauptet mehr als das Kapitel

## Zum Schluss

```
HTML:     <pfad> | Fehler
PDF:      <pfad> | übersprungen, weil <grund>
SLIDES:   <pfad> — <n> Folien aus <m> Kapiteln
FUSSNOTEN: <n> geprüft, <m> unaufgelöst: <ids>
STAND:    <datum im Dokument>
OFFEN:    <was aus wissen/LUECKEN.md im Dokument benannt ist>
```
