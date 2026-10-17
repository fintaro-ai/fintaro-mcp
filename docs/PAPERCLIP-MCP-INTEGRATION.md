# Paperclip ↔ Fintaro MCP: minimierte Finanzwerkzeuge

**Stand 17.10.2026: Dokumentationsvorschlag, keine automatische Verbindung.** [Übergreifende Architektur](https://github.com/servas-ai/paperclip-fullstack-agent-swarm/pull/1).

## Was dieses Repo bereitstellt
Die hier implementierten `whoami`, `list_invoices`, `get_invoice`, `list_transactions`, `list_unmatched` und `upload_invoice` sind **Fintaro-Fachwerkzeuge**; der Server soll kein universelles Memory-Backend werden.

## Sicherheitsvertrag für Paperclip
- `ftk_`-Key/Organisation/Scopes am Fintaro-Gateway prüfen; Client kann keine andere `org_id` als die vom Key abgeleitete erzwingen.
- Standardmäßig **nur lesen**. `upload_invoice` separat mit `invoices:write` sowie explizitem Nutzerauftrag/Freigabe; kein Auto-Upload als Nebenwirkung einer Wissensabfrage.
- Narrow PII-safe Projektionen von `get_invoice` beibehalten. OCR-Rohtext, Prompt-Injection-Inhalt, Bankgeheimnisse oder API-Keys **nicht** in Hindsight, Onyx oder Paperclip-Tasks spiegeln.
- `trace_id` + interne Task-/Run-ID für Audit, jedoch niemals Token-/Customer-Daten in Audit-Logs.
- MCP-Verbindung über berechtigten Principal mit kontrollierter Identität herstellen. Hindsight/Onyx sind **separate** spezialisierte Endpoints; keine Git-Submodule notwendig.

## Testfälle
Key ohne `invoices:write` darf nicht hochladen; fremde Org muss 403/404 ergeben; Prompt-Injection im Rechnungsnamen darf nicht Tool-Policy verändern; Secret-Redaktion in Logs; Read-only-Test darf unveränderte Finance-Daten hinterlassen.

Siehe [README](../README.md) und [Onboarding](../ONBOARDING.md).
