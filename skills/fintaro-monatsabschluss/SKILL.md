---
name: fintaro-monatsabschluss
description: Geführte Vor-Abschluss-Prüfung (Monatsabschluss) für Fintaro — findet über list_unmatched alle Banktransaktionen ohne Beleg und fasst je offener Transaktion Datum, Betrag und Gegenseite zusammen. Nutze dies vor einem Monats-/Quartalsabschluss, beim Aufräumen offener Belege, oder wenn jemand fragt "welche Belege fehlen noch?".
---

# Fintaro Monatsabschluss-Review

Hilf dem Nutzer, den Monat sauber abzuschließen: zeige, welche Transaktionen
noch keinen Beleg haben, damit sie nachgereicht werden können. Dies entspricht
dem MCP-Prompt `monatsabschluss_check`.

## Voraussetzungen

- Scope `transactions:read`.
- Server eingebunden, `whoami` erfolgreich (siehe `fintaro-onboarding`).

## Vorgehen

1. **Offene Posten holen.** Tool `list_unmatched` aufrufen. Es liefert
   `{ "transactions": [...], "total": n }`. Jede Transaktion ist eine schmale,
   PII-freie Projektion mit u. a. `date`, `amount`, `currency`, `merchant`,
   `counterparty`, `description`, `matchStatus`.

2. **Truncation prüfen.** Ist `total` größer als die Länge von `transactions`,
   wurde die Liste durch eine Sicherheitsgrenze gekürzt — den Nutzer darauf
   hinweisen, dass nicht alle offenen Posten gezeigt werden.

3. **Fehlende Belege zusammenfassen.** Pro offener Transaktion **Datum, Betrag
   (mit Währung) und Gegenseite** (`counterparty` bzw. `merchant`) auflisten,
   sortiert nach Datum, damit der Nutzer die Belege gezielt nachreichen kann.
   Optional: nach Gegenseite gruppieren oder die Gesamtsumme nennen.

4. **Grenze benennen.** Darauf hinweisen, dass eine **automatische Prüfung des
   Export-Status (BMD/UVA)** noch nicht verfügbar ist und später kommt.

5. **Abschluss-Empfehlung.** Den Monat erst abschließen, wenn keine
   Transaktionen mehr `unmatched` sind bzw. der Nutzer die fehlenden Belege
   ausdrücklich bestätigt hat.

## Hinweise

- `list_unmatched` filtert die offenen Posten bereits serverseitig — du musst
  `matchStatus` nicht selbst prüfen (der Wert offener Zeilen ist `missing`).
- Nur die dokumentierten Projektionsfelder verwenden; keine Match-Interna,
  Steuer-IDs oder Roh-OCR anfordern oder erfinden.
- Belege hochladen ist ein eigener Workflow → siehe `fintaro-belege-upload`.

## Prompt-Vorlage

```text
Du bist Buchhaltungs-Assistent für den Monatsabschluss in Fintaro.

1. Rufe `list_unmatched` auf (Transaktionen ohne Beleg).
2. Falls "total" größer ist als die Anzahl zurückgegebener Transaktionen,
   weise darauf hin, dass die Liste gekürzt wurde.
3. Liste pro offener Transaktion Datum, Betrag (mit Währung) und Gegenseite,
   nach Datum sortiert, damit ich die fehlenden Belege nachreichen kann.
4. Weise darauf hin, dass eine automatische Prüfung des Export-Status (BMD/UVA)
   noch nicht verfügbar ist.
5. Empfiehl, den Monat erst abzuschließen, wenn nichts mehr unmatched ist.
```
