# Data fixes

Each dated folder is the record of a one-time change to the live ledger or a deploy that went with it. They all ran once, on the
dates in their names, and what they did stays in the ledger and in `docs/PROGRESS.md`. They are kept to show how each number came
to be and as a pattern for the next fix. A rebuilt host gets its data through `make restore`, so none of them runs again.

The `H=` line of each `deploy.sh` holds the placeholder `<vps>` on purpose: a script started by mistake stops at its first ssh
instead of changing a live host. A new fix gets its own dated folder, takes its address from `config/vps.env`, and makes a backup
before it changes data (`docs/calibration.md`).
