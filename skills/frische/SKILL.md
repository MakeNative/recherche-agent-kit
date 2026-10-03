---
name: frische
description: "Prüft Drittquellen gegen die offizielle Doku und setzt deren Status: aktuell, überholt, widersprochen, unklar. Erzeugt dabei das Material für ein Kapitel über veraltete Ratschläge. Triggers on: /recherche-kit:frische [quellen-id ...] [--neuabruf]"
disable-model-invocation: true
argument-hint: "[quellen-id ...] [--neuabruf]"
---

Du entscheidest, welche Quelle als überholt gilt. Das ist eine Entscheidung mit
Folgen: eine überholte Quelle belegt nichts mehr (Q-04), und bereits
geschriebene Kapitel können dadurch Löcher bekommen.

## Zwei verschiedene Läufe

**Abgleich** (Standard): Kernaussagen aus Stufe 2–5 gegen Stufe 1 prüfen. Das
ist die inhaltliche Arbeit.

**Neuabruf** (`--neuabruf`): Stufe-1-Quellen neu holen und schauen, ob sich die
offizielle Doku geändert hat. Das ist die Wartung.

```bash
# erst Probelauf, überschreibt nichts
python3 "${CLAUDE_PLUGIN_ROOT}/tools/frische_lauf.py" --tier 1
# dann bewusst anwenden
python3 "${CLAUDE_PLUGIN_ROOT}/tools/frische_lauf.py" --tier 1 --anwenden
```

Führe `--anwenden` nie aus, ohne den Probelauf gezeigt und die Zustimmung
eingeholt zu haben. Ein Neuabruf macht Zitate ungültig und setzt Aussagen auf
`pruefen`.

## Ablauf des Abgleichs

1. Sammle die Kernaussagen aller Quellen der Stufe 2–5 aus deren `CARD.md`.
2. Spawn je Kernaussage einen `frische-pruefer` — **parallel**, die Aussagen
   sind voneinander unabhängig. Bei vielen Aussagen in Bündeln von zehn bis
   fünfzehn, damit die Berichte überschaubar bleiben.
3. Werte die Urteile aus und setze den Quellenstatus. Das ist deine Entscheidung,
   nicht die des Agenten (P-02).

## Status setzen

| Lage | Status |
|---|---|
| alle Kernaussagen bestätigt oder nicht abgedeckt | `aktuell` |
| eine Funktionsaussage widersprochen | `ueberholt` |
| mehrere Aussagen widersprochen, auch nicht-funktionale | `widersprochen` |
| Funktionsaussagen nicht abgedeckt und nicht prüfbar | `unklar` |

Ein Widerspruch bei einer Erfahrungs- oder Urteilsaussage macht eine Quelle
**nicht** überholt. Zwei Leute dürfen über Vorgehen unterschiedlicher Meinung
sein; das ist kein Fehler, sondern Inhalt.

Trag den Status in `sources.jsonl` und `meta.json` ein, setze `abgleich_am` auf
heute, und lauf danach `index_bauen.py`.

## Der eigentliche Gewinn

Jeder `widersprochen`-Befund ist ein Stück Inhalt: ein verbreiteter Ratschlag,
der nicht mehr gilt. Schreib diese Fälle sorgfältig nach `wissen/FRISCHE.md`,
je mit beiden Zitaten — was die Drittquelle sagt und was offiziell gilt.

Für die Zielgruppe ist das oft wertvoller als eine Werkzeugübersicht, weil sie
beim Suchen zuerst auf alte Anleitungen stößt. Behandle diesen Abschnitt nicht
als Nebenprodukt.

## Folgen für bestehende Aussagen

Setzt du eine Quelle auf `ueberholt` oder `widersprochen`, prüfe, ob sie schon
Aussagen trägt:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/claims_pruefen.py"
```

Jeder Q-04-Befund ist eine Aussage, die neu belegt oder gestrichen werden muss.
Gib die Liste weiter an `recherche`.

## Wenn ein Agent stirbt

Ein Agent, der ohne vollständigen Bericht endet, zählt nie als „nichts
gefunden" (P-07). Prüf jeden Bericht auf seine Pflichtblöcke, starte einmal neu
mit dem Hinweis, knapp zu bleiben, und melde beim zweiten Fehlschlag den Auftrag
als unerledigt — mit Quellen-ID oder Kapitel, damit er nicht verschwindet.

## Zum Schluss

```
GEPRÜFT:        <n> Aussagen aus <m> Quellen
BESTÄTIGT:      <n>
WIDERSPROCHEN:  <n> — <Quellen-IDs>
NICHT ABGEDECKT: <n>
STATUS GEÄNDERT: <id: alt → neu, je mit Grund>
BETROFFENE AUSSAGEN: <claim_ids, die jetzt neu belegt werden müssen>
INHALT GEWONNEN: <wie viele veraltete Ratschläge dokumentiert sind>
NÄCHSTER SCHRITT: /recherche-kit:outline oder /recherche-kit:recherche
```
