---
name: fintaro-belege-upload
description: Lade einen lokalen Beleg (Rechnung/Quittung als PDF/PNG/JPEG/WebP) nach Fintaro hoch und verifiziere, dass die Verarbeitung gestartet ist. Nutze dies, wenn der Nutzer eine Rechnung/Quittung/einen Beleg zu Fintaro hinzufügen, hochladen oder erfassen will.
---

# Fintaro Belege-Upload

Lade eine lokale Beleg-Datei nach Fintaro hoch und bestätige, dass sie zur
Verarbeitung angenommen wurde.

## Voraussetzungen

- Scope `invoices:write` (für den Upload) und `invoices:read` (zum Verifizieren).
- Server eingebunden, `whoami` erfolgreich (siehe `fintaro-onboarding`).
- Die Datei liegt **lokal** vor; Format **PDF/PNG/JPEG/WebP**, Größe **≤ 25 MB**.

## Vorgehen

1. **Scope bestätigen.** Sicherstellen, dass der Key `invoices:write` hat (bei
   Unsicherheit `whoami`). Fehlt der Scope: abbrechen und den Nutzer bitten,
   einen Key mit `invoices:write` zu minten.

2. **Hochladen.** Tool `upload_invoice(file_path=<absoluter Pfad>)` aufrufen.
   Rückgabe: `{ "invoice_id": <id>, "status": "processing", "deduplicated": <bool> }`.
   - `status` ist direkt nach dem Upload immer `processing` — die Extraktion
     läuft asynchron im Hintergrund.
   - `deduplicated: true` bedeutet, dass Fintaro die Datei als Duplikat eines
     bereits vorhandenen Belegs erkannt hat; dann den Nutzer informieren.

3. **Verifizieren.** Die zurückgegebene `invoice_id` über `get_invoice(invoice_id)`
   abrufen und die schmale Zusammenfassung zeigen (`status`, `seller_name`,
   `invoice_number`, `invoice_date`, `amount_gross`, `currency`). Solange die
   Extraktion läuft, können einzelne Felder noch leer sein — das ist erwartbar.
   Alternativ `list_invoices` aufrufen (neueste zuerst) und prüfen, dass der neue
   Beleg oben auftaucht.

4. **Ergebnis melden.** `invoice_id`, aktueller `status` und ggf. Duplikat-Hinweis
   knapp zusammenfassen.

## Hinweise

- Pro Aufruf wird **eine** Datei hochgeladen. Bei mehreren Belegen den Upload je
  Datei wiederholen.
- Niemals erfundene `file_path`-Werte verwenden — nur tatsächlich vorhandene,
  vom Nutzer genannte Dateien.
- `get_invoice`/`list_invoices` liefern bewusst nur eine PII-freie Kurzfassung
  (kein OCR-Text, keine Steuer-IDs).

## Prompt-Vorlage

```text
Lade einen Beleg nach Fintaro hoch und verifiziere ihn.

Datei: <ABSOLUTER_PFAD_ZUR_DATEI>  (PDF/PNG/JPEG/WebP, ≤ 25 MB)

1. Stelle sicher, dass mein Key den Scope invoices:write hat (sonst abbrechen).
2. Rufe upload_invoice(file_path="<ABSOLUTER_PFAD_ZUR_DATEI>") auf und nenne mir
   invoice_id, status und ob es als Duplikat erkannt wurde (deduplicated).
3. Rufe get_invoice(invoice_id) für die zurückgegebene ID auf und zeig mir die
   Kurzfassung. Leere Felder sind ok, solange die Verarbeitung noch läuft.
4. Fasse das Ergebnis in 1-2 Sätzen zusammen.
```
