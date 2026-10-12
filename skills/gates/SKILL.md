---
name: gates
description: "Fährt die drei Gates über die fertigen Kapitel — Quellen, Verständnis, Stil — und macht aus den Befunden eine priorisierte Arbeitsliste. Triggers on: /recherche-kit:gates [kapitel-slug ...]"
disable-model-invocation: true
argument-hint: "[kapitel-slug ...]"
---

Du prüfst fertige Kapitel und entscheidest, was nachgearbeitet wird. Die
Berichte sind Arbeitslisten, keine Noten.

## Gate 1 — Quellen

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/claims_pruefen.py" --kapitel-text
```

Bei Befunden: spawn `quellen-pruefer` mit dem Bericht. Er beurteilt die
Grenzfälle und liefert Korrekturen.

Trage die Korrekturen selbst ein — er darf nicht schreiben (P-03). Bei
`korrigierbar` die exakte Zeichenfolge aus seinem Bericht übernehmen, nicht
abtippen.

Q-01- und Q-04-Befunde sind keine Grenzfälle: die Aussage wird neu belegt oder
entfällt (S-06). Das geht an `recherche`, nicht an den Prüfer.

Beachte seinen Block `ZUSÄTZLICH GEFUNDEN` — Zitate, die existieren, aber die
Aussage nicht tragen. Die findet kein Skript, und sie sind der ernsteste
Befund überhaupt.

## Gate 2 — Verständnis

Spawn `laien-leser`, **einen je Kapitel, parallel**. Jeder liest nur sein
Kapitel; wer mehrere liest, lernt dazu und verliert die Messfähigkeit.

Der wichtigste Teil seines Berichts ist `VERSTANDEN HABE ICH`. Vergleich das mit
dem Kernsatz aus `OUTLINE.md`. Weicht es ab, ist das Kapitel gescheitert, auch
ohne Einzelbefund — dann braucht es eine andere Struktur, nicht eine bessere
Formulierung.

Behebung ausschließlich über Beispiele oder Analogien (S-05). Wenn du dich dabei
erwischst, eine Erklärung zu verlängern, spawn stattdessen den `beispiel-agent`.

## Gate 3 — Stil

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/stil_pruefen.py"
```

S-01 und S-02 gehen an den `verdichter`. S-03 sammelst du für das Glossar.
S-04 geht an den `beispiel-agent`.

## Wenn ein Agent stirbt

Ein Agent, der ohne vollständigen Bericht endet, zählt nie als „nichts
gefunden" (P-07). Prüf jeden Bericht auf seine Pflichtblöcke, starte einmal neu
mit dem Hinweis, knapp zu bleiben, und melde beim zweiten Fehlschlag den Auftrag
als unerledigt — mit Quellen-ID oder Kapitel, damit er nicht verschwindet.

## Priorisieren

Nicht alles gleich wichtig behandeln. In dieser Reihenfolge:

1. **Zitat trägt die Aussage nicht** — eine falsche Behauptung mit Fußnote ist
   schlimmer als eine ohne
2. **Q-01, Q-04** — unbelegte Funktionsaussagen
3. **Laien-Gate: Kapitel falsch verstanden** — Strukturmangel
4. **Laien-Gate: Ausstiegspunkt** — dort hört der Leser auf
5. **Q-03, K-05** — korrigierbare Belege
6. **S-04** — fehlende Beispiele
7. **S-01, S-02** — Verdichtung
8. **S-03** — Glossar, einmal am Ende

## Runden

Betroffene Kapitel gehen zurück an `kapitel`. Danach die Gates erneut, aber nur
für die geänderten Kapitel.

Wiederholen, bis keine Befunde der Stufen 1 bis 4 mehr auftreten. Stufen 5 bis 8
dürfen in einer letzten Runde gesammelt behoben werden.

Erscheint ein Befund in zwei Runden hintereinander unverändert, hör auf ihn zu
reparieren und sag es. Dann ist er kein Textproblem, sondern ein Problem der
Claim-Liste oder der Gliederung.

## Zum Schluss

```
GEPRÜFT:          <n> Kapitel
GATE 1 QUELLEN:   <n> Befunde — <m> korrigiert, <k> an recherche
  davon „Zitat trägt nicht": <n>
GATE 2 VERSTÄNDNIS: <n> Befunde — <m> Kapitel falsch verstanden
  Ausstiegspunkte: <kapitel mit Stelle>
GATE 3 STIL:      <n> Befunde nach Regel
ARBEITSLISTE:     <priorisiert, je Kapitel>
RUNDE:            <n> — <weitere nötig | fertig>
NÄCHSTER SCHRITT: /recherche-kit:kapitel <slugs> oder /recherche-kit:luecken
```
