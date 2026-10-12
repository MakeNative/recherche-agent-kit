---
name: kapitel
description: "Schreibt ein Kapitel: writer, dann verdichter, dann beispiel-agent, mit Stilprüfung nach jedem Schritt. Entscheidet, ob das Kapitel durch ist oder zurückgeht. Triggers on: /recherche-kit:kapitel <kapitel-slug | alle>"
disable-model-invocation: true
argument-hint: "<kapitel-slug | alle>"
---

Du führst ein Kapitel von der Claim-Liste zum fertigen Text und entscheidest, ob
es durch ist.

## Vorbedingungen

Brich ab, wenn eines davon nicht gilt:

- `claims/<kapitel>.jsonl` existiert und enthält Aussagen mit `status: belegt`
- `claims_pruefen.py <kapitel>` endet mit 0
- `STILVERTRAG.md` und `REQUIREMENTS.md` liegen vor
- der Kernsatz steht in `OUTLINE.md`

Ein Kapitel ohne bestandene Quellenprüfung zu schreiben erzeugt Text, der
nachher wieder auseinanderfällt.

## Ablauf

**1. Writer.** Spawn `writer` mit Kapitel-Slug. Er schreibt
`kapitel/<nr>-<slug>.qmd` und berichtet, was er nicht verwendet hat und was
ihm gefehlt hat.

Meldet er **fehlende Aussagen**, entscheide: zurück an `recherche` oder ohne
sie weiter. Schreib sie nicht selbst dazu.

**2. Stil messen.**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/stil_pruefen.py" kapitel/<nr>-<slug>.qmd
```

**3. Verdichter — nur bei Bedarf.** Spawn `verdichter` mit der Datei und dem
Stilbericht, wenn mindestens eins zutrifft: der Stilbericht meldet S-01 oder
S-02, oder die Datei liegt über 22.000 Zeichen. Steht das Gate auf 0 Befunden
und die Datei darunter, entfällt der Schritt — ein gemessener Lauf über fünf
grüne Kapitel kostete 342.192 Token für 1,97 % Zeichenersparnis bei Befunden
0→0; das ist Pflegeaufwand ohne Befundwirkung. Der Verdichter streicht, er
fügt nichts hinzu (P-05). Danach Stil erneut messen.

Zwei Durchläufe des Verdichters sind normal. Ein dritter bringt selten etwas —
dann liegt das Problem in der Claim-Liste, nicht im Text.

**4. Beispiele.** Spawn `beispiel-agent` für alle Aussagen mit
`schwierig: true` und alle offenen `<!-- beispiel: ... -->` Marken.
**Parallel**, einer je Aussage oder kleines Bündel.

Setz die Beispiele selbst ein — der Agent hat keine Schreibrechte. Ersetze die
Marke, lass die Fußnote stehen.

**5. Schlussprüfung.**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/claims_pruefen.py" <kapitel> --kapitel-text
python3 "${CLAUDE_PLUGIN_ROOT}/tools/stil_pruefen.py" kapitel/<nr>-<slug>.qmd
```

## Entscheiden, ob das Kapitel durch ist

**Durch** wenn beide Skripte 0 liefern, keine Beispielmarke offen ist und jeder
Abschnitt der Kapitelform vorhanden ist.

**Zurück an `recherche`** wenn Aussagen fehlen oder offen sind, die der Text
braucht.

**Zurück an `outline`** wenn beim Schreiben klar wird, dass der Kernsatz nicht
trägt oder das Kapitel zwei Themen vermischt. Das passiert, und früh zu stoppen
ist billiger als ein Kapitel, das niemand versteht.

**Offen lassen mit Vermerk** wenn nur S-03-Befunde übrig sind. Glossarlücken
werden gesammelt und einmal behoben, nicht je Kapitel einzeln.

## Bei `alle`

Kapitel sind voneinander unabhängig — **fahre sie parallel**, nicht
hintereinander. Ein Kapitel kann beim Verdichter sein, während ein anderes noch
beim Writer ist. Es gibt keine Barriere zwischen den Schritten.

Zwei Ausnahmen: Glossarlücken sammelst du über alle Kapitel und behebst sie
einmal am Ende. Und bei mehr als sechs Kapiteln gleichzeitig wird die Rückmeldung
unübersichtlich — dann in Bündeln.

## Wenn ein Agent stirbt

Ein Agent, der ohne vollständigen Bericht endet, zählt nie als „nichts
gefunden" (P-07). Prüf jeden Bericht auf seine Pflichtblöcke, starte einmal neu
mit dem Hinweis, knapp zu bleiben, und melde beim zweiten Fehlschlag den Auftrag
als unerledigt — mit Quellen-ID oder Kapitel, damit er nicht verschwindet.

## Zum Schluss

```
KAPITEL:            <slug>
AUSSAGEN VERWENDET: <n> von <m> belegten
ZEICHEN:            <writer> → <nach verdichter>
STILBEFUNDE:        <vorher> → <nachher>  (offen: <welche Regeln>)
BEISPIELE:          <n> eingesetzt, <m> Marken offen
QUELLENPRÜFUNG:     exit <n>
GLOSSARLÜCKEN:      <begriffe>
URTEIL:             durch | zurück an recherche | zurück an outline
NÄCHSTER SCHRITT:   /recherche-kit:gates
```
