# Fintaro Agent Skills

Portable, copy-paste-fähige Skill-Definitionen, die einem MCP-fähigen Agenten
echte Fintaro-Workflows über den [`fintaro-mcp`](../README.md)-Server beibringen.

Jeder Ordner enthält eine `SKILL.md` im üblichen Skill-Format (YAML-Frontmatter
mit `name` + `description`, danach die Instruktionen). Du kannst sie auf zwei
Arten verwenden:

1. **Als Agent-Skill** — z. B. in Claude Code unter `~/.claude/skills/<name>/`
   oder im Projekt unter `.claude/skills/<name>/` ablegen. Der Agent lädt sie
   anhand der `description` automatisch, wenn sie zum Anliegen passt.
2. **Als Prompt-Vorlage** — den Abschnitt **Prompt-Vorlage** aus der `SKILL.md`
   kopieren und direkt an einen beliebigen MCP-fähigen Agenten geben.

> Voraussetzung für alle Skills außer dem Onboarding: Der `fintaro-mcp`-Server
> ist eingebunden und ein gültiger `ftk_`-Key ist gesetzt. Wie das geht, steht
> in [`fintaro-onboarding`](fintaro-onboarding/SKILL.md).

## Skills

| Skill | Zweck | Benötigte Scopes |
| --- | --- | --- |
| [`fintaro-onboarding`](fintaro-onboarding/SKILL.md) | Server einbinden, Key minten, Verbindung prüfen | — |
| [`fintaro-monatsabschluss`](fintaro-monatsabschluss/SKILL.md) | Vor dem Abschluss fehlende Belege je Transaktion auflisten | `transactions:read` |
| [`fintaro-belege-upload`](fintaro-belege-upload/SKILL.md) | Beleg hochladen und Verarbeitung verifizieren | `invoices:write`, `invoices:read` |
| [`fintaro-rechnungs-review`](fintaro-rechnungs-review/SKILL.md) | Rechnungen & Transaktionen sichten (PII-frei) | `invoices:read`, `transactions:read` |

## Verfügbare MCP-Tools (Referenz)

| Tool | Funktion | Scope |
| --- | --- | --- |
| `whoami` | Organisation, Scopes und Ablauf des Keys anzeigen | — |
| `upload_invoice(file_path)` | Lokalen Beleg hochladen (PDF/PNG/JPEG/WebP, ≤ 25 MB) | `invoices:write` |
| `get_invoice(invoice_id)` | Schmale, PII-freie Zusammenfassung einer Rechnung | `invoices:read` |
| `list_invoices()` | PII-freie Zusammenfassungen aller Rechnungen (neueste zuerst) | `invoices:read` |
| `list_transactions()` | Banktransaktionen der Organisation (`{transactions, total}`) | `transactions:read` |
| `list_unmatched()` | Transaktionen ohne Beleg (`{transactions, total}`) | `transactions:read` |

Prompt: `monatsabschluss_check` — geführte Vor-Abschluss-Prüfung über `list_unmatched`.

## Sicherheit

Die Lese-Tools liefern bewusst **schmale, PII-freie Projektionen** (kein
OCR-Text, kein Roh-JSON, keine Steuer-IDs/E-Mails, keine Match-Interna). Skills
sollen nur diese dokumentierten Felder verwenden und keine sensiblen Daten
anfordern oder erfinden.
