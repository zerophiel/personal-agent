import json
import os
import sys

from .client import GmailClient
from .run import Config, run


def main() -> int:
    secrets = os.environ.get("SECRETS_DIR", "/run/secrets")
    load = lambda n: json.load(open(os.path.join(secrets, n)))  # noqa: E731
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "senders.json")) as f:
        banks = json.load(f)
    cfg = Config(senders={b["address"].lower(): k for k, b in banks.items()},
                 org_domains={k: b["org_domain"] for k, b in banks.items()},
                 drop_dir=os.environ.get("DROP_DIR", "/ingest"),
                 state_db=os.environ.get("STATE_DB", "/state/ingest.db"))
    summary = run(GmailClient(load("gmail_ingest_client"), load("gmail_ingest_token")), cfg)
    print(f"ingest-gmail: {summary}")
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
