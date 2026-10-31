# Architecture (M1 skeleton)

Split by trust boundary: vault (finance), front (general/web), comms (email/calendar), control (approvals, no LLM). One Hermes profile and one container per zone; zone services are added in M2-M4.

## Networks (all `internal: true`, no route out)
| Network | Members | Outbound via |
|---|---|---|
| net-vault | squid-vault, vault, vault-tools, ingest-gmail (timer job) | squid-vault allowlist |
| net-front | squid-front; front and change-proposals (M3, compose profile `front`, started once the owner's front secrets exist); sandbox and notion-mcp later | squid-front (web, private ranges blocked) |
| net-comms | squid-comms (+ comms, brokers, card-bus in M4) | squid-comms allowlist |
| net-ctl | squid-ctl, control | squid-ctl (api.telegram.org) |
| egress | the four squid proxies only | internet |

Only proxies join `egress`; a container with no proxy variable has no route out.

## Folders under /opt/personal-agent-data that two services share (`scripts/data-dirs.sh` creates the M3 ones)
| Folder | Writer | Reader | Why |
|---|---|---|---|
| `ingest` | ingest-gmail | vault-tools (read-only) | statement drop, same zone |
| `proposals-inbox` | change-proposals (net-front) | control (net-ctl), which empties it | the only path from a model-facing zone to control |
| `control-state` | control only | the applier, later (`approved/`) | decisions; never mounted by a model-facing container |

## Approvals (M3)
front (Hermes, Haiku) -> `submit` on change-proposals -> `proposals-inbox/<time>-<random>.json` -> control re-validates
and posts it to the owner with one-time Setujui/Tolak buttons -> the tap is recorded in `control-state` (`decided/`, and
`approved/` when approved). Applying an approved change is the applier's job, not built yet (contract in
`docs/SECURITY.md`). Control commands: `/status` (counts), `/usulan` (re-post waiting proposals with their buttons), `/ping`.

## Deviations from the original brief (see plan file)
- Kanban replaced by a `card-bus` MCP (Hermes docs do not cover Kanban across containers).
- Hermes cron jobs are seeded by deploy (`hermes cron create`), not defined in config.
- `/rincian` handled in `pre_gateway_dispatch` with `skip` plus direct Bot API send.

## Hermes pin
`nousresearch/hermes-agent` v0.22.5, manifest digest `sha256:9c5561579f3ffdf333401797094ac3a743738d6c25d40f4331c7bf77b694238d` (checked 2026-10-27).
