---
name: recherche
description: "Füllt die Claim-Liste eines Kapitels aus der Bibliothek, entscheidet welche Aussagen es braucht und was offen bleibt, und stößt fehlende Quellen an. Triggers on: /recherche-kit:recherche <kapitel-slug> [--nur-offene]"
disable-model-invocation: true
argument-hint: "<kapitel-slug> [--nur-offene]"
---

Du entscheidest, welche Aussagen ein Kapitel braucht. Das ist die inhaltliche
Kernentscheidung des ganzen Projekts: die Claim-Liste bestimmt, was im Kapitel
steht und wie lang es wird.

Der `claim-sammler` extrahiert, du entscheidest (P-02).

## Ablauf

1. Lies `OUTLINE.md` (Kernsatz des Kapitels), `wissen/FRAGEN-<kapitel>.md`,
   `wissen/THEMEN.md` und `wissen/INDEX.md`.
2. **Bestimme je Frage die Quellen**, die sie beantworten könnten. Über die
   Themenkarte, nicht über Raten. Lies die Karten der Kandidaten (K-01).
3. Spawn `claim-sammler` **parallel**, einen je Fragenbündel oder Quellengruppe.
   Gib jeder Instanz ausdrücklich die Quellen-IDs mit, in denen sie suchen soll —
   sonst liest sie die halbe Bibliothek.
4. Nimm die JSON-Zeilen entgegen, entscheide und schreib `claims/<kapitel>.jsonl`.

## Entscheiden, was aufgenommen wird

**Aufnehmen** wenn die Aussage eine Frage beantwortet, die ins Kapitel gehört,
und einen Beleg hat.

**Verwerfen** wenn sie richtig und belegt, aber für dieses Kapitel ohne Folge
ist. Das ist der häufigste Fall und der wichtigste Filter — hier entsteht
Dichte. Grund notieren.

**Als `offen` führen** wenn die Frage wichtig ist und der Beleg fehlt. Eine
offene Aussage ist ein Auftrag, keine Lücke im Text: der `writer` lässt sie weg.

**Zusammenführen** wenn zwei Sammler dasselbe gefunden haben. Nimm die Quelle
mit der niedrigeren Stufenzahl.

**Teilen** wenn eine Aussage zwei Behauptungen trägt. Jede braucht ihren eigenen
Beleg.

## Typ und Stufe prüfen, bevor du schreibst

Für jede Aussage mit Typ `funktion` oder `zahl`: ist die Quelle Stufe 1? Wenn
nicht, hast du zwei Möglichkeiten — einen Stufe-1-Beleg suchen, oder die Aussage
auf `offen` setzen. Niemals die Stufe hochschreiben.

Gegenprobe nach dem Schreiben:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/claims_pruefen.py" <kapitel>
```

Exit 0 ist die Vorbedingung dafür, dass `kapitel` laufen darf. Arbeite die
Befunde ab, bevor du weitergibst.

## Wenn Quellen fehlen

Bleiben Fragen ohne jede Quelle, ist das ein Bibliotheksmangel, kein
Schreibmangel. Sag, welche Quelle fehlen würde, und schlag konkrete URLs vor.
Die Aufnahme läuft über `quelle-aufnehmen`, nicht hier — sonst landen Quellen
ohne Stufeneinordnung in der Bibliothek.

## Umfang

Es gibt keine Zielzahl an Aussagen. Ein Kapitel mit acht Aussagen ist kurz, weil
es wenig zu sagen gibt — das ist in Ordnung. Füll nicht auf, um Länge zu
erzeugen, und streich nicht, um Kürze zu erzeugen.

## Wenn ein Agent stirbt

Ein Agent, der ohne vollständigen Bericht endet, zählt nie als „nichts
gefunden" (P-07). Prüf jeden Bericht auf seine Pflichtblöcke, starte einmal neu
mit dem Hinweis, knapp zu bleiben, und melde beim zweiten Fehlschlag den Auftrag
als unerledigt — mit Quellen-ID oder Kapitel, damit er nicht verschwindet.

## Zum Schluss

```
KAPITEL:        <slug>
AUFGENOMMEN:    <n> Aussagen (funktion <a>, zahl <b>, erfahrung <c>, urteil <d>)
OFFEN:          <n> — je Frage und was fehlt
VERWORFEN:      <n> — je Aussage ein Grund
SCHWIERIG:      <claim_ids für den beispiel-agent>
QUELLEN:        <ids, die das Kapitel belegen>
FEHLENDE QUELLEN: <vorgeschlagene URLs mit Stufe>
PRÜFUNG:        claims_pruefen.py exit <n>
NÄCHSTER SCHRITT: /recherche-kit:kapitel <slug>
```
