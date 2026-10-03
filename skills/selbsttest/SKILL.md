---
name: selbsttest
description: "Fährt die ganze Strecke an einer Mini-Quelle in einem Wegwerf-Projekt und prüft, dass die Gates auch ablehnen, was sie ablehnen sollen. Vor dem ersten echten Durchlauf und nach jeder Änderung an den Skripten. Triggers on: /recherche-kit:selbsttest [--offline]"
disable-model-invocation: true
argument-hint: "[--offline]"
---

Du prüfst, ob die Pipeline funktioniert, bevor sie auf echte Quellen losgeht.

Der Test prüft nicht nur, dass die Skripte durchlaufen, sondern dass sie
**ablehnen, was sie ablehnen sollen**. Ein Gate, das alles durchlässt, ist
schlimmer als keins, weil es Sicherheit vortäuscht.

## Skriptteil

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/selbsttest.py"
# ohne Netz:
python3 "${CLAUDE_PLUGIN_ROOT}/tools/selbsttest.py" --offline
# zum Nachsehen:
python3 "${CLAUDE_PLUGIN_ROOT}/tools/selbsttest.py" --behalten
```

Geprüft wird: Quelle holen, chunken, indexieren, Indexgrenze, wörtliches Zitat
akzeptiert, erfundenes Zitat abgelehnt (Q-03), Funktionsaussage aus Stufe 2
abgelehnt (Q-01), überholte Quelle abgelehnt (Q-04), Zahl ohne Fußnote gemeldet,
Stilgate meldet und besteht.

Läuft eine Erwartung nicht durch, repariere das Skript, **nicht** den Test. Ein
Test, der an die Umsetzung angepasst wird, prüft nichts mehr.

## Agententeil

Die Skripte sind damit abgedeckt, die Agenten nicht. Fahre zusätzlich einen
Minimalfall mit echten Agenten, denn deren Ausgabeform ist die häufigste
Fehlerquelle:

1. Nimm eine kleine Stufe-2-Quelle auf und spawn den `kartenschreiber`. Prüfe:
   hält er die Kartenform ein, sind die Zitate **wörtlich**, hat er
   „Nicht brauchbar für" gefüllt?
2. Spawn einen `frische-pruefer` auf eine seiner Kernaussagen. Prüfe: nennt er
   `GESUCHT IN`? Ohne diese Zeile ist sein Negativurteil wertlos.
3. Prüfe, ob der `kartenschreiber` wirklich nicht geschrieben hat. Liegt eine
   `CARD.md` da, die er selbst angelegt hat, ist P-03 verletzt und die
   Werkzeugrechte im Agenten sind falsch gesetzt.

Der dritte Punkt ist der wichtigste. Rechte, die nur im Prompt stehen und nicht
im Frontmatter, halten nicht.

## Zum Schluss

```
SKRIPTTEST:   <n> von <m> Erwartungen erfüllt
  nicht erfüllt: <liste>
AGENTENTEST:
  kartenformtreue:    ja | nein — <was abwich>
  zitate wörtlich:    ja | nein
  GESUCHT IN gesetzt: ja | nein
  P-03 gehalten:      ja | nein
URTEIL:       bereit für den echten Durchlauf | reparieren: <was>
```

Gib die Pipeline nicht frei, wenn der Agententeil auffällt. Ein Agent, der seine
Ausgabeform nicht hält, bricht später mitten in einem Lauf über zwanzig Kapitel.
