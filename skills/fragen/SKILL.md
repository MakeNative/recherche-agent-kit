---
name: fragen
description: "Lässt drei Perspektiv-Agenten parallel Fragen an ein geplantes Kapitel stellen und entscheidet, welche davon Recherche-Aufträge werden. Triggers on: /recherche-kit:fragen <kapitel-slug | alle>"
disable-model-invocation: true
argument-hint: "<kapitel-slug | alle>"
---

Du sammelst Fragen aus drei Blickwinkeln und entscheidest, welche verfolgt
werden. Das Entscheiden ist der Punkt: ungefiltert erzeugen drei Agenten
dreißig Fragen je Kapitel, und die Hälfte davon führt nirgendwohin (P-02).

## Ablauf

1. Lies den Kapitelabschnitt aus `OUTLINE.md`, `REQUIREMENTS.md` und, falls
   schon vorhanden, die Claim-Datei des Kapitels.
2. Spawn **parallel** und mit identischem Material:
   `perspektive-entwickler`, `perspektive-laie`, `perspektive-entscheider`.
   Parallel und getrennt, weil ein Agent, der alle drei Rollen spielt, an seiner
   ersten Perspektive ankert.
3. Lege die drei Berichte zusammen.

## Entscheiden

Je Frage genau eine Einordnung:

**Rechercheauftrag** — die Antwort steht womöglich in der Bibliothek oder in
einer noch fehlenden Quelle. Geht an `recherche`.

**Schon beantwortet** — steht bereits in einer belegten Aussage. Notiere die
Claim-ID. Das ist nützlich: es zeigt, dass der Text die Frage trifft.

**Gehört in ein anderes Kapitel** — mit Zielkapitel notieren, damit es dort
nicht verloren geht.

**Nicht belegbar** — berührt etwas, das niemand sauber belegen kann, etwa
Marktprognosen. Nach S-06 entweder weglassen oder sichtbar als Einschätzung
führen. Das ist eine Nutzerentscheidung nach der Zahlen-Policy; frag, wenn die
Frage inhaltlich wichtig ist.

**Verworfen** — mit Grund. Nie stillschweigend fallenlassen (P-06).

## Worauf du besonders achtest

Fragen des `perspektive-laie`, die **keine** Begriffsfrage sind, sondern
„warum sollte ich das wollen". Solche Fragen deuten darauf hin, dass dem Kapitel
der Nutzen fehlt, nicht die Erklärung. Das ist ein Outline-Mangel, kein
Recherchebedarf — gib ihn an `outline` zurück statt an `recherche`.

Fragen, die alle drei Perspektiven stellen. Das ist die wichtigste Frage des
Kapitels und gehört in den Kernsatz.

## Wenn ein Agent stirbt

Ein Agent, der ohne vollständigen Bericht endet, zählt nie als „nichts
gefunden" (P-07). Prüf jeden Bericht auf seine Pflichtblöcke, starte einmal neu
mit dem Hinweis, knapp zu bleiben, und melde beim zweiten Fehlschlag den Auftrag
als unerledigt — mit Quellen-ID oder Kapitel, damit er nicht verschwindet.

## Zum Schluss

Schreib die Aufträge in `wissen/FRAGEN-<kapitel>.md`, damit `recherche` sie
findet, und berichte:

```
KAPITEL:            <slug>
FRAGEN GESAMT:      <n> (Entwickler <a>, Laie <b>, Entscheider <c>)
RECHERCHEAUFTRÄGE:  <n> → wissen/FRAGEN-<kapitel>.md
SCHON BEANTWORTET:  <n> mit Claim-IDs
ANDERES KAPITEL:    <frage → zielkapitel>
NICHT BELEGBAR:     <fragen, Entscheidung nötig>
VERWORFEN:          <frage — grund>
VON ALLEN DREI GEFRAGT: <die Fragen — Kandidaten für den Kernsatz>
OUTLINE-MANGEL:     <Nutzenfragen, die zurück an outline gehen>
NÄCHSTER SCHRITT:   /recherche-kit:recherche <kapitel>
```
