# The project map

`CLAUDE.md` holds the rule and the commands: query the graph first, `make graph` after code edits, `/graphify . --update` after doc edits.
`docs/LAPTOP.md` holds the installation.

`graph_first.py` is the hook of `.claude/settings.json`. It adds the map, what changed since the build and the age of the copy in `private/`
to every request.

What past naming rounds taught (audit community names after re-clustering, per-doc delta bases from the manifest, a pass for lost names,
identifier and stale-name checks) is in Claude's memory, `project-graph-first.md`. On this laptop it is in
`~/.claude/projects/<this checkout's folder>/memory/`, where an AI may read it. Its copy in `private/knowledge/claude-projects/` is for the
owner to bring back on a new laptop.
