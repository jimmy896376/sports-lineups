"""Collect published match lineups from Scorebase for the current five KST days."""
import base64
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

BASE = 'https://www.xn--hy1bm7m1yevrd8pq.kr'
SPORTS = {'soccer': '축구', 'baseball': '야구', 'basketball': '농구',
          'volleyball': '배구', 'hockey': '하키', 'esports': 'e스포츠',
          'mma': 'UFC', 'tennis': '테니스', 'golf': '골프', 'f1': 'F1'}
STARTERS = {'축구': (11,), '야구': (9,), '농구': (5,), '배구': (6, 7), '하키': (19,)}
KST = ZoneInfo('Asia/Seoul')
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; NudeLineups/1.0)', 'Accept': 'text/html'}
ROW = re.compile(r'<div class="sb-row(?: [^"]*)?"')
CHUNK = re.compile(r'<script>self\.__next_f\.push\(\[1,("(?:\\.|[^"\\])*")\]\)</script>', re.S)
RECORD = re.compile(r'(\d+)승\s+(\d+)무\s+(\d+)패')
LEAGUE_LINK = re.compile(r'<a\b[^>]*href="/scores/([^"/?]+)"[^>]*>(.*?)</a>', re.S)


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


def board_upcoming(page, day, now):
    starts = list(ROW.finditer(page))
    for index, start in enumerate(starts):
        segment = page[start.start():starts[index + 1].start() if index + 1 < len(starts) else start.start() + 5000]
        clock = re.search(r'class="sb-st-time"[^>]*>(\d{1,2}):(\d{2})', segment[:1500])
        if not clock:
            continue
        kickoff = datetime.combine(day, datetime.min.time(), KST).replace(hour=int(clock[1]), minute=int(clock[2]))
        if kickoff <= now:
            continue
        path = re.search(r'href="/live/([^/"?]+)/', segment)
        tennis = re.search(r'href="/tennis/match/(atp|wta)/(\d+-\d{4})/', segment)
        league = path[1].lower() if path else f'{tennis[1]}-{tennis[2]}' if tennis else ''
        if league:
            yield league, int(kickoff.timestamp() * 1000)


def board_leagues(page):
    sidebar = re.search(r'<aside\b[^>]*aria-label="[^"]*(?:리그|대회) 목록"[^>]*>(.*?)</aside>', page, re.S)
    if not sidebar:
        return []
    leagues = []
    for entry in LEAGUE_LINK.finditer(sidebar[1]):
        name = re.search(r'<span\b[^>]*class="[^"]*\btruncate\b[^"]*"[^>]*>(.*?)</span>', entry[2], re.S)
        if name:
            leagues.append({'id': entry[1].lower(), 'name': unescape(re.sub(r'<[^>]+>', '', name[1])).strip()})
    for entry in re.finditer(r'<a\b[^>]*href="/scores\?[^" ]*?league=([^&"]+)[^"]*"[^>]*>(.*?)</a>', sidebar[1], re.S):
        name = re.search(r'<span\b[^>]*class="[^"]*\btruncate\b[^"]*"[^>]*>(.*?)</span>', entry[2], re.S)
        if name:
            leagues.append({'id': entry[1].lower(), 'name': unescape(re.sub(r'<[^>]+>', '', name[1])).strip()})
    return [league for league in leagues if league['name']]


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
    def pair(label, valid=lambda values: True):
        for parts in texts:
            if label not in parts:
                continue
            if label == '리그성적':
                index = parts.index(label)
                values = [parts[index - 1], parts[index + 1]]
            else:
                index = parts.index(label)
                values = [part for part in parts[index + 1:] if RECORD.fullmatch(part)][:2]
            if len(values) == 2 and all(RECORD.fullmatch(value) for value in values) and valid(values):
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
    season = pair('리그성적')
    def fits_season(values):
        return all(all(int(part) <= int(total) for part, total in zip(RECORD.fullmatch(value).groups(), overall.split('-')))
                   for value, overall in zip(values, season))
    venue = pair('홈 · 원정 강도 (홈 / 원정)', fits_season) if season else []
    if len(forms) != 10 or len(season) != 2 or len(venue) != 2:
        return None
    return ({'home': forms[:5], 'away': forms[5:]},
            {'home': {'record': season[0], 'sideRecord': venue[0]},
             'away': {'record': season[1], 'sideRecord': venue[1]}})


class LineupTree(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = {'tag': '', 'attrs': {}, 'children': []}
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = {'tag': tag, 'attrs': dict(attrs), 'children': []}
        self.stack[-1]['children'].append(node)
        if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'wbr'}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index]['tag'] == tag:
                del self.stack[index:]
                break

    def handle_data(self, value):
        self.stack[-1]['children'].append(value)


def descendants(node):
    if isinstance(node, dict):
        yield node
        for child in node['children']:
            yield from descendants(child)


