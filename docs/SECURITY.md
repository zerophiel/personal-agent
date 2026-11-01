# Security (M1)

Invariants are enforced in infrastructure, not prompts.
- Egress: internal-only networks + per-zone Squid default-deny allowlists (`config/squid/`).
- Telegram: control checks `from.id == MY_TELEGRAM_ID` and `chat.type == private` on every message and callback; others dropped and logged (`services/control/control.py`, tested). The Hermes zones answer only `TELEGRAM_ALLOWED_USERS`, ignore other DMs, and drop every group (`allowed_chats: "none"`: no group id matches it, and the filter never applies to DMs; checked against v0.22.5 in a throwaway container). BotFather "Allow Groups" should be off for every bot as well: getMe on 2026-11-01 still showed it on for the vault and control bots.
- Containers: `cap_drop: ALL`, `no-new-privileges`, read-only root fs where possible, memory/CPU caps, `oom_score_adj` per brief.
- Secrets: root-only dir `/opt/personal-agent-secrets` (0700), injected as Docker secrets; plaintext never in the repo (`.gitignore`). sops+age is added in M2 when zone secrets multiply.
- vault-tools has two surfaces with different tokens: `/mcp` (model; tools handle aliases and amounts only, no tool stores or reveals a full number) and `/internal/*` (plugin only: `store_payee`, `rincian`). Tokens are random, >= 32 chars, must differ, compared in constant time; unknown paths 404. The payee encryption key (`vault_tools_key`) is generated on the VPS by `make secret-gen` and the script refuses to overwrite it (overwriting would orphan every stored number). Back it up with restic; keep the restic password separately.
- Maintenance never deletes volumes (`scripts/prune.sh`).
- Known limits: DNS still resolves inside internal networks; Hermes read-only config mount is unverified (spike in M1/M2).

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
- **change-proposals** has one tool (`submit`), a bearer token (`change_proposals_mcp_token`), the inbox mount and
  nothing else; it applies nothing, cannot read decisions, and caps itself at five waiting files and ten per 24 hours.

### Applier contract (not built; nothing is applied yet)
A host unit (root on the VPS, never inside a container) that will:
1. read only `control-state/approved/<id>.json`, never the inbox, and apply each id at most once (`applied/<id>.json` or
   `failed/<id>.json` next to it);
2. re-validate with control's `validate()`; refuse zone `vault` outright (finance-zone changes are built by a human from
   the proposal) and `credential` (control tells the owner the `make secret-set` command instead);
3. write the files into a git checkout, commit with the proposal id, push with a deploy key, then
   `docker compose up -d <that zone's service>` (`egress_domain`: reconfigure that zone's squid), health-check it, and on
   failure revert the commit and redeploy; report the outcome through control.
Before it exists: a deploy key (the owner creates it), a git checkout on the VPS (today `/opt/personal-agent` is an rsync
target without `.git`) and the owner's review at the M3 gate; front runs since 2026-11-01.
Approvals recorded before it exists are tests and are never applied: #1 (Setujui on 1 Nov, a config change without
files that today's rules refuse) and #2 (front's test skill). At install the applier records them as not applied.
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
- Vault's cardguard checks no sender: Telegram's intake filter (TELEGRAM_ALLOWED_USERS with `unauthorized_dm_behavior:
  ignore`) drops a stranger before the hook, but `pair` or `decline` would let a stranger's `/rincian` reach it. Keep
  `ignore`; an owner check in cardguard is a follow-up (docs/PROGRESS.md).
