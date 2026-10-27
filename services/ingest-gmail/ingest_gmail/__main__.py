import json
import os
import sys

from .client import GmailClient
from .run import Config, run


def load_senders(banks: dict) -> dict[str, str]:
    """lowercase address -> bank key; an address listed under two banks is a config error."""
    out: dict[str, str] = {}
    for bank, cfg in banks.items():
        for addr in cfg["addresses"]:
            key = addr.lower()
            if key in out and out[key] != bank:
                raise ValueError(f"{key} listed for both {out[key]} and {bank}")
            out[key] = bank
    return out


def main() -> int:
    secrets = os.environ.get("SECRETS_DIR", "/run/secrets")
    load = lambda n: json.load(open(os.path.join(secrets, n)))  # noqa: E731
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "senders.json")) as f:
        banks = json.load(f)
    cfg = Config(senders=load_senders(banks),
                 org_domains={k: b["org_domain"] for k, b in banks.items()},
                 drop_dir=os.environ.get("DROP_DIR", "/ingest"),
                 state_db=os.environ.get("STATE_DB", "/state/ingest.db"))
    summary = run(GmailClient(load("gmail_ingest_client"), load("gmail_ingest_token")), cfg)
    print(f"ingest-gmail: {summary}")
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
