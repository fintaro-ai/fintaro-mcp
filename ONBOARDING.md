# Fintaro MCP — Onboarding

Material zum Weitergeben an Tester:innen und deren KI-Agenten. Zwei Teile:

1. **Kurz-Zusammenfassung** — für den Menschen, der den MCP einbindet.
2. **Onboarding-Prompt** — copy-paste an einen MCP-fähigen Agenten (Claude Desktop / Claude Code / Cursor …).

> **Verteilung:** Das Paket ist (noch) **nicht auf PyPI** — `uvx fintaro-mcp` allein funktioniert
> daher nicht. Am einfachsten direkt aus dem öffentlichen Repo installieren:
>
> ```text
> uvx --from git+https://github.com/fintaro-ai/fintaro-mcp fintaro-mcp
> ```
>
> Alternativ ein Wheel bauen und die Datei mitschicken:
>
> ```bash
> pip wheel . -w dist --no-deps        # erzeugt dist/fintaro_mcp-<version>-py3-none-any.whl
> ```
>
> Der Tester startet den Server dann mit `uvx --from <pfad>/fintaro_mcp-*.whl fintaro-mcp`
> (uvx löst die Abhängigkeiten `mcp`, `httpx` und `pydantic` automatisch auf). Alternativ: auf PyPI / einen
> privaten Index veröffentlichen, dann greift das README-`uvx fintaro-mcp`.

---

## Teil 1 — Kurz-Zusammenfassung (für den Tester)

**Fintaro MCP — Schnellüberblick**

Der Fintaro MCP-Server verbindet einen KI-Agenten direkt mit deinen Fintaro-Daten. Der Agent kann:

- **Belege hochladen** (`upload_invoice`) — PDF/PNG/JPEG/WebP, max. 25 MB
- **Rechnungen lesen** (`list_invoices`, `get_invoice`) — PII-bereinigte Kurzfassung
- **Banktransaktionen lesen** (`list_transactions`, `list_unmatched`)
- **Monatsabschluss prüfen** (`monatsabschluss_check`) — findet Transaktionen ohne Beleg

**Setup (ca. 5 Min):**

1. `uv` installieren, falls noch nicht vorhanden: <https://docs.astral.sh/uv/getting-started/installation/>
2. Die mitgeschickte `fintaro_mcp-*.whl` ablegen (Pfad merken).
3. In Fintaro unter **Einstellungen → API-Keys** einen Key erstellen. Scopes minimal halten:
   `invoices:read`, `transactions:read` (+ `invoices:write` nur, wenn du Belege hochladen willst).
   Der `ftk_…`-Key wird **nur einmal** angezeigt → sofort kopieren.
4. Key + Wheel-Pfad in den MCP-Client eintragen (Config siehe Teil 2) — oder einfach den
   Onboarding-Prompt aus Teil 2 an deinen Agenten geben.

**Wichtig:** Die Organisation steckt im Key — du musst nirgends eine Org-ID angeben. `get_invoice`
liefert bewusst nur eine schmale Projektion (kein OCR-Text, keine Steuer-IDs), damit
Rechnungsinhalte den Agenten nicht manipulieren können.

---

## Teil 2 — Onboarding-Prompt (an den Agenten geben)

Ersetze `<ABSOLUTER_PFAD_ZUR_WHEEL>` und `<MEIN_ftk_KEY>`, dann den ganzen Block an den Agenten geben:

```text
Du sollst den "Fintaro" MCP-Server einrichten und testen. Folge exakt diesen Schritten:

1. SETUP
   Richte den MCP-Server in meiner Client-Konfiguration ein. Verwende:
     - command: uvx
     - args: ["--from", "<ABSOLUTER_PFAD_ZUR_WHEEL>/fintaro_mcp-0.1.0-py3-none-any.whl", "fintaro-mcp"]
     - env: { "FINTARO_API_KEY": "<MEIN_ftk_KEY>" }

   Beispiel für Claude Code (CLI):
     claude mcp add fintaro \
       --env FINTARO_API_KEY=<MEIN_ftk_KEY> \
       -- uvx --from <ABSOLUTER_PFAD_ZUR_WHEEL>/fintaro_mcp-0.1.0-py3-none-any.whl fintaro-mcp

   Beispiel für Claude Desktop (claude_desktop_config.json):
     {
       "mcpServers": {
         "fintaro": {
           "command": "uvx",
           "args": ["--from", "<ABSOLUTER_PFAD_ZUR_WHEEL>/fintaro_mcp-0.1.0-py3-none-any.whl", "fintaro-mcp"],
           "env": { "FINTARO_API_KEY": "<MEIN_ftk_KEY>" }
         }
       }
     }

2. VERBINDUNG PRÜFEN
   Rufe das Tool `whoami` auf. Zeig mir Organisation, Scopes und Ablaufdatum.
   Wenn das fehlschlägt: prüfe, ob der ftk_-Key korrekt gesetzt ist und die nötigen
   Scopes hat — und brich hier ab.

3. DATEN LESEN
   - Rufe `list_invoices` auf und sag mir, wie viele Rechnungen es gibt.
   - Rufe `list_transactions` auf und nenne mir die Gesamtzahl (Feld "total").
   - Falls es Rechnungen gibt, ruf `get_invoice` für die neueste auf und zeig die Kurzfassung.

4. MONATSABSCHLUSS-DEMO
   Nutze den Prompt `monatsabschluss_check` und liste die Transaktionen auf,
   die noch keinen Beleg haben (unmatched) — pro Eintrag Datum, Betrag, Gegenseite.

5. (OPTIONAL) UPLOAD
   Nur wenn der Key den Scope `invoices:write` hat und ich es ausdrücklich sage:
   lade mit `upload_invoice` eine lokale Beleg-Datei hoch und bestätige die invoice_id.

Fasse am Ende in 3-4 Sätzen zusammen, was funktioniert hat und was nicht.
```

---

## Tools im Überblick

| Tool | Funktion | Scope |
| --- | --- | --- |
| `whoami` | Organisation, Scopes und Ablauf des Keys anzeigen | — |
| `upload_invoice(file_path)` | Lokalen Beleg hochladen (PDF/PNG/JPEG/WebP, ≤ 25 MB) | `invoices:write` |
| `get_invoice(invoice_id)` | Schmale, PII-freie Zusammenfassung einer Rechnung | `invoices:read` |
| `list_invoices()` | PII-freie Zusammenfassungen aller Rechnungen | `invoices:read` |
| `list_transactions()` | Banktransaktionen der Organisation | `transactions:read` |
| `list_unmatched()` | Transaktionen, denen noch ein Beleg fehlt | `transactions:read` |

Prompt: `monatsabschluss_check` — geführte Vor-Abschluss-Prüfung über `list_unmatched`.
