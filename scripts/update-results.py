#!/usr/bin/env python3
"""Publish verified ESPN finals for automatic Nude TV prediction settlement."""
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from recent_form import ESPN_PATHS

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://site.api.espn.com/apis/site/v2/sports/'


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'sports-lineups-results/1.0', 'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def main():
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=3)
    feed = json.loads((ROOT / 'dist/nude-feed.json').read_text())
    previous_path = ROOT / 'dist/results.json'
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {'items': []}
    leagues = {str(match.get('league')) for match in feed.get('matches', []) if match.get('league') in ESPN_PATHS}
    leagues.update(str(item.get('league')) for item in previous.get('items', []) if item.get('league') in ESPN_PATHS)
    dates = [(now.date() - timedelta(days=offset)).strftime('%Y%m%d') for offset in range(4)]
    items = {str(item.get('eventId')): item for item in previous.get('items', [])
             if item.get('eventId') and item.get('league') in leagues and
             start <= datetime.fromisoformat(item['kickoff'].replace('Z', '+00:00')) <= now}
    for league in sorted(leagues):
        path = ESPN_PATHS[league]
        for day in dates:
            url = BASE + path + '/scoreboard?' + urllib.parse.urlencode({'dates': day, 'limit': 500})
            try:
                events = fetch(url).get('events', [])
            except (OSError, ValueError, urllib.error.URLError) as error:
                print(f'ESPN results unavailable: {league} {day}: {error}')
                continue
            for event in events:
                competition = (event.get('competitions') or [{}])[0]
                status = competition.get('status', {}).get('type', {})
                name = str(status.get('name') or '').upper()
                state = 'postponed' if 'POSTPON' in name else 'cancelled' if 'CANCEL' in name else 'final' if status.get('completed') else ''
                if not state:
                    continue
                kickoff = str(event.get('date') or '')
                try:
                    played = datetime.fromisoformat(kickoff.replace('Z', '+00:00'))
                except ValueError:
                    continue
                if not start <= played <= now:
                    continue
                competitors = competition.get('competitors', [])
                home = next((team for team in competitors if team.get('homeAway') == 'home'), None)
                away = next((team for team in competitors if team.get('homeAway') == 'away'), None)
                if not home or not away:
                    continue
                row = {'eventId': str(event.get('id') or ''), 'league': league, 'kickoff': kickoff,
                       'status': state, 'homeId': str(home.get('id') or (home.get('team') or {}).get('id') or ''),
                       'awayId': str(away.get('id') or (away.get('team') or {}).get('id') or ''),
                       'homeName': str((home.get('team') or {}).get('displayName') or ''),
                       'awayName': str((away.get('team') or {}).get('displayName') or ''),
                       'checkedAt': now.isoformat(), 'note': ''}
                if state == 'final':
                    try:
                        hs, aws = int(home['score']), int(away['score'])
                    except (KeyError, TypeError, ValueError):
                        continue
                    row.update(homeScore=hs, awayScore=aws)
                    winner = next((team for team in competitors if team.get('winner') is True), None)
                    if winner:
                        row['winner'] = 'home' if winner.get('homeAway') == 'home' else 'away'
                    elif hs == aws and league not in ('ucl', 'uel'):
                        row['winner'] = 'draw'
                    else:
                        continue
                if row['eventId']:
                    items[row['eventId']] = row
    payload = {'schemaVersion': 1, 'asOf': now.isoformat(), 'windowStart': start.isoformat(),
               'windowEnd': now.isoformat(), 'items': sorted(items.values(), key=lambda item: item['kickoff'])}
    previous_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(f'Published {len(payload["items"])} verified ESPN results for {len(leagues)} leagues')


if __name__ == '__main__':
    main()
