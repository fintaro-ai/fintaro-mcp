# fintaro-mcp

A [Model Context Protocol](https://modelcontextprotocol.io) server that lets an
MCP-capable agent (Claude Desktop, etc.) read your Fintaro invoices and
transactions and upload receipts — over the Fintaro API gateway, authenticated
with a scoped, bring-your-own `ftk_` API key.

The server is **read-mostly and PII-safe by construction**: `get_invoice` returns
a narrow projection that never includes raw OCR text, raw extraction JSON, or
tax-IDs/emails, so attacker-controlled invoice content cannot be injected into
the agent's context.

## Tools

| Tool | What it does | Required scope |
| --- | --- | --- |
| `whoami` | Show the organization, scopes, and expiry the key is bound to | — |
| `upload_invoice(file_path)` | Upload a local PDF/PNG/JPEG/WebP receipt (≤ 25 MB) | `invoices:write` |
| `get_invoice(invoice_id)` | Narrow, PII-free summary of one invoice | `invoices:read` |
| `list_invoices()` | Narrow, PII-free summaries of the org's invoices | `invoices:read` |
| `list_transactions()` | The org's bank transactions | `transactions:read` |
| `list_unmatched()` | Transactions still missing a receipt | `transactions:read` |

Prompt: `monatsabschluss_check` — a guided pre-close review that uses
`list_unmatched` to find transactions still without a receipt.

## Agent skills

Ready-to-use, copy-paste skill definitions that teach an MCP-capable agent real
Fintaro workflows over these tools live in [`skills/`](skills/README.md) —
onboarding/setup, the pre-close (Monatsabschluss) review, receipt upload, and an
invoice/transaction review. Each is a `SKILL.md` usable as an agent skill or as a
standalone prompt template.

## Mint an API key

1. In Fintaro, open **Settings → API keys** and create a key.
2. Grant the **minimum** scopes for what you need:
   - read-only review: `invoices:read`, `transactions:read`
   - plus receipt upload: add `invoices:write`
3. Copy the `ftk_…` key once (it is shown only at creation) and store it in your
   MCP client's environment. The organization is derived from the key — there is
   no org parameter to pass.

## Configuration

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `FINTARO_API_KEY` | yes | — | the `ftk_` key |
| `FINTARO_BASE_URL` | no | `https://api.fintaro.ai/api/v1` | must be `https://` |

The server rejects any tool call without `FINTARO_API_KEY` or with a non-`https`
base URL (the configuration is validated on the first tool invocation).

## Client config (`uvx`)

```json
{
  "mcpServers": {
    "fintaro": {
      "command": "uvx",
      "args": ["fintaro-mcp"],
      "env": {
        "FINTARO_API_KEY": "ftk_your_scoped_key"
      }
    }
  }
}
```

## Onboarding a tester

See [`ONBOARDING.md`](ONBOARDING.md) for a ready-to-send tester summary and a copy-paste
onboarding prompt for an MCP-capable agent. The package is not on PyPI yet, so `uvx fintaro-mcp`
does not resolve on its own. Until it is published, install straight from this repo:

```json
{
  "mcpServers": {
    "fintaro": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/fintaro-ai/fintaro-mcp", "fintaro-mcp"],
      "env": { "FINTARO_API_KEY": "ftk_your_scoped_key" }
    }
  }
}
```

Alternatively distribute a built wheel (`pip wheel . -w dist --no-deps`) and configure the client
with `uvx --from <path>/fintaro_mcp-*.whl fintaro-mcp`.

## Development

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest -v
```
