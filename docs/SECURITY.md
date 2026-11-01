# Security (M1)

Invariants are enforced in infrastructure, not prompts.
- Egress: internal-only networks + per-zone Squid default-deny allowlists (`config/squid/`).
- Telegram: control checks `from.id == MY_TELEGRAM_ID` and `chat.type == private` on every message and callback; others dropped and logged (`services/control/control.py`, tested). The Hermes zones answer only `TELEGRAM_ALLOWED_USERS`, ignore other DMs, and drop every group (`allowed_chats: "none"`: no group id matches it, and the filter never applies to DMs; checked against v0.22.5 in a throwaway container). BotFather "Allow Groups" should be off for every bot as well: getMe on 2026-11-01 still showed it on for the vault and control bots.
- Containers: `cap_drop: ALL`, `no-new-privileges`, read-only root fs where possible, memory/CPU caps, `oom_score_adj` per brief.
- Secrets: root-only dir `/opt/personal-agent-secrets` (0700), injected as Docker secrets; plaintext never in the repo (`.gitignore`). sops+age is added in M2 when zone secrets multiply.
- vault-tools has two surfaces with different tokens: `/mcp` (model; tools handle aliases and amounts only, no tool stores or reveals a full number) and `/internal/*` (plugin only: `store_payee`, `rincian`). Tokens are random, >= 32 chars, must differ, compared in constant time; unknown paths 404. The payee encryption key (`vault_tools_key`) is generated on the VPS by `make secret-gen` and the script refuses to overwrite it (overwriting would orphan every stored number). Back it up with restic; keep the restic password separately.
- Maintenance never deletes volumes (`scripts/prune.sh`).
- Checked at the M2 gate (2026-11-01, docs/assumptions.md): external names do not resolve inside the internal networks
  and a direct connection has no route (ENETUNREACH from every zone container), so neither DNS nor Telegram's
  DNS-over-HTTPS fallback is a way out; the read-only config mount holds (spike #1). Hermes does not bound hooks by its
  hook timeout; every blocking call in the plugins has its own.

## Approvals (M3)
No LLM can approve anything. The chain is model -> `change-proposals` -> inbox folder -> `control` -> the owner's tap.
- **Only control decides**, and only on a tap of an inline button from `MY_TELEGRAM_ID` in the private chat. Each proposal
  gets a random 128-bit nonce (`a:<nonce>` / `r:<nonce>` in `callback_data`), stored in `control.db` and consumed in one
  `UPDATE ... WHERE nonce=? AND status='pending'`: a second tap, the other button, a forged or a stale nonce decides
  nothing. The buttons are removed after any tap. Control has no LLM, stdlib only, net-ctl only.
- **Two folders, one direction.** `proposals-inbox` is written by change-proposals and read (then emptied) by control;
  `control-state` (`control.db`, `decided/`, `approved/`) is mounted by control alone. Nothing a model-facing container
  writes can be an approval; `approved/<id>.json` exists only after the owner's tap.
- **Control trusts no inbox file.** It opens files with `O_NOFOLLOW`, accepts only small regular files, records a link,
  folder, oversized or deep JSON as invalid and removes it (a link, never its target), then re-validates: exactly the
  seven fields, zone and change type from fixed lists, length caps, and files only where that change type may write
  (`PATHS` in `services/control/control.py`). Host scripts, compose, plugins, control itself and secrets can never be in a
  proposal; a new service is an escalation, a secret value goes through `make secret-set`. At most five wait at a time.
- **Model text is shown, never run or rendered**: plain text (no `parse_mode`), no link previews, control and direction
  characters removed, links, domains and `@names` defanged so a tap opens nothing; a fixed footer says the text is the
  agent's. Quiet hours 22:00-06:00 WIB send without sound.
- **The owner sees the change as control computes it.** Before the card, control posts the unified diff of each file
  against the installed one (read-only mounts of `services/hermes/front/` and `config/squid/` under `/repo`), never the
  agent's description of it, and stores what it showed with the proposal (`review`: the installed files' hashes, and
  whether the diff was shown whole). Whole means every installed file readable by control, no hidden character in the
  new content (a `.yaml` or `.conf` may hold printable ASCII only, so no look-alike letters either) and the whole diff
  in one message of at most 3000 characters. The card says what a tap will do.
- **change-proposals** has one tool (`submit`), a bearer token (`change_proposals_mcp_token`), the inbox mount and
  nothing else; it applies nothing, cannot read decisions, and caps itself at five waiting files and ten per 24 hours.

### Applier (built 2026-11-01, not installed: the owner decides at the M3 gate)
`services/applier/applier.py`, a root host unit, never inside a container; stdlib only, no LLM. It drives Docker, which
is root on the host anyway, so systemd does not sandbox it: what keeps it narrow is what it accepts.
- **Input**: only `control-state/approved/<id>.json` (small, regular, never a link), and only when `control.db`, opened
  read-only, records that id as approved with the same proposal and the same review; then control's own `validate()`.
  Each id once: `applied/`, `failed/` or `skipped/` under `/opt/personal-agent-data/applier` (root, 0700). Approvals
  decided before the install time (`outcome/applier.json`) are skipped without a message, as the test #1 will be
  (Setujui on 1 Nov, a config change without files that today's rules refuse). The test #2 (front's skill, waiting for
  the owner's Tolak) can never be applied either way: skills are refused, and so is anything posted before control
  showed diffs.
- **What it applies**: zone front, and only the three files mounted into front and squid-front (`FRONT_FILES`: front's
  `config.yaml` and `SOUL.md`, `config/squid/front.conf`), narrower than control's `PATHS` on purpose. Vault, comms,
  `credential` and `skill` are refused with the reason the owner reads: a human builds them from the proposal, and a
  secret goes through `make secret-set`.
- **Exactly what the owner saw**: refused unless control showed the diff whole before the buttons and every file is
  still what it was when that diff was made (`review.base_sha256`), so a change made since (a deploy, another proposal)
  is never overwritten by an older diff.
- **Rules before writing**: `tests/test_zones.py` passes on a copy of the tree with the change in it (none skipped), and
  a squid conf passes `squid -k parse` in a throwaway container without a network (any output but the two offline
  warnings is a refusal: a broken `http_access` line still exits 0). Among those rules: front's config sets only the
  keys the test lists (a `base_url` would send every chat and the Anthropic key elsewhere while `provider` still says
  anthropic; a new provider, hook, platform or MCP server needs a human); both profiles: Anthropic Haiku or Sonnet only,
  no `${...}` or URL outside the MCP url and its header, no lazy installs, memory and skill writes only with the
  owner's OK, Telegram only; every squid conf holds plain lines only (no helper program, `include`, `cache_peer` or
  other port), and front denies private ranges, other ports and CONNECT to anything but 443 before any allow.
