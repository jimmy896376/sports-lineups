# Korean name catalog

`dist/name-catalog.json` is the public feed for reviewed team and player names. The standalone board refreshes it on page load and reload. NudeTV staging reads the same feed, but its renderer is maintained separately.

## Sources and approval

- Add reviewed team aliases and full names to `scripts/team-name-review.json`.
- Add reviewed player spellings to `scripts/player-name-review.json` (`userOverrides`), with identity evidence in `scripts/player-name-source-review.json`.
- `scripts/resolve-player-names.py` checks current lineup, pitcher and injury names against exact bilingual team roster rows, identifiable Google results, Daum sports profiles, or two independent bilingual sports sources. It does not search Wikipedia or generate phonetic guesses. Previously approved legacy entries remain in `scripts/player-name-auto-review.json`.
- The resolver must match the full original name and player identity. An ambiguous or unreadable result stays in the review queue and remains in its original script on the site.

## Automation and limits

`.github/workflows/refresh-names.yml` runs every 15 minutes and on relevant changes. It collects names from every configured league, checks up to 24 team rosters and 100 individual searches per run, validates approved mappings, then publishes the catalog. A successful run means the pipeline completed; it does not mean every name was translated.

`scripts/player-name-run-report.json` records pending names by league, roster approvals, search approvals and collection failures. The workflow also uploads `scripts/player-name-live-audit.json` and the current inventory as artifacts. Repeated zero search approvals require a source or matching-rule investigation; more scheduling alone cannot improve coverage. Google and Bing can return challenges or unreadable pages on GitHub runners. No API key is configured.

The standalone board normalizes case, accents and punctuation before lookup. The catalog also publishes exact aliases for verified player and team names as they appear in the latest collected inventory. This covers newly observed provider variants on NudeTV staging without inventing new Korean spellings. The NudeTV staging renderer must still apply the same normalization or use an approved stable player ID to handle a variant before the next scheduled catalog build.

## Checks

```sh
python3 scripts/test_resolve_player_names.py
node scripts/build-name-catalog.mjs
node scripts/check-player-names.mjs --inventory scripts/fixtures/player-name-inventory.json --require-reviewed
```

Check `scripts/player-name-run-report.json` after each run and inspect the public staging page for at least one newly approved name. Do not infer site success from a green GitHub Actions check.
