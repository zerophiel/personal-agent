# Assumption spikes (Hermes v0.22.5, digest sha256:9c55...4238d)

| # | Assumption | Result | Evidence / consequence |
|---|---|---|---|
| 1 | `config.yaml` and plugins can be mounted read-only | **Pass** (2026-10-27) | Bind-mounted `config.yaml:ro` and `plugins/cardguard:ro` over `/opt/data`; `HERMES_SKIP_CONFIG_MIGRATION=1`; gateway started and ran as user `hermes`; `touch /opt/data/config.yaml` -> "Read-only file system". Rest of `/opt/data` stays writable (state, logs). |
| 2 | Raw inbound Telegram text never persisted before `pre_gateway_dispatch` | **Pass** | Sent a Luhn-valid test card (spaced and plain) to the vault bot. `grep -a` over the whole data dir (`state.db`, WAL, logs, cache, receipts) and `docker logs`: 0 raw hits; only `[[CARD:****1111]]` present. |
| 3 | `pre_gateway_dispatch` rewrite works | **Pass** | Log: `cardguard rewrote 1 number(s)`; the model path only saw the token. |
| 4 | Hook errors are safe | **Fail by default -> mitigated** | Docs: hook exceptions are caught and dispatch continues with the raw text (fail-open). `cardguard` now catches all errors and returns `{"action":"skip"}` (fail closed); unit-tested. |
| 5 | Hermes reaches Telegram through the zone proxy from an `internal: true` network | **Pass** | Connected in polling mode via `squid-vault`. |
| 6 | Plugins are opt-in | Confirmed | Must list under `plugins.enabled`; loaded as source `user`. |

| 7 | MCP over HTTP with bearer from env | **Pass** (2026-10-27) | `mcp_servers.vault_tools.url` + `headers.Authorization: "Bearer ${env:VAULT_TOOLS_MCP_TOKEN}"`; Hermes logged "registered 7 tool(s)" as `mcp__vault_tools__<tool>`. |
| 8 | Model id `claude-sonnet-5-5` accepted | **Pass** (2026-10-27) | Not in the Hermes docs (only `claude-sonnet-4-6` shown); live Telegram replies came back. Aux `claude-haiku-5-5` not yet confirmed. |
| 9 | Raw number never reaches model/session/logs with the real container | **Pass** | Dummy card sent to the vault bot: 0 raw hits across `/opt/data` and vault-tools logs; token present in `state.db`, `gateway.log`, `agent.log`. |
| 10 | `deleteMessage` on the owner's incoming message | **Pass** | Log `deleteMessage ok`; owner confirmed the message disappeared. |
| 11 | `/rincian` via `skip` + direct Bot API send stays out of the session store | **Pass** | Reply text "Belum ada rencana" has 0 hits in the data dir; TTL record written (auto-delete after 24h, sweep every 15 min; first expiry not yet observed). |

| 12 | All vault MCP tools are visible to the model | **Fail by default -> fixed** (2026-10-27) | With 28 tools, Hermes' Tool Search deferred 30 of 36 tools ("tier 1: 6 core/visible tools kept, 30 deferred"); the bot told the owner it had no PDF tool. Fix: `tools.tool_search.enabled: off` in `config.yaml` (doc: /user-guide/features/tool-search; there is no per-server "always visible" key). Also: a long-lived Telegram session keeps stale history (old dummy card/salary questions); `/new` starts a fresh one. |

## Closed at the M2 gate (2026-11-01, read-only probes on the VPS)
- Telegram-side copy of the raw message: closed by #10 (`deleteMessage ok`, the owner saw the message disappear).
  `event.message_id` matches Telegram's native id.
- `skip` plus a direct Bot API reply writes nothing to the session store: closed by #11. The 24-hour auto-delete runs:
  8 `/rincian` sends in the vault logs, 0 rows left in the TTL file and 0 failed sweeps. A sweep drops a row whether or
  not Telegram accepted the delete, so this shows the sweep ran, not that each delete worked; `sweep_ttl` now logs how
  many deletes Telegram accepted (counts only), so the first sweep after that code reaches the vault settles it. The
  code reached the vault on 2026-11-01 20:13 WIB with the doubled-rows deploy
  (`ops/datafix/2026-11-01-mandiri-dupes/deploy.sh`; before it the VPS ran a473d4d's cardguard, by hash), so the first
  sweep that finds an expired `/rincian` message logs `ttl sweep: Telegram deleted N of M`.
- DNS-over-HTTPS fallback cannot bypass the proxy: a direct TCP connection to both of Hermes' seed Telegram IPs fails
  with ENETUNREACH from all five zone containers (vault, front, vault-tools, control, change-proposals), external names
  do not resolve in them (`getaddrinfo` fails), and squid-vault denied the DoH queries themselves (`dns.google`,
  `cloudflare-dns.com`, docs/runtime/proxies.md). Hermes' fallback transport also takes its proxy from
  `TELEGRAM_PROXY`/`HTTPS_PROXY` (v0.22.5 `plugins/platforms/telegram/telegram_network.py`), so a fallback IP either goes
  through the zone's squid (where an IP is not on any allowlist) or to a network with no route.
- Hooks are not bounded by `plugins.hook_callback_timeout`, so each plugin bounds itself: every blocking call has a
  timeout (vault-tools 8 s, reports 30 s, Telegram 15 s, per socket operation) and deletes run in threads. Worst cases:
  a report 30 s + 2 x 15 s per message part (an HTML part refused is sent again plain), `/rincian` 8 + 15 s, a card
  number 8 s per number + 15 s; `cardblock` makes no network call on the dispatch path.