- **Writing and checking**: the old files kept (`backup/<id>.json`), the new ones written atomically with the old owner
  and mode, the service recreated (a file mount keeps the old inode until then) and checked: running, not restarting,
  front back on Telegram from a new process, the files inside the container the new ones. A failed check puts the old
  files back and recreates the service again, once. A run that stopped between the backup and the outcome is undone at
  the next run, never over a file that changed since (that one is reported for a human).
- **Reporting**: `outcome/<id>.json` (status, paths, reason; never contents), mounted read-only into control, which
  tells the owner once and counts the outcomes in `/status`.
- **Deploys and the repo**: no deploy key and no git on the VPS, so the VPS never writes to GitHub. `make deploy` holds
  the applier while it runs (`scripts/deploy-guard.sh`) and refuses while the VPS has an applied change this checkout
  lacks; `make applied-pull` commits each one here after checking it again against this checkout's `control.py` and
  the hashes the applier recorded.
- **Left to a human**: a diff over 3000 characters (it cannot be shown whole), skills, vault and comms, secrets.
A `skill` change lands only after a human has added, once, a read-only mount of `services/hermes/<zone>/skills/` listed
in `skills.external_dirs` and turned the `skills` toolset on (compose is never in a proposal). Not a mount over
`<HERMES_HOME>/skills`: Hermes copies its bundled skills and a manifest there at every boot.

### Front zone (M3)
- Tools: web search and extract, `clarify`, `vision_analyze`, memory (each write waits for the owner's OK; no background
  memory review) and `submit`.
  Terminal, code, files, browser, skills, x_search (it switches itself on when xAI credentials exist), delegation, cron
  and the rest are disabled (`services/hermes/front/config.yaml`,
  checked by `tests/test_zones.py`), so no enabled tool reads the env file or the keys in it: `vision_analyze` refuses
  `.env`/`auth.json` by name and anything whose bytes are not an image (Hermes v0.22.5 `tools/image_source.py`).
- Its own bot and its own Anthropic key, from a separate workspace with a USD 40 limit; `scripts/render-front-env.sh`
  refuses the vault's key and token. Front is on net-front only: no route to vault-tools, the ledger or control.
- Web search uses no key: the image has no DuckDuckGo package, so Hermes falls back to the free tiers of Exa, Parallel,
  Keenable or Firecrawl through squid-front (open web, private ranges blocked; Hermes also refuses private addresses).
  Search text leaves the VPS. At boot, before any chat, Hermes also fetches model catalogs (models.dev, openrouter.ai),
  Nous pages and two DNS-over-HTTPS resolvers (squid-front's log, 2026-11-01).
- Web text is untrusted. A prompt in a page could make front fetch a URL that carries chat text, which is why finance
  and secrets stay out of front (SOUL.md), and why a change still needs the owner's tap in control.
- Card numbers: the `cardblock` plugin (`services/hermes/front/plugins/cardblock`, mounted read-only) drops every
  inbound message whose text holds a Luhn-valid 13-19 digit run before Hermes dispatches it, so neither the model nor
  the session store sees it; photo captions and the text documents Hermes inlines are checked too. The owner's raw
  message is deleted and a fixed notice sent; anyone else's is dropped without a reply (Hermes runs this hook before its
  sender check). An error drops the message as well. The detection is vault cardguard's, kept equal by a test.
  Left to SOUL.md: a photo of a card, account and VA numbers, PINs, OTPs and passwords. Luhn also flags some IMEIs and
  reference numbers; the notice asks the owner to send the message again without the digit run.
- Vault's cardguard acts only for the owner in a private chat, decided as cardblock decides (a test keeps the two
  equal): anyone else's command (`/rincian`, `/rekening`, `/va`, the reports) or card number is dropped unanswered and
  nothing is stored or sent. Telegram's intake filter (TELEGRAM_ALLOWED_USERS with `unauthorized_dm_behavior: ignore`)
  already drops a stranger before the hook; the check keeps `/rincian` the owner's if that setting ever changes to
  `pair` or `decline`. Hermes gives every Telegram message, media included, `user_id = str(user.id)`; on 2026-11-01 all
  30 of vault's Telegram sessions carried the allowlisted id. An empty allowlist drops every command and is logged at
  boot. Live since 2026-11-01 20:13 WIB: `ops/datafix/2026-11-01-mandiri-dupes/deploy.sh` synced it and restarted the
  vault (the plugin in the container hashes as the repo's; agent.log has no empty-allowlist line and says the command
  menu was restored). Until then the VPS ran a473d4d's cardguard, which acts for any private chat that passes the
  intake filter.
