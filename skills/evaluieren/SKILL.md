---
name: evaluieren
description: "Bewertet die Pipeline selbst statt des Inhalts: welche Agenten liefern brauchbar, welche Regel greift nicht, welcher Schritt erzeugt Nacharbeit. Triggers on: /recherche-kit:evaluieren [durchlauf-beschreibung]"
disable-model-invocation: true
argument-hint: "[was gerade gelaufen ist]"
---

Du prüfst das Werkzeug, nicht das Werkstück. Nach einem Durchlauf ist der
Blick darauf am klarsten, und später erinnert sich niemand mehr.

Diese Skill ändert die Pipeline im Plugin-Repo. Das ist ein anderer Ort als das
Dokumentprojekt — sag immer, in welchem Repo du schreibst.

## Woran du die Pipeline misst

**Nacharbeitsquote.** Wie viele Kapitel mussten zurück, und wegen was? Gehen
Kapitel wegen fehlender Aussagen zurück, liegt der Fehler in `recherche`, nicht
im `writer`.

**Blindgänger.** Welcher Agent hat etwas geliefert, das niemand benutzt hat?
Entweder ist sein Auftrag falsch geschnitten, oder er ist überflüssig.

**Stille Regeln.** Welche Regel aus dem Regelwerk hat in diesem Durchlauf nie
gegriffen? Zwei Möglichkeiten: sie ist unnötig, oder sie wird umgangen. Prüfe,
welche es ist — eine Regel, die niemand verletzt, ist verdächtig.

**Rauschen.** Welcher Befundtyp war meist Fehlalarm? Ein Gate mit vielen
Fehlalarmen wird irgendwann übergangen und ist dann schlechter als keins.

**Wo der Nutzer eingegriffen hat.** Jede Stelle, an der er korrigieren musste,
ist eine Stelle, an der ein Prompt oder eine Schwelle falsch ist. Das ist das
wertvollste Signal und steht nirgends in einem Bericht.

**Falsche Rollenverteilung.** Hat ein Agent entschieden, was ein Skill
entscheiden müsste (P-01, P-02)? Erkennbar daran, dass sein Bericht eine
Arbeitsliste statt Befunde enthält.

## Vorgehen

1. Spawn `lauf-auswerter`. Er liest `.claude/recherche-log/lauf.jsonl` und die
   Gate-Berichte und liefert Befunde mit Zahlen.
2. Frag den Nutzer, wo er eingegriffen hat und was ihn genervt hat. Das ist das
   wertvollste Signal und steht in **keinem** Protokoll.
3. Entscheide, welche Befunde zu Änderungen führen. Der Agent urteilt über die
   Pipeline, du entscheidest über Eingriffe (P-02).
4. Führ die Änderungen aus und sag, in welchem Repo.

Fehlt das Protokoll oder ist es fast leer, sag das und bewerte **nicht** aus
dem Gedächtnis. Eine Bewertung ohne Daten erzeugt Änderungen, deren Wirkung
niemand messen kann. Dann ist die richtige Änderung: einen Protokolleintrag
ergänzen und nach dem nächsten Durchlauf erneut bewerten.

## Was du änderst, und was nicht

Ändern: Prompts von Agenten, Schwellen in `stil.json`, Schärfe der Muster in
den Skripten, Reihenfolge der Schritte in einer Skill.

Nicht ändern ohne Rückfrage: das Regelwerk, die Stufeneinteilung, die Trennung
Skill gegen Agent. Das sind die Grundentscheidungen; wer sie leise verschiebt,
verliert den Grund, aus dem sie getroffen wurden.

Niemals: eine Schwelle lockern, weil zu viele Befunde kommen. Erst prüfen, ob
die Befunde stimmen. Viele richtige Befunde sind ein Inhaltsproblem, nicht ein
Werkzeugproblem.

## Memory der Agenten pflegen

Fünf Agenten haben `memory: project` und lesen
`.claude/agent-memory/recherche-kit-<name>/`. Hierher gehört, was über einen
Lauf hinaus gilt — nicht Einzelfälle:

- `kartenschreiber`: welche Kartenfelder regelmäßig zu lang wurden
- `frische-pruefer`: Begriffe, unter denen die offizielle Doku etwas anders
  benennt als Drittquellen
- `writer`: wiederkehrende Stilbefunde, die er selbst vermeiden kann
- `verdichter`: Streichungen, die zurückgenommen werden mussten
- `laien-leser`: nichts. Sein Memory bleibt leer — ein Laie, der sich etwas
  merkt, ist kein Laie mehr und verliert seine Messfähigkeit

Trag nur ein, was aus dem Protokoll belegt ist. Memory, das aus Vermutung
gefüllt wird, verschlechtert den Agenten dauerhaft und lässt sich später nicht
mehr von Erfahrung unterscheiden.

## Ergebnis

```
DATENLAGE:          <n> Protokollzeilen, Zeitraum <…>  |  kein Protokoll
BEFUNDE DES AGENTEN: <Kurzfassung je Auswertung>
NUTZEREINGRIFFE:    <stellen — nicht protokollierbar, erfragt>

ÄNDERUNGEN AUSGEFÜHRT
1. <repo/datei> — <änderung> — <welche Zahl sie begründet>

MEMORY GEPFLEGT
<agent — was eingetragen wurde, mit Belegzeile aus dem Protokoll>

NICHT GEÄNDERT, OBWOHL AUFFÄLLIG
<befund — warum nicht>

RÜCKFRAGEN
<was du nicht allein entscheiden willst>

PROTOKOLLLÜCKEN
<was fehlt, um beim nächsten Mal besser bewerten zu können>
```
