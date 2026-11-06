#!/usr/bin/env bash
# The owner's last step of the merge into main, in ~/personal-agent after git pull --ff-only origin main. It checks that this folder now
# holds the recipe and the copy, keeps the graph's git-ignored files (the extraction cache saves a paid re-extraction) and removes the old
# worktree. Any failed check stops it with nothing removed. Safe to run again. Its only reader is the owner, so it speaks Indonesian.
set -euo pipefail
cd "$(dirname "$0")/.."
old=.claude/worktrees/m1-skeleton
stop() { echo "finish-merge: berhenti, tidak ada yang dihapus: $*" >&2; exit 1; }

[ "$(git rev-parse --git-dir)" = .git ] || stop "jalankan di folder utama ~/personal-agent, bukan di worktree"
[ "$(git symbolic-ref -q --short HEAD)" = main ] || stop "folder ini tidak berada di cabang main"
[ -f docs/REBUILD.md ] || stop "docs/REBUILD.md tidak ada; jalankan dulu: git pull --ff-only origin main"
grep -q -e '--exclude /private/' Makefile || stop "Makefile tidak mengecualikan private/ dari deploy"
git check-ignore -q private/ || stop "git tidak mengabaikan private/"
[ -f private/vps/MIRROR.json ] || stop "belum ada salinan di private/; jalankan dulu: make mirror"
[ -z "$(git status --porcelain)" ] || stop "folder ini punya perubahan yang belum di-commit"

if [ -d "$old" ]; then
  [ ! -e "$old/private" ] || stop "ada folder private di dalam worktree; pindahkan dulu ke folder utama"
  [ -z "$(git -C "$old" status --porcelain)" ] || stop "worktree punya perubahan yang belum di-commit"
  git merge-base --is-ancestor "$(git -C "$old" rev-parse HEAD)" HEAD || stop "worktree punya commit yang belum ada di main"
  if [ -d "$old/graphify-out" ]; then
    # What git tracks came with the pull. The build state is a fingerprint of the old path, and graphify makes it again.
    rsync -a --ignore-existing --exclude .graphify_build_state.json "$old/graphify-out/" graphify-out/
  fi
  git worktree remove "$old"
fi
git worktree prune
echo "finish-merge: selesai. Mulai sekarang kerja di ~/personal-agent, cabang main."
