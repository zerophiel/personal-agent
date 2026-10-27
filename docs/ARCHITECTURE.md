# Architecture (M1 skeleton)

Split by trust boundary: vault (finance), front (general/web), comms (email/calendar), control (approvals, no LLM). One Hermes profile and one container per zone; zone services are added in M2-M4.

## Networks (all `internal: true`, no route out)
| Network | Members (M1) | Outbound via |
|---|---|---|
| net-vault | squid-vault (+ vault, vault-tools, ingest-gmail in M2) | squid-vault allowlist |
| net-front | squid-front (+ front, sandbox, notion-mcp, change-proposals in M3) | squid-front (web, private ranges blocked) |
| net-comms | squid-comms (+ comms, brokers, card-bus in M4) | squid-comms allowlist |
| net-ctl | squid-ctl, control | squid-ctl (api.telegram.org) |
| egress | the four squid proxies only | internet |

Only proxies join `egress`; a container with no proxy variable has no route out.

## Deviations from the original brief (see plan file)
- Kanban replaced by a `card-bus` MCP (Hermes docs do not cover Kanban across containers).
- Hermes cron jobs are seeded by deploy (`hermes cron create`), not defined in config.
- `/rincian` handled in `pre_gateway_dispatch` with `skip` plus direct Bot API send.

## Hermes pin
`nousresearch/hermes-agent` v0.22.5, manifest digest `sha256:9c5561579f3ffdf333401797094ac3a743738d6c25d40f4331c7bf77b694238d` (checked 2026-10-27).
