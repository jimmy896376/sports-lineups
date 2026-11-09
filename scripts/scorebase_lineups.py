"""Collect published match lineups from Scorebase for the current five KST days."""
import base64
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from html import unescape
from zoneinfo import ZoneInfo

BASE = 'https://www.xn--hy1bm7m1yevrd8pq.kr'
SPORTS = {'soccer': '축구', 'baseball': '야구', 'basketball': '농구',
          'volleyball': '배구', 'hockey': '하키'}
STARTERS = {'축구': 11, '야구': 9, '농구': 5, '배구': 6, '하키': 6}
KST = ZoneInfo('Asia/Seoul')
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; NudeLineups/1.0)', 'Accept': 'text/html'}
ROW = re.compile(r'<div class="sb-row(?: [^"]*)?"')
CHUNK = re.compile(r'<script>self\.__next_f\.push\(\[1,("(?:\\.|[^"\\])*")\]\)</script>', re.S)
RECORD = re.compile(r'(\d+)승\s+(\d+)무\s+(\d+)패')


def fetch(path):
    with urllib.request.urlopen(urllib.request.Request(BASE + path, headers=HEADERS), timeout=25) as response:
        return response.read().decode('utf-8', 'replace')


def board_rows(page, day, now):
    """Find matches that could have a published lineup; never infer an exact kickoff here."""
    starts = list(ROW.finditer(page))
    found = []
    for index, start in enumerate(starts):
        segment = page[start.start():starts[index + 1].start() if index + 1 < len(starts) else start.start() + 5000]
        path = re.search(r'href="(/live/[^"?]+)"', segment)
        home = re.search(r'class="sb-team-home"[^>]*>(.*?)</span>', segment, re.S)
        away = re.search(r'class="sb-team-away"[^>]*>(.*?)</span>', segment, re.S)
        state = re.search(r'class="(sb-st-[^" ]+)', segment[:1500])
        if not (path and home and away and state):
            continue
        if state[1] == 'sb-st-time':
            clock = re.search(r'class="sb-st-time"[^>]*>(\d{1,2}):(\d{2})', segment[:1500])
            if not clock:
                continue
            approximate = datetime.combine(day, datetime.min.time(), KST).replace(hour=int(clock[1]), minute=int(clock[2]))
            # shortcut: pregame lineups appear near kickoff; rescan this five-day window each run.
            if approximate - now > timedelta(hours=12):
                continue
        elif state[1] not in ('sb-st-live', 'sb-st-ft'):
            continue
        found.append((path[1], unescape(home[1]), unescape(away[1])))
    return found


def rendered_text(node):
    if isinstance(node, str):
        if node not in {'div', 'span', 'section', 'header', 'button', 'details', 'summary', 'p', 'h2', 'h3', 'ul', 'li', 'table', 'tr', 'td', 'th', 'svg', 'path'} and not node.startswith('$'):
            yield node
    elif isinstance(node, list):
        for child in node:
            yield from rendered_text(child)
    elif isinstance(node, dict) and 'children' in node:
        yield from rendered_text(node['children'])


def records_from_page(page):
    texts = []
    for match in CHUNK.finditer(page):
        try:
            chunk = json.loads(match[1])
            texts.append(list(rendered_text(json.loads(chunk.split(':', 1)[1]))))
        except (ValueError, IndexError):
            continue
    def pair(label):
        for parts in texts:
            if label not in parts:
                continue
            if label == '리그성적':
                index = parts.index(label)
                values = [parts[index - 1], parts[index + 1]]
            else:
                index = parts.index(label)
                values = [part for part in parts[index + 1:] if RECORD.fullmatch(part)][:2]
            if len(values) == 2 and all(RECORD.fullmatch(value) for value in values):
                return ['-'.join(RECORD.fullmatch(value).groups()) for value in values]
        return []
    forms = []
    for parts in texts:
        values = [part for part in parts if part in ('W', 'D', 'L')]
        if len(values) == 10:
            forms = values
            break
        if len(values) == 5 and len(forms) < 10:
            forms.extend(values)
    season, venue = pair('리그성적'), pair('홈 · 원정 강도 (홈 / 원정)')
    if len(forms) != 10 or len(season) != 2 or len(venue) != 2:
        return None
    return ({'home': forms[:5], 'away': forms[5:]},
            {'home': {'record': season[0], 'sideRecord': venue[0]},
             'away': {'record': season[1], 'sideRecord': venue[1]}})