def node_text(node):
    if isinstance(node, str):
        return node
    return ''.join(node_text(child) for child in node['children'])


def html_rosters(page):
    """Read the two published pregame roster columns, never infer names from a schedule."""
    tree = LineupTree()
    tree.feed(page)
    for section in descendants(tree.root):
        if section['tag'] not in {'section', 'div'}:
            continue
        if section['tag'] == 'div' and section['attrs'].get('data-live-sec') != 'lineup':
            continue
        headings = [node_text(node).strip() for node in descendants(section)
                    if node['tag'] == 'h2' or
                    (node['tag'] == 'div' and all(isinstance(child, str) for child in node['children']))]
        if not any(label in {'예상 선발 라인업', '예상 출전 명단'} for label in headings):
            continue
        for grid in descendants(section):
            if grid['tag'] != 'div' or 'sm:grid-cols-2' not in grid['attrs'].get('class', '').split():
                continue
            columns = [child for child in grid['children'] if isinstance(child, dict) and child['tag'] == 'div']
            if len(columns) != 2:
                continue
            rosters = [[node_text(link).strip() for link in descendants(column)
                        if link['tag'] == 'a' and link['attrs'].get('href', '').startswith('/players/')]
                       for column in columns]
            if all(rosters) and all(len(players) == len(set(players)) for players in rosters):
                return rosters
    return None


def parse_detail(page, path, sport, names, now):
    schema = re.search(r'<script type="application/ld\+json">(\{.*?\})</script>', page, re.S)
    payload = re.search(r'/lineup\?d=([A-Za-z0-9_-]+)', page)
    if not schema:
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
    if payload:
        encoded = payload[1]
        board = json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
        rosters = [[str(player[3]).strip() for player in board.get(side, {}).get('pl', [])
                    if len(player) > 3 and str(player[3]).strip()] for side in ('h', 'a')]
    else:
        rosters = html_rosters(page)
    if not rosters or any(len(players) not in STARTERS[sport] for players in rosters):
        return None
    confirmed = until_kickoff <= timedelta(hours=2) and bool(re.search(r'확정 라인업', page))
    stats = records_from_page(page) if sport == '축구' else None
    if sport == '축구' and not stats:
        return None
    teams = []
    for side, name, players, key in zip(('home', 'away'), names, rosters, ('homeTeam', 'awayTeam')):
        team = event.get(key) or {}
        teams.append({'side': side, 'id': str(team.get('name') or name)[:240], 'name': name[:240],
                      'logo': str(team.get('logo') or '')[:240],
                      'players': [{'name': player[:240], 'originalName': player[:240],
                                   'position': '', 'number': '', 'flag': ''} for player in players],
                      'status': 'confirmed' if confirmed else 'predicted', 'injuries': [], 'pitcher': None})
    league = path.split('/')[2]
    return {'id': 'scorebase:' + path, 'eventId': path.rsplit('/', 1)[-1], 'league': league.lower(),
            'sport': sport, 'leagueName': str((event.get('organizer') or {}).get('name') or league)[:240],
            'kickoff': int(kickoff.timestamp() * 1000), 'teams': teams, 'logos': {},
            'recentForm': stats[0] if stats else {}, 'records': stats[1] if stats else {},
            'checkedAt': datetime.now(timezone.utc).isoformat(),
            'sourceFailed': False, 'note': ''}


def collect(now=None):
    now = now or datetime.now(KST)
    paths = {}
    leagues = {sport: {} for sport in SPORTS.values()}
    upcoming = {sport: {} for sport in SPORTS.values()}
    boards = [(now.date() + timedelta(days=offset), query, sport)
              for offset in range(5) for query, sport in SPORTS.items()]
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch, f'/scores?sport={query}&date={day.isoformat()}&sort=board'): (day, sport)
                   for day, query, sport in boards}
        for future in as_completed(futures):
            day, sport = futures[future]
            page = future.result()
            for league in board_leagues(page):
                leagues[sport][league['id']] = league['name']
            for league, kickoff in board_upcoming(page, day, now):
                upcoming[sport][league] = max(kickoff, upcoming[sport].get(league, 0))
            if sport in STARTERS:
                for path, home, away in board_rows(page, day, now):
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
    return sorted(matches, key=lambda match: (match['kickoff'], match['id'])), {
        sport: [{'id': key, 'name': name, **({'lastScheduledKickoff': upcoming[sport][key]} if key in upcoming[sport] else {})}
                for key, name in sorted(entries.items(), key=lambda item: item[1])]
        for sport, entries in leagues.items()}


if __name__ == '__main__':
    import pathlib
    target = pathlib.Path('dist/scorebase-lineups.json')
    matches, leagues = collect()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({'asOf': datetime.now(timezone.utc).isoformat(), 'matches': matches,
                                  'leagues': leagues}, ensure_ascii=False) + '\n')
    print(f'Scorebase lineups: {len(matches)}; leagues: {sum(map(len, leagues.values()))}')
