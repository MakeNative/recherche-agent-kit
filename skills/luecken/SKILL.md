---
name: luecken
description: "Sucht über den Gesamtstand nach Lücken und entscheidet, ob eine weitere Runde läuft oder das Dokument fertig ist. Triggers on: /recherche-kit:luecken"
disable-model-invocation: true
---

Du entscheidest, ob noch eine Runde läuft. Das ist die Entscheidung, bei der
man am leichtesten zu früh aufhört — und die am leichtesten endlos wird.

## Ablauf

1. Spawn `luecken-finder` über den Gesamtstand.
2. Lies seinen Bericht und prüfe die Zahlen selbst nach. Verlass dich nicht auf
   seine Zählung, wenn eine Entscheidung daran hängt:

   ```bash
   grep -c '"status":"offen"' claims/*.jsonl
   grep -rn 'beispiel:' kapitel/ | wc -l
   python3 "${CLAUDE_PLUGIN_ROOT}/tools/claims_pruefen.py" --kapitel-text
   ```

3. Entscheide je Befund: nacharbeiten, bewusst offen lassen, oder verwerfen.

## Wann eine weitere Runde läuft

**Ja**, wenn mindestens ein blockierender Befund offen ist: ein Kapitel ohne
Quellendeckung, eine unbelegte Funktionsaussage, ein Widerspruch zwischen
Kapiteln, ein Thema aus der Outline ohne Text.

**Nein**, wenn nur noch Kosmetik offen ist. Dann listest du das Offene
ausdrücklich auf und gibst frei. Eine Runde für Kosmetik erzeugt neue Fehler.

## Bewusst offen lassen

Manches bleibt offen, und das ist in Ordnung, solange es **sichtbar** ist:

- Fragen, die niemand belegen kann. Nach der Zahlen-Policy entweder weglassen
  oder als Einschätzung markieren (S-06)
- Themen, die den Rahmen verlassen. Gehören in einen Ausblick, nicht in ein
  halbes Kapitel
- Werkzeuge, die zu neu sind, um darüber etwas Belastbares zu sagen

Schreib diese Punkte nach `wissen/LUECKEN.md`. Diese Datei ist später die
Grundlage für die zweite Auflage und für das Stand-Datum im Dokument.

## Der Abbruchtest

Erscheint derselbe Befund in zwei Runden unverändert, repariere ihn nicht noch
einmal. Dann liegt er tiefer: in der Gliederung, in der Quellenlage oder in
einer Anforderung, die mit einer anderen kollidiert. Sag das und frag.

## Zum Schluss

```
RUNDE:            <n>
BLOCKIEREND:      <n> — <je Befund und Zielskill>
WICHTIG:          <n>
KOSMETISCH:       <n>
BEWUSST OFFEN:    <liste> → wissen/LUECKEN.md
UNGENUTZT AUS FRISCHE.MD: <veraltete Ratschläge, die Inhalt werden könnten>
WIDERSPRÜCHE:     <kapitelpaare>
ZAHLEN:           <kapitel geschrieben/geplant, aussagen belegt/offen>
URTEIL:           weitere Runde | fertig für /recherche-kit:rendern
```

Bei `fertig` sag ausdrücklich, was offen bleibt. Ein freigegebenes Dokument mit
benannten Lücken ist brauchbar; eines mit stillen Lücken ist es nicht (P-06).