def parse_detail(page, path, sport, names, now):
    schema = re.search(r'<script type="application/ld\+json">(\{.*?\})</script>', page, re.S)
    payload = re.search(r'/lineup\?d=([A-Za-z0-9_-]+)', page)
    if not (schema and payload):
        return None
    event = json.loads(schema[1])
    if event.get('@type') != 'SportsEvent' or not event.get('startDate'):
        return None
    kickoff = datetime.fromisoformat(event['startDate'].replace('Z', '+00:00'))
    if not now.date() <= kickoff.astimezone(KST).date() < now.date() + timedelta(days=5):
        return None
    # Early boards can retain a stale confirmed label; publish them as predictions until kickoff nears.
    until_kickoff = kickoff - now.astimezone(timezone.utc)
    if until_kickoff > timedelta(hours=12):
        return None
    encoded = payload[1]
    board = json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
    rosters = [board.get('h', {}).get('pl', []), board.get('a', {}).get('pl', [])]
    if any(len(players) != STARTERS[sport] for players in rosters):
        return None
    confirmed = until_kickoff <= timedelta(hours=2) and bool(re.search(r'확정 라인업', page))
    stats = records_from_page(page) if sport == '축구' else None
    if not stats:
        return None
    teams = []
    for side, name, players, key in zip(('home', 'away'), names, rosters, ('homeTeam', 'awayTeam')):
        team = event.get(key) or {}
        teams.append({'side': side, 'id': str(team.get('name') or name)[:240], 'name': name[:240],
                      'logo': str(team.get('logo') or '')[:240],
                      'players': [{'name': str(player[3])[:240], 'originalName': str(player[3])[:240],
                                   'position': '', 'number': '', 'flag': ''} for player in players if len(player) > 3 and player[3]],
                      'status': 'confirmed' if confirmed else 'predicted', 'injuries': [], 'pitcher': None})
    if any(len(team['players']) != STARTERS[sport] for team in teams):
        return None
    league = path.split('/')[2]
    return {'id': 'scorebase:' + path, 'eventId': path.rsplit('/', 1)[-1], 'league': league.lower(),
            'sport': sport, 'leagueName': str((event.get('organizer') or {}).get('name') or league)[:240],
            'kickoff': int(kickoff.timestamp() * 1000), 'teams': teams, 'logos': {},
            'recentForm': stats[0], 'records': stats[1], 'checkedAt': datetime.now(timezone.utc).isoformat(),
            'sourceFailed': False, 'note': ''}


def collect(now=None):
    now = now or datetime.now(KST)
    paths = {}
    boards = [(now.date() + timedelta(days=offset), query, sport)
              for offset in range(5) for query, sport in SPORTS.items()]
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch, f'/scores?sport={query}&date={day.isoformat()}&sort=board'): (day, sport)
                   for day, query, sport in boards}
        for future in as_completed(futures):
            day, sport = futures[future]
            for path, home, away in board_rows(future.result(), day, now):
                paths[path] = (sport, (home, away))
    matches = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fetch, path): (path, *details) for path, details in paths.items()}
        for future in as_completed(futures):
            path, sport, names = futures[future]
            try:
                match = parse_detail(future.result(), path, sport, names, now)
                if match:
                    matches.append(match)
            except (OSError, ValueError, KeyError, IndexError, TimeoutError) as error:
                print(f'Scorebase detail unavailable: {path}: {error}')
    return sorted(matches, key=lambda match: (match['kickoff'], match['id']))


if __name__ == '__main__':
    import pathlib
    target = pathlib.Path('dist/scorebase-lineups.json')
    matches = collect()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({'asOf': datetime.now(timezone.utc).isoformat(), 'matches': matches}, ensure_ascii=False) + '\n')
    print(f'Scorebase lineups: {len(matches)}')
