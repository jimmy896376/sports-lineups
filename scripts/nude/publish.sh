#!/usr/bin/env bash
set -euo pipefail
[[ ${GITHUB_ACTIONS:-} == true ]] || { echo 'CI only: this script resets the checkout.' >&2; exit 2; }

git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
for attempt in 1 2 3; do
  # Disposable CI checkout only. Rebuild on fresh main after any race.
  git fetch origin main
  git reset --hard origin/main
  node scripts/nude/test.mjs
  node scripts/nude/export.mjs
  git add -- dist/nude-feed.json
  if git diff --cached --quiet; then exit 0; fi
  git commit -m 'chore: publish Nude lineup feed'
  if git push origin HEAD:main; then exit 0; fi
done
echo 'Publish raced with upstream or branch protection blocked it; previous feed retained.' >&2
exit 1
