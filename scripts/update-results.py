#!/usr/bin/env python3
"""Publish verified ESPN finals for automatic Nude TV prediction settlement."""
import json
import html
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from recent_form import ESPN_PATHS

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://site.api.espn.com/apis/site/v2/sports/'


def fetch(url, headers=None):
    request = urllib.request.Request(url, headers={'User-Agent': 'sports-lineups-results/1.0', 'Accept': 'application/json', **(headers or {})})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def fetch_text(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 sports-lineups-results/1.0'})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode('utf-8', 'replace')


def text(value):
    return html.unescape(re.sub(r'<[^>]+>', ' ', value)).strip()


def parse_kbl_results(payload, start, now, checked_at):
    """Accept only ended regular-season games with an official ID and valid final score."""
    if isinstance(payload, list):
        rows = payload
    else:
        if payload.get('resultCode') not in (None, '', 'Success', '00'):
            raise ValueError('KBL official API rejected the results request')
        rows = payload.get('object') or payload.get('data') or []
    if isinstance(rows, dict):
        rows = rows.get('list') or rows.get('matches') or []
    results = []
    for match in rows if isinstance(rows, list) else []:
        if str(match.get('isEnded') or '').upper() not in ('Y', 'TRUE', '1'):
            continue
        event_id = str(match.get('gmkey') or match.get('gameId') or '')
        date = re.sub(r'[^0-9]', '', str(match.get('gameDate') or ''))[:8]
        time = re.sub(r'[^0-9]', '', str(match.get('gameTime') or match.get('startTime') or ''))[:4].ljust(4, '0')
        try:
            kickoff = datetime.strptime(date + time, '%Y%m%d%H%M').replace(tzinfo=ZoneInfo('Asia/Seoul')).astimezone(timezone.utc)
            home_score, away_score = int(match['scoreH']), int(match['scoreA'])
        except (KeyError, TypeError, ValueError):
            continue
        home, away = str(match.get('tnameH') or '').strip(), str(match.get('tnameA') or '').strip()
        if not event_id or not home or not away or home == away or home_score == away_score or not start <= kickoff <= now:
            continue
        results.append({'eventId': event_id, 'league': 'kbl', 'kickoff': kickoff.isoformat(), 'status': 'final',
                        'homeName': home, 'awayName': away, 'homeScore': home_score, 'awayScore': away_score,
                        'winner': 'home' if home_score > away_score else 'away', 'checkedAt': checked_at, 'note': ''})
    return results


def main():
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=3)
    feed = json.loads((ROOT / 'dist/nude-feed.json').read_text())
    previous_path = ROOT / 'dist/results.json'
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {'items': []}
    leagues = {str(match.get('league')) for match in feed.get('matches', []) if match.get('league') in ESPN_PATHS}
    leagues.update(str(item.get('league')) for item in previous.get('items', []) if item.get('league') in ESPN_PATHS)
    dates = [(now.date() - timedelta(days=offset)).strftime('%Y%m%d') for offset in range(4)]
    supported = set(ESPN_PATHS) | {'kbl', 'khl', 'v_league', 'v_league_w'}
    items = {str(item.get('eventId')): item for item in previous.get('items', [])
             if item.get('eventId') and item.get('league') in supported and
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
    # KBL's official API returns match ID, game date and final scores together.
    kst = ZoneInfo('Asia/Seoul')
    try:
        query = urllib.parse.urlencode({'fromDate': (now.astimezone(kst).date() - timedelta(days=3)).strftime('%Y%m%d'),
                                        'toDate': now.astimezone(kst).date().strftime('%Y%m%d'), 'tcodeList': 'all', 'seasonGrade': 1})
        payload = fetch('https://api.kbl.or.kr/match/list?' + query, {'channel': 'WEB', 'teamCode': 'XX'})
        for row in parse_kbl_results(payload, start, now, now.isoformat()):
            items[row['eventId']] = row
    except (OSError, ValueError, urllib.error.URLError) as error:
        print(f'KBL results unavailable: {error}')
    # KOVO's public match data includes final set scores and feed-matching match IDs.
    try:
        page = fetch_text('https://bkvolley.kr/matches')
        source = re.search(r'<script id="volley-public-data" type="application/json">(.*?)</script>', page, re.S)
        public = json.loads(source.group(1)).get('data', {}) if source else {}
        for match in public.get('recentMatches', []):
            if match.get('status') != 'finished' or not match.get('matchDate'):
                continue
            kickoff = datetime.fromisoformat(match['matchDate'].replace('Z', '+00:00'))
            home, away = match.get('homeSets'), match.get('awaySets')
            event_id = str(match.get('id') or '')
            if not event_id or not start <= kickoff <= now or not isinstance(home, int) or not isinstance(away, int) or home == away:
                continue
            division = str(match.get('league') or match.get('division') or '').lower()
            league = 'v_league_w' if '여' in division or 'women' in division else 'v_league'
            items[event_id] = {'eventId': event_id, 'league': league, 'kickoff': kickoff.isoformat(), 'status': 'final',
                               'homeId': str(match.get('homeTeamId') or ''), 'awayId': str(match.get('awayTeamId') or ''),
                               'homeName': str(match.get('homeTeamName') or ''), 'awayName': str(match.get('awayTeamName') or ''),
                               'homeScore': home, 'awayScore': away, 'winner': 'home' if home > away else 'away',
                               'checkedAt': now.isoformat(), 'note': '세트 점수'}
    except (OSError, ValueError, urllib.error.URLError) as error:
        print(f'KOVO results unavailable: {error}')
    # KHL marks completed events with end_at and supplies final score in the same event feed.
    try:
        query = urllib.parse.urlencode({'q[start_at_gt_time_from_unixtime]': int(start.timestamp()),
                                        'q[start_at_lt_time_from_unixtime]': int(now.timestamp()),
                                        'order_direction': 'desc', 'locale': 'en'}, safe='[]')
        history = fetch('https://khl.api.webcaster.pro/api/khl_mobile/events_v2.json?' + query)
        events = history if isinstance(history, list) else history.get('events', [])
        for raw in events:
            game = raw.get('event', raw)
            event_id = str(game.get('id') or '')
            try:
                kickoff = datetime.fromtimestamp(int(game['start_at']) / 1000, timezone.utc)
                ended = datetime.fromtimestamp(int(game['end_at']) / 1000, timezone.utc)
                hs, aws = map(int, str(game.get('score') or '').split(':'))
            except (KeyError, TypeError, ValueError, OSError):
                continue
            if game.get('type_id') not in (18, 24) or not event_id or not start <= kickoff <= now or not start <= ended <= now or hs == aws:
                continue
            home, away = game.get('team_a') or {}, game.get('team_b') or {}
            items[event_id] = {'eventId': event_id, 'league': 'khl', 'kickoff': kickoff.isoformat(), 'status': 'final',
                               'homeId': str(home.get('id') or ''), 'awayId': str(away.get('id') or ''),
                               'homeName': str(home.get('name') or ''), 'awayName': str(away.get('name') or ''),
                               'homeScore': hs, 'awayScore': aws, 'winner': 'home' if hs > aws else 'away',
                               'checkedAt': now.isoformat(), 'note': ''}
    except (OSError, ValueError, urllib.error.URLError) as error:
        print(f'KHL results unavailable: {error}')
    payload = {'schemaVersion': 1, 'asOf': now.isoformat(), 'windowStart': start.isoformat(),
               'windowEnd': now.isoformat(), 'items': sorted(items.values(), key=lambda item: item['kickoff'])}
    previous_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(f'Published {len(payload["items"])} verified ESPN results for {len(leagues)} leagues')


if __name__ == '__main__':
    main()
