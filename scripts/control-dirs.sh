#!/usr/bin/env bash
# Run with sudo on the VPS before control (M3) first starts: the folders control and change-proposals write, owned by the
# uid both run as. Safe to run again; never deletes or empties anything.
set -euo pipefail
install -d -o 10001 -g 10001 -m 0700 /opt/personal-agent-data/control-state /opt/personal-agent-data/proposals-inbox
stat -c '%n %U:%G %a' /opt/personal-agent-data/control-state /opt/personal-agent-data/proposals-inbox
