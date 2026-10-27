# Assumption spikes (Hermes v0.22.5, digest sha256:9c55...4238d)

| # | Assumption | Result | Evidence / consequence |
|---|---|---|---|
| 1 | `config.yaml` and plugins can be mounted read-only | **Pass** (2026-10-27) | Bind-mounted `config.yaml:ro` and `plugins/cardguard:ro` over `/opt/data`; `HERMES_SKIP_CONFIG_MIGRATION=1`; gateway started and ran as user `hermes`; `touch /opt/data/config.yaml` -> "Read-only file system". Rest of `/opt/data` stays writable (state, logs). |
| 2 | Raw inbound Telegram text never persisted before `pre_gateway_dispatch` | **Pass** | Sent a Luhn-valid test card (spaced and plain) to the vault bot. `grep -a` over the whole data dir (`state.db`, WAL, logs, cache, receipts) and `docker logs`: 0 raw hits; only `[[CARD:****1111]]` present. |
| 3 | `pre_gateway_dispatch` rewrite works | **Pass** | Log: `cardguard rewrote 1 number(s)`; the model path only saw the token. |
| 4 | Hook errors are safe | **Fail by default -> mitigated** | Docs: hook exceptions are caught and dispatch continues with the raw text (fail-open). `cardguard` now catches all errors and returns `{"action":"skip"}` (fail closed); unit-tested. |
| 5 | Hermes reaches Telegram through the zone proxy from an `internal: true` network | **Pass** | Connected in polling mode via `squid-vault`. |
| 6 | Plugins are opt-in | Confirmed | Must list under `plugins.enabled`; loaded as source `user`. |

## Still open
- Telegram-side copy of the raw message: the chat history keeps it until the plugin calls `deleteMessage` (to implement; allowed for incoming messages in private chats within 48 h, to verify).
- Whether a `skip` plus direct Bot API reply (design for `/rincian`) writes anything to the session store.
- Hermes logs "Discovering Telegram API fallback IPs via DNS-over-HTTPS": confirm it cannot bypass the proxy when DoH is blocked (spike worked, but check the fallback path).
- Hooks are not bounded by `plugins.hook_callback_timeout`: a hung callback blocks that message.
