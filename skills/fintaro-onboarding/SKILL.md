---
name: fintaro-onboarding
description: Richte den Fintaro MCP-Server ein und prüfe die Verbindung — einbinden via uvx (Git oder Wheel), einen scoped ftk_-Key minten und mit whoami testen. Nutze dies beim ersten Setup von Fintaro / fintaro-mcp, beim Verbinden eines Agenten mit Fintaro, oder wenn whoami/Verbindung fehlschlägt.
---

# Fintaro Onboarding & Setup

Bring einen MCP-fähigen Agenten mit Fintaro-Daten zusammen: Server einbinden,
einen scoped `ftk_`-Key minten und die Verbindung verifizieren.

## Voraussetzungen

- `uv` ist installiert (<https://docs.astral.sh/uv/getting-started/installation/>).
- Ein Fintaro-Account mit Zugriff auf **Einstellungen → API-Keys**.

## Vorgehen

1. **Key minten.** In Fintaro unter **Einstellungen → API-Keys** einen Key
   erstellen. Scopes **minimal** halten:
   - reines Lesen/Review: `invoices:read`, `transactions:read`
   - zusätzlich Belege hochladen: `invoices:write`

   Der `ftk_…`-Key wird **nur einmal** angezeigt → sofort sicher kopieren.

2. **Server einbinden.** Bevorzugt direkt aus dem öffentlichen Repo (uvx löst
   die Abhängigkeiten automatisch auf):

   ```json
   {
     "mcpServers": {
       "fintaro": {
         "command": "uvx",
         "args": ["--from", "git+https://github.com/fintaro-ai/fintaro-mcp", "fintaro-mcp"],
         "env": { "FINTARO_API_KEY": "ftk_dein_scoped_key" }
       }
     }
   }
   ```

   Claude Code (CLI):

   ```text
   claude mcp add fintaro \
     --env FINTARO_API_KEY=ftk_dein_scoped_key \
     -- uvx --from git+https://github.com/fintaro-ai/fintaro-mcp fintaro-mcp
   ```

   Alternativ aus einem mitgelieferten Wheel:
   `uvx --from <pfad>/fintaro_mcp-*.whl fintaro-mcp`.

3. **Verbindung prüfen.** Tool `whoami` aufrufen und Organisation, Scopes und
   Ablaufdatum des Keys zeigen. Schlägt das fehl: prüfen, ob `FINTARO_API_KEY`
   korrekt gesetzt ist und die nötigen Scopes hat — und hier abbrechen.

4. **Kurzer Lesetest.** Wenn `invoices:read`/`transactions:read` vergeben sind:
   `list_invoices` und `list_transactions` aufrufen und die Anzahl melden
   (bei Transaktionen das Feld `total`).

## Hinweise

- Die Organisation steckt im Key — es gibt **keinen** Org-Parameter.
- `FINTARO_BASE_URL` ist optional (Default `https://api.fintaro.ai/api/v1`) und
  muss `https://` sein. Die Konfiguration wird beim ersten Tool-Aufruf geprüft.

## Prompt-Vorlage

```text
Du sollst den "Fintaro" MCP-Server einrichten und testen. Ich habe einen
ftk_-Key (Scopes: invoices:read, transactions:read; optional invoices:write).

1. Binde den Server ein mit:
   command: uvx
   args: ["--from", "git+https://github.com/fintaro-ai/fintaro-mcp", "fintaro-mcp"]
   env:  { "FINTARO_API_KEY": "<MEIN_ftk_KEY>" }
2. Rufe `whoami` auf und zeig mir Organisation, Scopes und Ablaufdatum.
   Schlägt es fehl, prüfe den Key und brich ab.
3. Rufe `list_invoices` und `list_transactions` auf und nenne mir die Anzahl
   (bei Transaktionen das Feld "total").
Fasse am Ende in 2-3 Sätzen zusammen, was funktioniert hat.
```
