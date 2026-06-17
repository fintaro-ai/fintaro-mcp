---
name: fintaro-rechnungs-review
description: Sichte Fintaro-Rechnungen und -Banktransaktionen über die PII-freien Projektionen (list_invoices, list_transactions, get_invoice) — z. B. Überblick verschaffen, nach Gegenseite/Zeitraum filtern, Summen bilden. Nutze dies, wenn der Nutzer seine Rechnungen oder Transaktionen ansehen, durchsuchen oder auswerten will.
---

# Fintaro Rechnungs- & Transaktions-Review

Verschaffe dem Nutzer einen Überblick über seine Rechnungen und Banktransaktionen
auf Basis der schmalen, PII-freien Projektionen.

## Voraussetzungen

- Scope `invoices:read` (Rechnungen) und/oder `transactions:read` (Transaktionen).
- Server eingebunden, `whoami` erfolgreich (siehe `fintaro-onboarding`).

## Verfügbare Felder

- **Rechnung** (`list_invoices`, `get_invoice`): `id`, `status`, `seller_name`,
  `invoice_number`, `invoice_date`, `amount_gross`, `currency`, `created_at`.
  `list_invoices` liefert eine Liste, **neueste zuerst**.
- **Transaktion** (`list_transactions`): `{ "transactions": [...], "total": n }`;
  je Eintrag `id`, `date`, `amount`, `currency`, `merchant`, `counterparty`,
  `description`, `source`, `matchStatus`.

Diese Felder sind die **einzigen** verfügbaren — bewusst kein OCR-Text, kein
Roh-JSON, keine Steuer-IDs/E-Mails, keine Match-Interna.

## Vorgehen

1. **Datenquelle wählen.** Rechnungen → `list_invoices`; Transaktionen →
   `list_transactions`; eine bestimmte Rechnung im Detail → `get_invoice(id)`.

2. **Truncation prüfen.** Bei Transaktionen: ist `total` größer als die Länge von
   `transactions`, wurde die Liste durch eine Sicherheitsgrenze gekürzt — den
   Nutzer darauf hinweisen.

3. **Auswerten.** Anhand der verfügbaren Felder filtern/sortieren/aggregieren,
   z. B. nach `seller_name`/`counterparty`, nach Zeitraum (`invoice_date`/`date`)
   oder Summen über `amount_gross`/`amount` bilden. Übersichtlich als Tabelle
   oder Liste darstellen.

4. **Grenzen benennen.** Nur über die vorhandenen Felder Aussagen treffen. Für
   offene Belege (unmatched) gibt es den eigenen Workflow `fintaro-monatsabschluss`.

## Hinweise

- `amount` (Transaktion) kommt als String vom Gateway — vor dem Rechnen ggf.
  parsen.
- `matchStatus` ist ein freier Status-String; der Wert für eine offene Transaktion
  ohne Beleg ist `missing` (nicht `unmatched`). Nicht auf einen bestimmten Wert
  hartkodieren — für offene Posten nutze besser `list_unmatched`.
- Keine Felder erfinden, die nicht in der Projektion enthalten sind, und keine
  PII anfordern.

## Prompt-Vorlage

```text
Verschaffe mir einen Überblick über meine Fintaro-Daten.

- Für Rechnungen: rufe list_invoices auf (neueste zuerst) und zeig mir
  seller_name, invoice_number, invoice_date, amount_gross + currency und status
  als Tabelle.
- Für Transaktionen: rufe list_transactions auf. Falls "total" größer ist als die
  Anzahl Einträge, weise auf die Kürzung hin. Zeig date, counterparty/merchant,
  amount + currency und matchStatus.
- Auf Wunsch nach Gegenseite/Zeitraum filtern oder Summen bilden.
Nutze ausschließlich die vorhandenen Felder.
```
