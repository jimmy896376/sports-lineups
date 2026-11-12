#!/usr/bin/env python3
"""Save dated, attributed lineup predictions from public lineup pages."""
import html
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
WINDOW_DAYS = 5
SOURCES = {
    'ucl': ('UCL', 'soccer'), 'epl': ('EPL', 'soccer'),
    'laliga': ('LIGA', 'soccer'), 'bundesliga': ('BUND', 'soccer'),
    'seriea': ('SERI', 'soccer'), 'ligue1': ('FRAN', 'soccer'),
    'mls': ('MLS', 'soccer'), 'ligamx': ('LMX', 'soccer'), 'wnba': ('', 'wnba'),
    'nba': ('', 'nba'), 'mlb': ('', 'mlb'),
}

KBL_LOGO_CODES = {'원주 DB': 'db', '서울 삼성': 'ss', '고양 소노': 'sono',
                  '서울 SK': 'sk', '창원 LG': 'lg', '안양 정관장': 'kgc',
                  '부산 KCC': 'kcc', '수원 KT': 'kt', '대구 한국가스공사': 'pega',
                  '울산 현대모비스': 'hd'}
WKBL_LOGO_CODES = {'KB스타즈': '01', '삼성생명': '03', '우리은행': '05',
                   '신한은행': '07', '하나은행': '09', 'BNK 썸': '11'}


def basketball_logo(league, name):
    if league == 'kbl':
        code = KBL_LOGO_CODES.get(name)
        return f'https://www.kbl.or.kr/assets/img/ico/logo/ic-{code}.svg' if code else ''
    code = WKBL_LOGO_CODES.get(name)
    return f'https://www.wkbl.or.kr/static/images/team/teamlogo_{code}.png' if code else ''


def source_url(league, code, kind):
    if kind == 'soccer':
        return f'https://www.rotowire.com/soccer/lineups.php?league={code}'
    if kind == 'nba':
        return 'https://www.rotowire.com/basketball/nba-lineups.php'
    if kind == 'wnba':
        return 'https://www.rotowire.com/wnba/lineups.php'
    return 'https://www.rotowire.com/baseball/daily-lineups.php'


def scrape_page(league, code, kind):
    import urllib.request
    request = urllib.request.Request(source_url(league, code, kind), headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=20) as response:
        page = response.read().decode('utf-8', errors='replace')
    blocks = re.split(r'(?=<div class="lineup is-(?:nba|wnba|soccer|mlb))', page)[1:]
    results = []
    for block in blocks:
        teams = {}
        names = {}
        for role, abbr in re.findall(r'<(?:a|div)[^>]*class="lineup__team is-(home|visit)"[^>]*>.*?<div class="lineup__abbr">([^<]+)</div>', block, re.S):
            teams['away' if role == 'visit' else 'home'] = html.unescape(abbr.strip())
        for role, name in re.findall(r'<div class="lineup__mteam is-(home|visit)"[^>]*>\s*([^<]+)', block):
            names['away' if role == 'visit' else 'home'] = html.unescape(name.strip())
        if len(teams) != 2:
            continue
        time_match = re.search(r'<div class="lineup__time">(.*?)</div>', block, re.S)
        if not time_match:
            continue
        time_text = re.sub(r'<[^>]+>|&nbsp;', ' ', time_match.group(1)).strip()
        if kind != 'soccer':
            # Daily NBA/MLB pages identify the date in the page heading.
            date_match = re.search(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}', page[300000:])
            if not date_match:
                continue
            time_text = date_match.group(0).replace(',', '') + ' ' + time_text
        else:
            time_text = time_text + f' {datetime.now(timezone.utc).year}'
            time_text = re.sub(r' ET (\d{4})$', r' \1 ET', time_text)
        try:
            moment = datetime.strptime(time_text.replace(' ET', ''), '%B %d %I:%M %p %Y' if kind == 'soccer' else '%B %d %Y %I:%M %p')
            kickoff = moment.replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
        except ValueError:
            continue
        rosters = {}
        injuries = {}
        injury_details = {}
        statuses = {}
        for role in ('home', 'visit'):
            side = 'away' if role == 'visit' else 'home'
            roster_match = re.search(r'<ul class="lineup__list is-' + role + r'".*?</ul>', block, re.S)
            if not roster_match:
                continue
            roster_html = roster_match.group(0)
            lineup_html = roster_html.split('<li class="lineup__title')[0]
            statuses[side] = 'confirmed' if 'is-confirmed' in lineup_html else 'predicted'
            players = []
            for item in re.findall(r'<li class="lineup__player[^>]*>.*?</li>', lineup_html, re.S):
                name = re.search(r'<a title="([^"]+)"', item)
                if not name:
                    continue
                position = re.search(r'<div class="lineup__pos[^>]*>([^<]+)', item)
                flag = re.search(r'<span class="lineup__inj">([^<]+)', item)
                players.append({'name': html.unescape(name.group(1)), 'position': position.group(1).strip() if position else '', 'flag': flag.group(1).strip() if flag else ''})
            rosters[side] = players
            injury_html = roster_html[len(lineup_html):]
            injuries[side] = [html.unescape(name) for name in re.findall(r'<li class="lineup__player[^>]*>.*?<a title="([^"]+)"', injury_html, re.S)][:8]
            injury_details[side] = []
            for row in re.findall(r'<li class="lineup__player[^>]*>.*?</li>', injury_html, re.S):
                name = re.search(r'<a title="([^"]+)"', row)
                if not name:
                    continue
                flag = re.search(r'<span class="lineup__inj[^>]*>([^<]+)', row)
                injury_details[side].append({'name': html.unescape(name.group(1)), 'status': html.unescape(flag.group(1).strip()) if flag else ''})
        expected = 11 if kind == 'soccer' else 9 if kind == 'mlb' else 5
        if any(len(rosters.get(side, [])) != expected for side in ('home', 'away')):
            continue
        logos = {side: 'https://a.espncdn.com/i/teamlogos/soccer/500/493.png'
                 for side, name in names.items() if league == 'ucl' and 'Shakhtar' in name}
        for role, team_html in re.findall(r'<(?:a|div)[^>]*class="lineup__team is-(home|visit)"[^>]*>(.*?)<div class="lineup__abbr">', block, re.S):
            image = re.search(r'<img[^>]*class="lineup__logo"[^>]*src="([^"]+)"', team_html)
            if image and image.group(1).startswith('https://'):
                logos['away' if role == 'visit' else 'home'] = html.unescape(image.group(1))
        results.append({'league': league, 'kickoff': kickoff, 'teams': teams, 'names': names, 'logos': logos, 'lineups': rosters, 'injuries': injuries, 'injuryDetails': injury_details, 'statuses': statuses, 'source': source_url(league, code, kind)})
    return results


def scrape_europa():
    import urllib.request
    url = 'https://starting11.com/europa-league'
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=20) as response:
        page = response.read().decode('utf-8', errors='replace')
    results = []
    for article in re.findall(r'<article class="rounded-xl border border-white/\[0\.07\].*?</article>', page, re.S):
        title = re.search(r'<h3[^>]*>([^<]+) predicted lineups</h3>', article)
        time_match = re.search(r'Kick-off is (\d{1,2}:\d{2}) BST on (\w{3} \d{1,2} \w{3})', article)
        if not title or not time_match or ' vs ' not in title.group(1):
            continue
        home_name, away_name = title.group(1).split(' vs ', 1)
        try:
            moment = datetime.strptime(time_match.group(2) + f' {datetime.now(timezone.utc).year} ' + time_match.group(1), '%a %d %b %Y %H:%M')
            kickoff = moment.replace(tzinfo=ZoneInfo('Europe/London')).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
        except ValueError:
            continue
        lineups = {}
        for side, name in [('home', home_name), ('away', away_name)]:
            match = re.search(r'<strong[^>]*>' + re.escape(name) + r' predicted lineup[^<]*</strong>\s*<!-- -->\s*(.*?)</p>', article, re.S)
            if not match:
                break
            names = [html.unescape(value.strip(' .')) for value in re.split(r'[;,]', match.group(1)) if value.strip(' .')]
            lineups[side] = [{'name': name, 'position': '', 'flag': ''} for name in names]
        if len(lineups.get('home', [])) != 11 or len(lineups.get('away', [])) != 11:
            continue
        results.append({'league': 'uel', 'kickoff': kickoff, 'names': {'home': home_name, 'away': away_name}, 'teams': {}, 'lineups': lineups, 'injuries': {}, 'statuses': {'home': 'predicted', 'away': 'predicted'}, 'source': url})
    return results


def fetch_text(url):
    import urllib.request
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode('utf-8', errors='replace')


def fetch_json(url):
    return json.loads(fetch_text(url))


ESPN_INJURY_PATHS = {
    'ucl': 'soccer/uefa.champions', 'uel': 'soccer/uefa.europa',
    'epl': 'soccer/eng.1', 'championship': 'soccer/eng.2', 'laliga': 'soccer/esp.1',
    'eredivisie': 'soccer/ned.1', 'jupiler': 'soccer/bel.1', 'primeira': 'soccer/por.1',
    'scottish': 'soccer/sco.1', 'bundesliga': 'soccer/ger.1', 'seriea': 'soccer/ita.1',
    'ligue1': 'soccer/fra.1', 'j1': 'soccer/jpn.1', 'mls': 'soccer/usa.1',
    'nba': 'basketball/nba', 'wnba': 'basketball/wnba', 'mlb': 'baseball/mlb',
    'nhl': 'hockey/nhl',
}

ESPN_INTERNATIONAL = {
    'uefa_nl': ('soccer/uefa.nations', 'UEFA 네이션스 리그'),
    'intl_friendly': ('soccer/fifa.friendly', '국가대표 친선'),
    'fifa_world': ('soccer/fifa.world', 'FIFA 월드컵'),
    'afc_asian_cup': ('soccer/afc.asian.cup', 'AFC 아시안컵'),
    'caf_nations': ('soccer/caf.nations', '아프리카 네이션스컵'),
    'uefa_euro': ('soccer/uefa.euro', 'UEFA 유로'),
    'uefa_u21': ('soccer/uefa.euro_u21', 'UEFA U21 챔피언십'),
}
NATIONAL_TEAM_KO = {
    'Albania': '알바니아', 'Andorra': '안도라', 'Armenia': '아르메니아',
    'Austria': '오스트리아', 'Azerbaijan': '아제르바이잔', 'Belarus': '벨라루스',
    'Belgium': '벨기에', 'Bosnia-Herzegovina': '보스니아 헤르체고비나',
    'Bulgaria': '불가리아', 'Croatia': '크로아티아', 'Cyprus': '키프로스',
    'Czechia': '체코', 'Denmark': '덴마크', 'England': '잉글랜드',
    'Estonia': '에스토니아', 'Faroe Islands': '페로 제도', 'Finland': '핀란드',
    'France': '프랑스', 'Georgia': '조지아', 'Germany': '독일',
    'Gibraltar': '지브롤터', 'Greece': '그리스', 'Hungary': '헝가리',
    'Iceland': '아이슬란드', 'Israel': '이스라엘', 'Italy': '이탈리아',
    'Kazakhstan': '카자흐스탄', 'Kosovo': '코소보', 'Latvia': '라트비아',
    'Liechtenstein': '리히텐슈타인', 'Lithuania': '리투아니아',
    'Luxembourg': '룩셈부르크', 'Malta': '몰타', 'Moldova': '몰도바',
    'Montenegro': '몬테네그로', 'Netherlands': '네덜란드',
    'New Zealand': '뉴질랜드', 'North Macedonia': '북마케도니아',
    'Northern Ireland': '북아일랜드', 'Norway': '노르웨이',
    'Poland': '폴란드', 'Portugal': '포르투갈',
    'Republic of Ireland': '아일랜드', 'Romania': '루마니아',
    'Russia': '러시아', 'San Marino': '산마리노', 'Scotland': '스코틀랜드',
    'Serbia': '세르비아', 'Slovakia': '슬로바키아', 'Slovenia': '슬로베니아',
    'Spain': '스페인', 'Sweden': '스웨덴', 'Switzerland': '스위스',
    'Türkiye': '튀르키예', 'Ukraine': '우크라이나',
    'Uzbekistan': '우즈베키스탄', 'Wales': '웨일스', 'India': '인도',
}


def international_item(event, summary, league):
    """Use ESPN's exact kickoff and published starting elevens only."""
    competitors = (event.get('competitions') or [{}])[0].get('competitors') or []
    rosters = summary.get('rosters') or []
    if len(competitors) != 2 or len(rosters) != 2:
        return None
    by_side = {entry.get('homeAway'): entry for entry in competitors}
    roster_by_side = {entry.get('homeAway'): entry for entry in rosters}
    if set(by_side) != {'home', 'away'} or set(roster_by_side) != {'home', 'away'}:
        return None
    names, teams, logos, lineups = {}, {}, {}, {}
    for side in ('home', 'away'):
        team = by_side[side].get('team') or {}
        name = team.get('displayName') or ''
        players = [row for row in roster_by_side[side].get('roster', []) if row.get('starter') is True]
        if not name or len(players) != 11:
            return None
        names[side] = NATIONAL_TEAM_KO.get(name, name)
        teams[side] = team.get('abbreviation') or name
        logos[side] = team.get('logo') or ''
        lineups[side] = [{'name': row['athlete']['displayName'],
                          'position': (row.get('position') or {}).get('abbreviation', '')}
                         for row in players if (row.get('athlete') or {}).get('displayName')]
        if len(lineups[side]) != 11:
            return None
    return {'league': league, 'kickoff': event['date'], 'espnEventId': str(event['id']),
            'teams': teams, 'names': names, 'logos': logos, 'lineups': lineups,
            'injuries': {}, 'statuses': {'home': 'confirmed', 'away': 'confirmed'},
            'source': 'https://www.espn.com/soccer/match/_/gameId/' + str(event['id'])}


def scrape_espn_international(league, path, target_days):
    start = datetime.combine(min(target_days), datetime.min.time(), ZoneInfo('Asia/Seoul')).astimezone(timezone.utc).date()
    end = datetime.combine(max(target_days) + timedelta(days=1), datetime.min.time(), ZoneInfo('Asia/Seoul')).astimezone(timezone.utc).date()
    entries = []
    now = datetime.now(timezone.utc)
    boards_read = 0
    for offset in range((end - start).days + 1):
        day = start.fromordinal(start.toordinal() + offset).strftime('%Y%m%d')
        try:
            board = fetch_json(f'https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard?dates={day}&limit=500')
            boards_read += 1
        except Exception as error:
            print(league, day, 'scoreboard unavailable:', error)
            continue
        for event in board.get('events', []):
            kickoff = datetime.fromisoformat(event['date'].replace('Z', '+00:00'))
            if kickoff.astimezone(ZoneInfo('Asia/Seoul')).date() not in target_days or kickoff - now > timedelta(hours=12):
                continue
            try:
                summary = fetch_json(f'https://site.api.espn.com/apis/site/v2/sports/{path}/summary?event={event["id"]}')
            except Exception as error:
                print(league, event['id'], 'lineup unavailable:', error)
                continue
            item = international_item(event, summary, league)
            if item:
                entries.append(item)
    if not boards_read:
        raise OSError('All international scoreboards unavailable')
    return entries


def injury_name_key(value):
    value = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', value)


def fetch_espn_injury_reports(path):
    """Return current ESPN injury details indexed by team abbreviation."""
    data = fetch_json(f'https://site.api.espn.com/apis/site/v2/sports/{path}/injuries')
    teams = {}
    for group in data.get('injuries', []):
        team = group.get('displayName') or (group.get('team') or {}).get('displayName', '')
        code = ((group.get('team') or {}).get('abbreviation') or group.get('abbreviation') or '').upper()
        entries = {}
        for item in group.get('injuries', []):
            athlete = item.get('athlete') or {}
            injury_team = item.get('team') or athlete.get('team') or {}
            code = (code or injury_team.get('abbreviation') or '').upper()
            team = team or injury_team.get('displayName', '')
            name = athlete.get('displayName') or athlete.get('fullName')
            if not name:
                continue
            details = item.get('details') or {}
            injury_type = item.get('type') or {}
            record = {
                'name': name,
                'status': item.get('status') or injury_type.get('description', ''),
                'part': details.get('type', ''),
                'location': details.get('location', ''),
                'side': details.get('side', ''),
                'condition': details.get('detail', ''),
                'returnDate': details.get('returnDate', ''),
                'comment': item.get('shortComment', ''),
                'updatedAt': item.get('date', ''),
            }
            key = injury_name_key(name)
            if key not in entries or record['updatedAt'] > entries[key]['updatedAt']:
                entries[key] = record
        if code:
            teams[code] = {'name': team, 'records': list(entries.values())}
    return teams


def enrich_injury_details(payload):
    """Attach verified status/body details when ESPN publishes them."""
    reports = {}
    for league, path in ESPN_INJURY_PATHS.items():
        try:
            reports[league] = fetch_espn_injury_reports(path)
            print('injuries', league, sum(len(team['records']) for team in reports[league].values()))
        except Exception as error:
            print('injuries source unavailable:', league, error)
            reports[league] = {}

    for league, events in [('items', payload.get('items', []))]:
        for item in events:
            code = item.get('league')
            if code not in ESPN_INJURY_PATHS:
                continue
            report = reports.get(code, {})
            details = {}
            existing = item.setdefault('injuries', {})
            existing_details = item.setdefault('injuryDetails', {})
            for side in ('home', 'away'):
                team_code = str((item.get('teams') or {}).get(side, '')).upper()
                team_report = report.get(team_code, {})
                report_rows = team_report.get('records', [])
                listed_names = existing.get(side) or []
                listed_rows = existing_details.get(side) or [{'name': name, 'status': ''} for name in listed_names]
                if listed_rows:
                    by_key = {injury_name_key(row.get('name')): row for row in report_rows}
                    selected = []
                    for row in listed_rows:
                        match = by_key.get(injury_name_key(row.get('name')))
                        selected.append({**row, **match} if match else row)
                else:
                    selected = report_rows
                details[side] = selected
                if selected:
                    existing[side] = [row['name'] for row in selected]
            item['injuryDetails'] = details

    # Domestic data currently lacks an injury feed. Keep this field present for
    # consistent rendering; never infer an injury from a missing lineup slot.
    for entries in (payload.get('domestic') or {}).values():
        for entry in entries:
            if isinstance(entry, dict) and isinstance(entry.get('prediction'), dict):
                entry['prediction'].setdefault('injuryDetails', {'home': [], 'away': []})


class DailyFaceoffParser(__import__('html.parser', fromlist=['HTMLParser']).HTMLParser):
    def __init__(self):
        super().__init__()
        self.section = None
        self.anchor = None
        self.players = {'forwards': [], 'defense': [], 'goalies': []}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'span' and attrs.get('id') in self.players:
            self.section = attrs['id']
        if tag == 'a' and attrs.get('href', '').startswith('/players/news/'):
            self.anchor = {'text': [], 'alt': ''}
        elif tag == 'img' and self.anchor is not None:
            self.anchor['alt'] = attrs.get('alt', '')

    def handle_data(self, data):
        if self.anchor is not None:
            self.anchor['text'].append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.anchor is not None:
            name = ' '.join(' '.join(self.anchor['text']).split()).strip() or self.anchor['alt'].strip()
            if name and self.section and name.casefold() not in {item.casefold() for item in self.players[self.section]}:
                self.players[self.section].append(name.title() if name.isupper() else name)
            self.anchor = None


def scrape_nhl_dailyfaceoff():
    """Use current Daily Faceoff lines and goalie depth chart for NHL six-player projections."""
    from datetime import timedelta
    from urllib.parse import quote
    eastern = ZoneInfo('America/New_York')
    today = datetime.now(eastern).date()
    scores = {}
    for offset in range(WINDOW_DAYS):
        day = today + timedelta(days=offset)
        board = fetch_json(f'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates={day:%Y%m%d}&limit=500')
        for event in board.get('events', []):
            scores[event.get('id')] = event
    pages = {}
    results = []
    for event in scores.values():
        competition = (event.get('competitions') or [{}])[0]
        competitors = competition.get('competitors', [])
        if len(competitors) != 2:
            continue
        teams, names, logos = {}, {}, {}
        lineups = {}
        for competitor in competitors:
            side = str(competitor.get('homeAway') or '').strip().lower()
            team = competitor.get('team', {})
            display = team.get('displayName') or team.get('name') or ''
            slug = re.sub(r'[^a-z0-9]+', '-', display.lower()).strip('-')
            if not side or not display or not slug:
                continue
            teams[side] = team.get('abbreviation', '')
            names[side] = display
            logo = team.get('logo') or next((item.get('href') for item in team.get('logos', []) if item.get('href')), '')
            logos[side] = logo if isinstance(logo, str) and logo.startswith('https://') else ''
            if slug not in pages:
                try:
                    parser = DailyFaceoffParser()
                    parser.feed(fetch_text(f'https://www.dailyfaceoff.com/teams/{quote(slug)}/line-combinations'))
                    pages[slug] = parser.players
                except Exception as error:
                    print('nhl Daily Faceoff source unavailable:', slug, error)
                    pages[slug] = {}
            roster = pages[slug]
            forward = roster.get('forwards', [])
            defense = roster.get('defense', [])
            goalies = roster.get('goalies', [])
            probable_goalies = [item.get('athlete', {}).get('displayName') or item.get('athlete', {}).get('fullName')
                                for item in competitor.get('probables', [])
                                if item.get('athlete', {}).get('position') in ('G', 'Goalie', 'Goaltender')]
            goalie = next((item.get('athlete', {}).get('displayName') for item in competitor.get('probables', [])
                           if item.get('athlete', {}).get('position') in ('G', 'Goalie', 'Goaltender')
                           and item.get('status', {}).get('type') == 'confirmed'), None)
            goalie = goalie or next((name for name in probable_goalies if name), None) or (goalies[0] if goalies else None)
            selected = forward[:3] + defense[:2] + ([goalie] if goalie else [])
            if len(selected) == 6:
                lineups[side] = [{'name': player, 'position': '', 'flag': ''} for player in selected]
        if len(lineups) != 2 or len(names) != 2:
            continue
        results.append({'league': 'nhl', 'kickoff': event.get('date'), 'teams': teams, 'names': names, 'logos': logos,
                        'lineups': lineups, 'injuries': {}, 'statuses': {'home': 'predicted', 'away': 'predicted'},
                        'note': 'Daily Faceoff 1선·1수비 조합과 첫 골리 기준 예상',
                        'source': 'https://www.dailyfaceoff.com/teams'})
    return results


def scrape_fotmob_kleague(league_id, key):
    """Use FotMob schedule and its lastStarting11 roster for K League projections."""
    from urllib.parse import urlencode
    today = datetime.now(ZoneInfo('Asia/Seoul')).date()
    end = today.fromordinal(today.toordinal() + WINDOW_DAYS)
    query = urlencode({'id': league_id, 'ccode3': 'KOR', 'season': today.year})
    data = fetch_json('https://www.fotmob.com/api/data/leagues?' + query)
    fixture_list = data.get('fixtures', {}).get('allMatches', [])
    events = []
    for match in fixture_list:
        status = match.get('status', {})
        kickoff_text = status.get('utcTime')
        if not kickoff_text:
            continue
        kickoff = datetime.fromisoformat(kickoff_text.replace('Z', '+00:00'))
        local = kickoff.astimezone(ZoneInfo('Asia/Seoul'))
        if not today <= local.date() < end or status.get('finished'):
            continue
        home, away = match.get('home', {}), match.get('away', {})
        if not home.get('id') or not away.get('id'):
            continue
        detail = fetch_json('https://www.fotmob.com/api/data/matchDetails?' + urlencode({'matchId': match['id']}))
        lineup = detail.get('content', {}).get('lineup') or detail.get('lineup') or {}
        def players(team):
            result = []
            for row in team.get('starters', []):
                player = row.get('player', row)
                if player.get('name'):
                    result.append({'name': player['name'], 'number': player.get('shirtNumber', ''), 'position': row.get('position', ''), 'flag': ''})
            return result[:11]
        rosters = {'home': players(lineup.get('homeTeam', {})), 'away': players(lineup.get('awayTeam', {}))}
        names = {'home': home.get('name', ''), 'away': away.get('name', '')}
        logos = {side: next((team.get('imageUrl', '') for team in detail.get('header', {}).get('teams', [])
                             if str(team.get('id')) == str(club['id']) and team.get('imageUrl', '').startswith('https://')), '')
                 for side, club in (('home', home), ('away', away))}
        utc = kickoff.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
        competitors = [
            {'homeAway': 'home', 'team': {'id': home['id'], 'displayName': names['home'], 'shortDisplayName': names['home'], 'abbreviation': str(home['id']), 'logo': logos['home']}},
            {'homeAway': 'away', 'team': {'id': away['id'], 'displayName': names['away'], 'shortDisplayName': names['away'], 'abbreviation': str(away['id']), 'logo': logos['away']}}
        ]
        prediction = {'league': key, 'kickoff': utc, 'names': names, 'teams': {'home': str(home['id']), 'away': str(away['id'])},
            'logos': logos, 'lineups': rosters, 'injuries': {}, 'statuses': {'home': 'predicted', 'away': 'predicted'},
            'note': 'FotMob 최근 선발 11명 기준 예상', 'source': 'https://www.fotmob.com'}
        prediction['recentForm'], prediction['records'] = fotmob_records(fixture_list, match)
        events.append({'event': {'id': str(match['id']), 'date': utc, 'competitions': [{'competitors': competitors}]}, 'prediction': prediction, 'confirmed': False})
    return events


def fotmob_records(fixtures, upcoming):
    """Use completed matches in the same season before kickoff; W-D-L for football."""
    kickoff = upcoming['status']['utcTime']
    history = []
    for game in fixtures:
        status = game.get('status', {})
        if not status.get('finished') or status.get('cancelled') or status.get('awarded') or not status.get('utcTime') or status['utcTime'] >= kickoff:
            continue
        score = re.fullmatch(r'\s*(\d+)\s*[-–:]\s*(\d+)\s*', status.get('scoreStr', ''))
        if score:
            history.append((status['utcTime'], game, int(score[1]), int(score[2])))
    history.sort(key=lambda row: row[0])
    forms, records = {}, {}
    for side in ('home', 'away'):
        team_id = str(upcoming[side]['id'])
        results = []
        for _, game, home_score, away_score in history:
            venue = next((position for position in ('home', 'away') if str(game.get(position, {}).get('id')) == team_id), None)
            if venue:
                own, opponent = (home_score, away_score) if venue == 'home' else (away_score, home_score)
                results.append((venue, 'W' if own > opponent else 'L' if own < opponent else 'D'))
        if results:
            forms[side] = [result for _, result in results[-5:]]
            def tally(rows):
                return '-'.join(str(sum(result == mark for _, result in rows)) for mark in ('W', 'D', 'L'))
            records[side] = {'record': tally(results), 'sideRecord': tally([row for row in results if row[0] == side])}
    return forms, records


def scorebase_venue_records(league, page=None):
    """Read season and venue records from Scorebase's team statistics table."""
    if page is None:
        try:
            page = fetch_text(f'https://www.xn--hy1bm7m1yevrd8pq.kr/leagues/{league}')
        except OSError as error:
            print(league, 'venue records unavailable:', error)
            return {}
    table = re.search(r'팀 통계</h2>.*?<table[^>]*>(.*?)</table>', page, re.S)
    if not table:
        return {}
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table.group(1), re.S)
    def cells(row):
        return [html.unescape(re.sub(r'<[^>]+>', '', cell)).strip()
                for cell in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.S)]
    if not rows:
        return {}
    headers = cells(rows[0])
    if not all(key in headers for key in ('승-패', '홈', '원정')):
        return {}
    indices = [headers.index(key) for key in ('승-패', '홈', '원정')]
    records = {}
    for row in rows[1:]:
        values = cells(row)
        name = re.search(r'<a\b[^>]*>(.*?)</a>', row, re.S)
        if not name or len(values) <= max(indices):
            continue
        team = re.sub(r'^\d+\s*', '', html.unescape(re.sub(r'<[^>]+>', '', name.group(1)))).strip()
        overall, home, away = (values[index] for index in indices)
        if not all(re.fullmatch(r'\d+-\d+', value) for value in (overall, home, away)):
            continue
        if any(sum(int(value.split('-')[part]) for value in (home, away)) != int(overall.split('-')[part]) for part in (0, 1)):
            continue
        records[team] = {'record': overall, 'home': home, 'away': away}
    return records


def scrape_khl():
    """Import five-day KHL fixtures from the public KHL mobile API."""
    from urllib.parse import urlencode
    today = datetime.now(ZoneInfo('Asia/Seoul')).date()
    start = datetime.combine(today, datetime.min.time(), ZoneInfo('Asia/Seoul')).astimezone(timezone.utc).timestamp()
    end = start + WINDOW_DAYS * 86400
    query = urlencode({'q[start_at_gt_time_from_unixtime]': int(start), 'q[start_at_lt_time_from_unixtime]': int(end), 'order_direction': 'asc', 'locale': 'en'}, safe='[]')
    raw = fetch_json('https://khl.api.webcaster.pro/api/khl_mobile/events_v2.json?' + query)
    events = []
    rows = raw if isinstance(raw, list) else raw.get('events', [])
    upcoming = []
    for row in rows:
        game = row.get('event', row)
        if game.get('type_id') not in (18, 24) or not game.get('start_at'):
            continue
        upcoming.append(game)
    upcoming_teams = {str(team.get('id')) for game in upcoming for team in (game.get('team_a', {}), game.get('team_b', {})) if team.get('id')}
    recent_starters = {}
    history = []
    for page in range(1, 7):
        history_query = urlencode({'q[start_at_gt_time_from_unixtime]': int(start - 35 * 86400), 'q[start_at_lt_time_from_unixtime]': int(start), 'order_direction': 'desc', 'locale': 'en', 'page': page}, safe='[]')
        try:
            history_raw = fetch_json('https://khl.api.webcaster.pro/api/khl_mobile/events_v2.json?' + history_query)
        except OSError as error:
            print('khl recent results unavailable:', error)
            break
        batch = history_raw if isinstance(history_raw, list) else history_raw.get('events', [])
        history.extend(batch)
        if len(batch) < 16:
            break
    season = f'{today.year}/{today.year + 1}' if today.month >= 7 else f'{today.year - 1}/{today.year}'
    try:
        table = fetch_json('https://khl.api.webcaster.pro/api/khl_mobile/tables_v2.json?locale=en')
    except OSError as error:
        print('khl season standings unavailable:', error)
        table = []
    stage = next((stage for year in table if year.get('season') == season for stage in year.get('stages', []) if stage.get('type') == 'regular'), {})
    standings = {str(team['id']): team for team in stage.get('regular', [])}
    scorebase_records = scorebase_venue_records('KHL')
    korean_names = json.loads((ROOT / 'dist/team-ko.json').read_text())
    scorebase_aliases = {'Avtomobilist': '아프토모빌리스트 예카테린부르크',
                         'Dragons': '상하이 드래곤스', 'Lada': '라다 톨리야티',
                         'Metallurg Mg': '메탈루르크 마그니토고르스크'}
    results_by_team = {}
    for row in history:
        game = row.get('event', row)
        score = re.fullmatch(r'(\d+)\s*:\s*(\d+)', str(game.get('score', '')))
        if game.get('type_id') not in (18, 24) or not score:
            continue
        home_score, away_score = map(int, score.groups())
        for side, own, other in (('home', home_score, away_score), ('away', away_score, home_score)):
            team_id = str(game.get('team_a' if side == 'home' else 'team_b', {}).get('id', ''))
            if team_id and own != other:
                results_by_team.setdefault(team_id, []).append((game['start_at'], 'W' if own > other else 'L'))
    for results in results_by_team.values():
        results.sort(reverse=True)
    for row in history:
        game = row.get('event', row)
        if game.get('type_id') not in (18, 24):
            continue
        teams = [game.get('team_a', {}), game.get('team_b', {})]
        missing = [team for team in teams if str(team.get('id')) in upcoming_teams - recent_starters.keys()]
        if not missing:
            continue
        try:
            detail = fetch_json('https://khl.api.webcaster.pro/api/khl_mobile/event_v2.json?' + urlencode({'id': game['id'], 'locale': 'en'}))
        except OSError:
            continue
        detail = detail.get('event', detail)
        for side, team in (('home', detail.get('team_a', {})), ('away', detail.get('team_b', {}))):
            team_id = str(team.get('id', ''))
            if team_id not in upcoming_teams or team_id in recent_starters:
                continue
            players = team.get('start_fives') or team.get('starting_five') or []
            if isinstance(players, dict): players = players.get('players', players.get('items', []))
            lineup = [{'name': p.get('name') or p.get('player_name'), 'position': p.get('position', ''), 'flag': ''} for p in players if isinstance(p, dict) and (p.get('name') or p.get('player_name'))]
            if len(lineup) >= 6:
                recent_starters[team_id] = lineup[:6]
    for team_id in upcoming_teams - recent_starters.keys():
        try:
            team = fetch_json('https://khl.api.webcaster.pro/api/khl_mobile/team_v2.json?' + urlencode({'id': team_id, 'locale': 'en'})).get('team', {})
            players = team.get('players', [])
            def rank(player): return int(player.get('g') or 0) + int(player.get('a') or 0)
            goalie = sorted((p for p in players if p.get('role_key') == 'goaltender'), key=rank, reverse=True)[:1]
            defense = sorted((p for p in players if p.get('role_key') == 'defensemen'), key=rank, reverse=True)[:2]
            forwards = sorted((p for p in players if p.get('role_key') == 'forward'), key=rank, reverse=True)[:3]
            lineup = goalie + defense + forwards
            if len(lineup) == 6:
                recent_starters[team_id] = [{'name': p.get('name', ''), 'position': p.get('role_key', ''), 'flag': ''} for p in lineup]
        except Exception:
            continue
    for game in upcoming:
        home, away = game.get('team_a', {}), game.get('team_b', {})
        names = {'home': home.get('name', ''), 'away': away.get('name', '')}
        if not names['home'] or not names['away']:
            continue
        kickoff = datetime.fromtimestamp(game['start_at'] / 1000, timezone.utc).isoformat().replace('+00:00', 'Z')
        logos = {'home': home.get('image', ''), 'away': away.get('image', '')}
        competitors = [
            {'homeAway': 'home', 'team': {'id': str(home['id']), 'displayName': names['home'], 'shortDisplayName': names['home'], 'abbreviation': str(home['id']), 'logo': logos['home']}},
            {'homeAway': 'away', 'team': {'id': str(away['id']), 'displayName': names['away'], 'shortDisplayName': names['away'], 'abbreviation': str(away['id']), 'logo': logos['away']}}
        ]
        lineups = {'home': recent_starters.get(str(home['id']), []), 'away': recent_starters.get(str(away['id']), [])}
        recent_form = {side: [result for _, result in results_by_team.get(str(team['id']), [])[:5]] for side, team in (('home', home), ('away', away))}
        records = {}
        for side, team in (('home', home), ('away', away)):
            standing = standings.get(str(team['id']))
            if standing:
                wins = sum(int(standing.get(key) or 0) for key in ('w', 'otw', 'sow'))
                losses = sum(int(standing.get(key) or 0) for key in ('l', 'otl', 'sol'))
                records[side] = {'record': f'{wins}-{losses}'}
            source = scorebase_records.get(scorebase_aliases.get(names[side], korean_names.get(names[side], '')))
            if source and (side not in records or records[side]['record'] == source['record']):
                records[side] = {'record': source['record'], 'sideRecord': source[side]}
        prediction = {'league': 'khl', 'kickoff': kickoff, 'names': names, 'teams': {'home': str(home['id']), 'away': str(away['id'])}, 'logos': logos,
            'lineups': lineups, 'injuries': {}, 'recentForm': recent_form, 'records': records, 'statuses': {'home': 'predicted', 'away': 'predicted'},
            'note': 'KHL 직전 선발 또는 팀 등록 선수 기록 기준 예상', 'source': 'https://khl.api.webcaster.pro'}
        events.append({'event': {'id': str(game['id']), 'date': kickoff, 'competitions': [{'competitors': competitors}]}, 'prediction': prediction, 'confirmed': False})
    return events


def cpbl_kickoff(game):
    value = game.get('PreExeDate')
    if not value or not re.search(r'T\d{2}:\d{2}', value):
        raise ValueError('CPBL scheduled timestamp is missing')
    local = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if local.tzinfo is None:
        local = local.replace(tzinfo=ZoneInfo('Asia/Taipei'))
    return local.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def announced_pitchers(row, fields, source):
    result = {}
    for side, field in fields.items():
        name = row.get(field)
        if isinstance(name, str) and name.strip() and name.strip() not in ('未定', '未公布', '-', '待定'):
            result[side] = {'name': name.strip(), 'status': 'probable', 'source': source}
    return result


def npb_members(raw, side):
    if isinstance(raw, list):
        return [row for row in raw if str(row.get('hv')) == ('1' if side == 'home' else '2')]
    if isinstance(raw, dict):
        rows = raw.get(side, raw.get('Home' if side == 'home' else 'Visitor', []))
        return rows.get('players', rows.get('members', [])) if isinstance(rows, dict) else rows
    return []


def npb_pitchers(raw, overview, game_id, day):
    result = {}
    rows = overview if isinstance(overview, list) else [overview]
    for row in rows:
        if str(row.get('gameId')) == str(game_id) and str(row.get('gameDate')) == day.strftime('%Y%m%d'):
            result.update(announced_pitchers(row, {'home': 'homePrePitcherName', 'away': 'visitorPrePitcherName'},
                f'https://spaia.jp/baseball/npb/api/game_over_view?gameId={game_id}'))
    for side, key in (('home', 'home'), ('away', 'visitor')):
        # startPosition=11 identifies bench pitchers; never reuse yesterday's pitcher.
        starter = next((row for row in npb_members(raw, key) if str(row.get('startPosition')) == '1'), None)
        if starter and starter.get('playerName'):
            result[side] = {'name': starter['playerName'], 'status': 'confirmed',
                'source': f'https://spaia.jp/baseball/npb/api/starting_members_for_flash?gameId={game_id}'}
    return result


def yahoo_npb_pitchers(page, game_id, day):
    # Use the explicit home/away team IDs, not the order of player links.
    if f'/npb/game/{game_id}/top' not in page or f'{day.year}年{day.month}月{day.day}日' not in page:
        return {}
    team_ids = dict(re.findall(r'bb-gameCard__readMoreItem--(home|away)"[^>]*>\s*<a href="/npb/teams/(\d+)/schedule', page))
    section = re.search(r'id="strt_pit"(.*?)(?=<div class="bb-splits bb-splits--stretch")', page, re.S)
    if not section:
        return {}
    names = dict(re.findall(r'bb-splitsHead--npbTeam(\d+)".*?class="bb-splitsPitcherStarting".*?<a href="/npb/player/\d+/top">([^<]+)</a>', section.group(1), re.S))
    return {side: {'name': html.unescape(names[team_id]).strip(), 'status': 'probable',
                   'source': f'https://baseball.yahoo.co.jp/npb/game/{game_id}/top'}
            for side, team_id in team_ids.items() if team_id in names}


def reviewed_pitcher_fallback(event_id, kickoff, names, pitchers):
    path = ROOT / 'scripts' / 'starting-pitcher-review.json'
    reviews = json.loads(path.read_text()) if path.exists() else []
    for row in reviews:
        if row['eventId'] == str(event_id) and row['kickoff'] == kickoff and row['teams'] == names:
            for side, name in row['pitchers'].items():
                pitchers.setdefault(side, {'name': name, 'status': 'probable', 'source': row['source']})
    return pitchers


def scrape_cpbl():
    """Use CPBL public schedule and game detail API for five-day starter projections."""
    today = datetime.now(ZoneInfo('Asia/Seoul')).date()
    events = []
    recent_batters = {}
    announced_games = []
    try:
        official = post_json('https://www.cpbl.com.tw/home/getdetaillist', {}, 'https://www.cpbl.com.tw/')
        announced_games = json.loads(official.get('GameDetailJson') or '[]')
    except Exception as error:
        print('CPBL announced pitcher feed unavailable:', error)
    def hitters(team):
        return [{'name': row.get('HitterName', ''), 'position': row.get('PositionName', ''), 'flag': ''}
                for row in team.get('Hitters', []) if row.get('HitterName') and row.get('Lineup')]
    for lookback in range(1, 8):
        day = today.fromordinal(today.toordinal() - lookback)
        try:
            games = fetch_json(f'https://stats.cpbl.com.tw/api/proxy/v1/games/schedule/{day.isoformat()}').get('Data', {}).get('Games', [])
            for game in games:
                game_id = game.get('GameId') or game.get('Id')
                if not game_id: continue
                data = fetch_json(f'https://stats.cpbl.com.tw/api/proxy/v1/games/{game_id}').get('Data', {}).get('Game', {})
                for side in ('Home', 'Visiting'):
                    team = data.get(side, {})
                    team_name = (team.get('Team') or {}).get('Name', '')
                    lineup = hitters(team)
                    if team_name and len(lineup) >= 9 and team_name not in recent_batters:
                        recent_batters[team_name] = lineup[:9]
        except Exception:
            continue
    for offset in range(WINDOW_DAYS):
        day = today.fromordinal(today.toordinal() + offset)
        games = fetch_json(f'https://stats.cpbl.com.tw/api/proxy/v1/games/schedule/{day.isoformat()}')
        rows = games.get('Data', {}).get('Games', [])
        for game in rows:
            game_id = game.get('GameId') or game.get('Id')
            if not game_id or game.get('GameStatus') in ('POSTPONED', 'CANCELLED', 'CANCELED'):
                continue
            try:
                kickoff = cpbl_kickoff(game)
            except (ValueError, TypeError):
                continue
            if datetime.fromisoformat(kickoff.replace('Z', '+00:00')).astimezone(ZoneInfo('Asia/Taipei')).date() != day:
                continue
            if any(x['event']['id'] == str(game_id) for x in events):
                continue
            detail = fetch_json(f'https://stats.cpbl.com.tw/api/proxy/v1/games/{game_id}')
            data = detail.get('Data', {}).get('Game', {})
            # The detail carries postponements sooner than the schedule list.
            if data.get('PreExeDate'):
                kickoff = cpbl_kickoff(data)
                if datetime.fromisoformat(kickoff.replace('Z', '+00:00')).astimezone(ZoneInfo('Asia/Taipei')).date() != day:
                    continue
            visiting, home = data.get('Visiting', {}), data.get('Home', {})
            away_players, home_players = hitters(visiting), hitters(home)
            home_team = home.get('Team') or {}
            away_team = visiting.get('Team') or {}
            names = {'home': home_team.get('Name', game.get('HomeTeamName', '')), 'away': away_team.get('Name', game.get('VisitingTeamName', ''))}
            if not names['home'] or not names['away']:
                continue
            if len(home_players) < 9: home_players = recent_batters.get(names['home'], home_players)
            if len(away_players) < 9: away_players = recent_batters.get(names['away'], away_players)
            competitors = [{'homeAway': side, 'team': {'id': names[side], 'displayName': names[side], 'shortDisplayName': names[side], 'abbreviation': names[side], 'logo': logos[side]}} for side in ('home', 'away')]
            confirmed = len(hitters(home)) >= 9 and len(hitters(visiting)) >= 9
            pitchers = {}
            for row in announced_games:
                if str(row.get('Year')) + '-' + str(row.get('KindCode')) + '-' + str(row.get('GameSno')) == str(game_id):
                    pitchers.update(announced_pitchers(row, {'home': 'HomeFirstMover', 'away': 'VisitingFirstMover'}, 'https://www.cpbl.com.tw/'))
            reviewed_pitcher_fallback(game_id, kickoff, names, pitchers)
            prediction = {'league': 'cpbl', 'kickoff': kickoff, 'names': names, 'teams': names,
                'lineups': {'home': home_players, 'away': away_players}, 'startingPitchers': pitchers, 'injuries': {},
                'statuses': {'home': 'confirmed' if confirmed else 'predicted', 'away': 'confirmed' if confirmed else 'predicted'},
                'note': 'CPBL 공식 선발 타순' if confirmed else 'CPBL 직전 경기 타순 기준 예상', 'source': 'https://stats.cpbl.com.tw'}
            events.append({'event': {'id': str(game_id), 'date': kickoff, 'competitions': [{'competitors': competitors}]}, 'prediction': prediction, 'confirmed': confirmed})
    return events


def npb_kickoff(game, day):
    """SPAIA startTime is local HHmm, not a UTC timestamp or midnight placeholder."""
    value = str(game.get('startTime') or '').strip()
    match = re.fullmatch(r'(\d{1,2}):?(\d{2})', value)
    if not match:
        raise ValueError('NPB start time is not published')
    hour, minute = map(int, match.groups())
    if not 1 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError('Invalid NPB start time')
    local = datetime.combine(day, datetime.min.time(), ZoneInfo('Asia/Tokyo')).replace(hour=hour, minute=minute)
    return local.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def scrape_npb():
    """Use SPAIA published lineups, then carry forward each team's latest batting order."""
    today = datetime.now(ZoneInfo('Asia/Tokyo')).date()
    events = []
    recent_rosters = {}
    team_aliases = {}
    competition_stages = {}
    def team_names(game):
        names = []
        for prefix, legacy, alternate in (('home', 'Home', 'home'), ('visitor', 'Visitor', 'away')):
            name = game.get(prefix + 'TeamName') or game.get(legacy + 'TeamName') or game.get(alternate)
            aliases = [game.get(prefix + 'TeamNameI'), game.get(prefix + 'TeamNameS')]
            if name:
                for alias in aliases:
                    if alias: team_aliases[alias] = name
            else:
                name = next((team_aliases[x] for x in aliases if x in team_aliases), None)
            names.append(name)
        if all(names) and game.get('gameTypeName'):
            competition_stages[tuple(sorted(names))] = game['gameTypeName']
        return names
    def players(sides, side):
        values = npb_members(sides, side)
        if isinstance(sides, list):
            values = sorted((row for row in values if str(row.get('startBatNo', '')).isdigit() and 1 <= int(row['startBatNo']) <= 9), key=lambda row: int(row['startBatNo']))
        return [{'name': row.get('name') or row.get('playerName') or row.get('PlayerName', ''), 'position': row.get('startPosition', row.get('position', '')), 'flag': ''}
                for row in values if isinstance(row, dict) and (row.get('name') or row.get('playerName') or row.get('PlayerName'))]
    for lookback in range(1, 8):
        day = today.fromordinal(today.toordinal() - lookback)
        try:
            raw = fetch_json(f'https://spaia.jp/baseball/npb/api/games_info_by_date?gameDate={day:%Y%m%d}')
            past_games = raw if isinstance(raw, list) else raw.get('data', raw.get('games', []))
            for game in past_games:
                game_id = game.get('gameId') or game.get('GameID') or game.get('id')
                home, away = team_names(game)
                if not game_id or not home or not away: continue
                sides = fetch_json(f'https://spaia.jp/baseball/npb/api/starting_members_for_flash?gameId={game_id}')
                for name, side in ((home, 'home'), (away, 'visitor')):
                    lineup = players(sides, side)
                    if len(lineup) >= 9 and name not in recent_rosters: recent_rosters[name] = lineup[:9]
        except Exception:
            continue
    for offset in range(WINDOW_DAYS):
        day = today.fromordinal(today.toordinal() + offset)
        raw = fetch_json(f'https://spaia.jp/baseball/npb/api/games_info_by_date?gameDate={day:%Y%m%d}')
        games = raw if isinstance(raw, list) else raw.get('data', raw.get('games', []))
        for game in games:
            game_id = game.get('gameId') or game.get('GameID') or game.get('id')
            home, away = team_names(game)
            if not game_id or not home or not away:
                continue
            lineup = fetch_json(f'https://spaia.jp/baseball/npb/api/starting_members_for_flash?gameId={game_id}')
            sides = lineup
            try:
                overview = fetch_json(f'https://spaia.jp/baseball/npb/api/game_over_view?gameId={game_id}')
            except Exception as error:
                print(f'NPB {game_id} announced pitchers unavailable:', error)
                overview = []
            pitchers = npb_pitchers(sides, overview, game_id, day)
            if len(pitchers) < 2:
                try:
                    backup = yahoo_npb_pitchers(fetch_text(f'https://baseball.yahoo.co.jp/npb/game/{game_id}/top'), game_id, day)
                    for side, pitcher in backup.items(): pitchers.setdefault(side, pitcher)
                except Exception as error:
                    print(f'NPB {game_id} backup pitchers unavailable:', error)
            rosters = {'home': players(sides, 'home'), 'away': players(sides, 'visitor')}
            names = {'home': home, 'away': away}
            confirmed = len(rosters['home']) >= 9 and len(rosters['away']) >= 9
            if len(rosters['home']) < 9: rosters['home'] = recent_rosters.get(home, rosters['home'])
            if len(rosters['away']) < 9: rosters['away'] = recent_rosters.get(away, rosters['away'])
            try:
                kickoff = npb_kickoff(game, day)
            except ValueError as error:
                print(f'NPB {game_id}: {error}; not publishing an invented time')
                continue
            competitors = [{'homeAway': side, 'team': {'id': names[side], 'displayName': names[side], 'shortDisplayName': names[side], 'abbreviation': names[side]}} for side in ('home', 'away')]
            prediction = {'league': 'npb', 'competitionStage': competition_stages.get(tuple(sorted(names.values())), ''), 'kickoff': kickoff, 'names': names, 'teams': names, 'lineups': rosters, 'startingPitchers': pitchers, 'injuries': {},
                'statuses': {'home': 'confirmed' if confirmed else 'predicted', 'away': 'confirmed' if confirmed else 'predicted'},
                'note': 'NPB 선발 타순' if confirmed else 'NPB 직전 경기 타순 기준 예상', 'source': 'https://spaia.jp'}
            events.append({'event': {'id': str(game_id), 'date': kickoff, 'status': {'type': {'completed': game.get('gameStateName') == '試合終了'}}, 'competitions': [{'timeValid': True, 'competitors': competitors}]}, 'prediction': prediction, 'confirmed': confirmed})
    return events


def post_json(url, values, referer):
    import urllib.parse
    import urllib.request
    data = urllib.parse.urlencode(values).encode()
    request = urllib.request.Request(url, data=data, headers={
        'User-Agent': 'Mozilla/5.0', 'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'Referer': referer
    })
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode('utf-8', errors='replace'))


def scrape_kbo_official():
    logo_codes = {'LG', 'HH', 'SK', 'SS', 'NC', 'KT', 'LT', 'HT', 'OB', 'WO'}
    def logo(code):
        return f'https://6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/emblem/regular/fixed/emblem_{code}.png' if code in logo_codes else ''
    today = datetime.now(ZoneInfo('Asia/Seoul')).date()
    events = []
    for offset in range(WINDOW_DAYS):
        day = today.fromordinal(today.toordinal() + offset).strftime('%Y%m%d')
        referer = f'https://www.koreabaseball.com/Schedule/GameCenter/Main.aspx?gameDate={day}'
        games = post_json('https://www.koreabaseball.com/ws/Main.asmx/GetKboGameList', {
            'leId': 1, 'srId': '0,1,3,4,5,6,7,8,9', 'date': day
        }, referer).get('game', [])
        for game in games:
            if game.get('GAME_STATE_SC') in ('3', '4') or game.get('CANCEL_SC_ID') not in ('0', 0, None):
                continue
            try:
                rows = post_json('https://www.koreabaseball.com/ws/Schedule.asmx/GetLineUpAnalysis', {
                    'leId': game['LE_ID'], 'srId': game['SR_ID'], 'seasonId': game['SEASON_ID'], 'gameId': game['G_ID']
                }, referer)
            except Exception as error:
                print(f"KBO {game['G_ID']} batting order unavailable; retaining announced pitchers:", error)
                rows = []
            if not isinstance(rows, list) or len(rows) < 5:
                rows = [[], [], [], ['{"rows":[]}'], ['{"rows":[]}']]
            def lineup(table):
                result = []
                for row in table.get('rows', []):
                    cells = row.get('row', [])
                    if len(cells) >= 3 and cells[2].get('Text'):
                        result.append({'name': cells[2]['Text'], 'position': cells[1].get('Text', ''), 'flag': ''})
                return result
            home, away = lineup(json.loads(rows[3][0])), lineup(json.loads(rows[4][0]))
            confirmed = bool(rows[0] and rows[0][0].get('LINEUP_CK'))
            kickoff = datetime.strptime(day + game['G_TM'], '%Y%m%d%H:%M').replace(tzinfo=ZoneInfo('Asia/Seoul'))
            names = {'home': game['HOME_NM'], 'away': game['AWAY_NM']}
            competitors = [
                {'homeAway': 'home', 'team': {'id': game['HOME_ID'], 'displayName': names['home'], 'shortDisplayName': names['home'], 'abbreviation': game['HOME_ID'], 'logo': logo(game['HOME_ID'])}},
                {'homeAway': 'away', 'team': {'id': game['AWAY_ID'], 'displayName': names['away'], 'shortDisplayName': names['away'], 'abbreviation': game['AWAY_ID'], 'logo': logo(game['AWAY_ID'])}}
            ]
            prediction = {'league': 'kbo', 'kickoff': kickoff.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'), 'names': names,
                'teams': {'home': game['HOME_ID'], 'away': game['AWAY_ID']}, 'logos': {'home': logo(game['HOME_ID']), 'away': logo(game['AWAY_ID'])}, 'lineups': {'home': home, 'away': away},
                'startingPitchers': announced_pitchers(game, {'home': 'B_PIT_P_NM', 'away': 'T_PIT_P_NM'}, referer), 'injuries': {},
                'statuses': {'home': 'confirmed' if confirmed else 'predicted', 'away': 'confirmed' if confirmed else 'predicted'},
                'note': 'KBO 공식 당일 타순' if confirmed else 'KBO 공식 최근 선발 타순 기준 예상',
                'source': f"https://www.koreabaseball.com/Schedule/GameCenter/Main.aspx?gameDate={day}&gameId={game['G_ID']}&section=START_PIT"}
            events.append({'event': {'id': game['G_ID'], 'date': prediction['kickoff'], 'competitions': [{'competitors': competitors}]},
                'prediction': prediction, 'confirmed': confirmed})
    return events


def kbl_projected_lineups(detail, names):
    tables = re.findall(r'<h3[^>]*class="font-semibold"[^>]*>([^<]+)</h3>.*?<table[^>]*>(.*?)</table>', detail, re.S)
    lineups = {}
    for team_name, table in tables[:2]:
        if team_name.strip() not in names:
            continue
        header = re.search(r'<thead[^>]*>(.*?)</thead>', table, re.S)
        columns = [re.sub(r'<[^>]+>', '', cell).strip() for cell in re.findall(r'<th\b[^>]*>(.*?)</th>', header.group(1), re.S)] if header else []
        minute_column = columns.index('출장') if '출장' in columns else -1
        body = re.search(r'<tbody[^>]*>(.*?)</tbody>', table, re.S)
        if not body:
            continue
        players = []
        for row in re.findall(r'<tr[^>]*>(.*?)</tr>', body.group(1), re.S):
            name_match = re.search(r'<span class="flex items-center gap-1\.5 whitespace-nowrap font-medium">([^<]+)</span>', row)
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)
            if not name_match or len(cells) < 2 or minute_column >= len(cells):
                continue
            minute_text = re.sub(r'<[^>]+>', '', cells[minute_column]).strip()
            try:
                minutes = float(minute_text)
            except ValueError:
                continue
            if minutes > 0:
                players.append((minutes, html.unescape(name_match.group(1).strip())))
        projected = sorted(players, reverse=True)[:5]
        if projected:
            side = 'home' if team_name.strip() == names[0].strip() else 'away'
            lineups[side] = [{'name': player, 'position': '', 'flag': ''} for _, player in projected]
    return lineups


def kbl_recent_and_records(detail):
    """Read the home-left, away-right team comparison without inventing missing games."""
    result = {'recentForm': {}, 'records': {}}
    for key in ('recent', 'record'):
        match = re.search(r'<div data-compare-row="' + key + r'".*?(?=<div data-compare-row=|</section>|$)', detail, re.S)
        if not match:
            continue
        row = match.group(0)
        for side, column in (('home', '1'), ('away', '3')):
            cell = re.search(r'<div class="[^"]*col-start-' + column + r' row-start-1[^"]*">(.*?)(?=<div class="[^"]*col-start-[13] row-start-1|$)', row, re.S)
            if not cell:
                continue
            if key == 'recent':
                results = re.findall(r'<span aria-hidden="true">([WLD])</span>', cell.group(1))
                if results:
                    result['recentForm'][side] = results[:5]
            else:
                value = re.search(r'\b(\d+\s*[-–]\s*\d+)\b', re.sub(r'<[^>]+>', ' ', cell.group(1)))
                if value:
                    result['records'][side] = [{'name': 'overall', 'summary': value.group(1)}]
    return result


def scrape_kbl_statgg():
    """Use KBL schedule and season player minutes as a transparent starter projection."""
    today = datetime.now(ZoneInfo('Asia/Seoul')).date()
    end = today.fromordinal(today.toordinal() + WINDOW_DAYS)
    schedule = fetch_text(f'https://statgg.com/ko/kbl/schedule?date={today.isoformat()}')
    links = re.findall(r'<a[^>]+href="(/ko/kbl/matches/[^\"]+)"[^>]*>(.*?)</a>', schedule, re.S)
    events = []
    seen = set()
    for path, card in links:
        if path in seen:
            continue
        seen.add(path)
        names = re.findall(r'<span class="break-keep[^\"]*">([^<]+)</span>', card)
        time_match = re.search(r'<span class="stat-num text-fg-muted">(\d{1,2}:\d{2})</span>', card)
        if len(names) != 2 or not time_match or '예정' not in card:
            continue
        # StatGG's KBL route also lists EASL fixtures involving KBL clubs.
        if any(name not in KBL_LOGO_CODES for name in names):
            continue
        card_index = schedule.find(f'href="{path}"')
        day_match = list(re.finditer(r'<span class="stat-num tabular-nums">(\d{4}\.\d{2}\.\d{2})', schedule[:card_index]))
        if not day_match:
            continue
        kickoff_local = datetime.strptime(day_match[-1].group(1) + ' ' + time_match.group(1), '%Y.%m.%d %H:%M').replace(tzinfo=ZoneInfo('Asia/Seoul'))
        if not today <= kickoff_local.date() < end:
            continue
        detail = fetch_text('https://statgg.com' + path)
        lineups = kbl_projected_lineups(detail, names)
        comparison = kbl_recent_and_records(detail)
        event_id = path.rsplit('/', 1)[-1]
        logos = {'home': basketball_logo('kbl', names[0]), 'away': basketball_logo('kbl', names[1])}
        competitors = [
            {'homeAway': 'home', 'team': {'id': names[0], 'displayName': names[0], 'shortDisplayName': names[0], 'abbreviation': names[0], 'logo': logos['home']}, 'records': comparison['records'].get('home', [])},
            {'homeAway': 'away', 'team': {'id': names[1], 'displayName': names[1], 'shortDisplayName': names[1], 'abbreviation': names[1], 'logo': logos['away']}, 'records': comparison['records'].get('away', [])}
        ]
        records = {side: {'record': rows[0]['summary']} for side, rows in comparison['records'].items() if rows}
        events.append({'event': {'id': event_id, 'date': kickoff_local.astimezone(timezone.utc).isoformat().replace('+00:00','Z'), 'competitions': [{'competitors': competitors}], 'recentForm': comparison['recentForm']}, 'prediction': {'league': 'kbl', 'kickoff': kickoff_local.astimezone(timezone.utc).isoformat().replace('+00:00','Z'), 'names': {'home': names[0], 'away': names[1]}, 'teams': {'home': names[0], 'away': names[1]}, 'logos': logos, 'lineups': lineups, 'recentForm': comparison['recentForm'], 'records': records, 'injuries': {}, 'statuses': {'home': 'predicted', 'away': 'predicted'}, 'note': 'StatGG 시즌 경기당 출장시간 상위 5명 기준 예상 선발', 'source': 'https://statgg.com' + path}})
    scorebase_records = scorebase_venue_records('KBL')
    for event in events:
        prediction = event['prediction']
        for side, name in prediction['names'].items():
            source = scorebase_records.get(name)
            record = prediction['records'].get(side)
            if source and (not record or record['record'] == source['record']):
                prediction['records'][side] = {'record': source['record'], 'sideRecord': source[side]}
    return events


def scrape_kovo_bkvolley():
    """Build six-player KOVO estimates from the match-linked registered roster."""
    from html.parser import HTMLParser
    logo_ids = {'SOOP': 'soopers', 'IBK기업은행': 'altos', '정관장': 'redsparks',
                '흥국생명': 'pinkspiders', 'GS칼텍스': 'kixx', '한국도로공사': 'hipass',
                '현대건설': 'hillstate', '대한항공': 'jumbos', '현대캐피탈': 'skywalkers',
                '우리카드': 'wooriwon', 'KB손해보험': 'stars', '한국전력': 'vixtorm',
                'OK저축은행': 'okman', '삼성화재': 'bluefangs'}
    def logo(team_name):
        code = next((value for name, value in logo_ids.items() if name in team_name), '')
        return f'https://cdn.kovo.co.kr/emblems/{code}.svg' if code else ''
    class Text(HTMLParser):
        def __init__(self):
            super().__init__(); self.value = []
        def handle_data(self, data):
            self.value.append(data)
    today = datetime.now(ZoneInfo('Asia/Seoul')).date()
    page = fetch_text('https://bkvolley.kr/matches')
    public_match = re.search(r'<script id="volley-public-data" type="application/json">(.*?)</script>', page, re.S)
    public_data = json.loads(public_match.group(1)).get('data', {}) if public_match else {}
    completed = public_data.get('recentMatches', [])
    events, seen = [], set()
    for match in re.finditer(r'<a\b[^>]*href=["\'](/matches/\d+)["\'][^>]*>(.*?)</a>', page, re.S | re.I):
        path, anchor = match.groups()
        if path in seen:
            continue
        seen.add(path)
        parser = Text(); parser.feed(anchor)
        title = ' '.join(' '.join(parser.value).split())
        pair = re.search(r'(.+?)\s+vs\s+(.+)', title, re.I)
        if not pair:
            continue
        context_start = max(0, match.start()-500)
        context = page[context_start:match.end()+500]
        text_parser = Text(); text_parser.feed(context)
        context_text = ' '.join(' '.join(text_parser.value).split())
        date_pattern = r'(20\d{2})년\s*(\d{1,2})월\s*(\d{1,2})일\s*(\d{1,2}):(\d{2})'
        date_candidates = list(re.finditer(date_pattern, context_text))
        date_match = min(date_candidates, key=lambda item: abs(item.start()-len(context_text)//2)) if date_candidates else None
        if date_match:
            year, month, day, hour, minute = map(int, date_match.groups())
        else:
            short_candidates = list(re.finditer(r'(?<!\d)(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{1,2}):(\d{2})', context_text))
            short_date = min(short_candidates, key=lambda item: abs(item.start()-len(context_text)//2)) if short_candidates else None
            if not short_date:
                continue
            month, day, hour, minute = map(int, short_date.groups())
            year = today.year
        try:
            kickoff_local = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo('Asia/Seoul'))
        except ValueError:
            continue
        if not today <= kickoff_local.date() < today.fromordinal(today.toordinal()+WINDOW_DAYS):
            continue
        home, away = [name.strip() for name in pair.groups()]
        kickoff = kickoff_local.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
        fixture = next((item for item in public_data.get('upcomingMatches', []) if str(item.get('id')) == path.rsplit('/', 1)[-1]), {})
        division = {'KOVO 남자부': 'men', 'KOVO 여자부': 'women'}.get(fixture.get('league'), '')
        recent_form, records = {}, {}
        for side in ('home', 'away'):
            team_id = fixture.get(side + 'TeamId')
            history = []
            for result in completed:
                if result.get('status') != 'finished' or not result.get('matchDate') or datetime.fromisoformat(result['matchDate'].replace('Z', '+00:00')) >= kickoff_local.astimezone(timezone.utc):
                    continue
                venue = next((position for position in ('home', 'away') if result.get(position + 'TeamId') == team_id), None)
                if venue and isinstance(result.get('homeSets'), int) and isinstance(result.get('awaySets'), int):
                    won = result['homeSets'] > result['awaySets'] if venue == 'home' else result['awaySets'] > result['homeSets']
                    history.append((result['matchDate'], venue, 'W' if won else 'L', result.get('season')))
            history.sort(reverse=True)
            if history:
                recent_form[side] = [result for _, _, result, _ in history[:5]]
                season_history = [(venue, result) for _, venue, result, season in history if season == fixture.get('season')]
                wins = sum(result == 'W' for _, result in season_history)
                at_venue = [result for venue, result in season_history if venue == side]
                records[side] = {'record': f'{wins}-{len(season_history)-wins}', 'sideRecord': f'{sum(result == "W" for result in at_venue)}-{sum(result == "L" for result in at_venue)}'}
        logos = {'home': logo(home), 'away': logo(away)}
        competitors = [
            {'homeAway': 'home', 'team': {'id': home, 'displayName': home, 'shortDisplayName': home, 'abbreviation': home, 'logo': logos['home']}},
            {'homeAway': 'away', 'team': {'id': away, 'displayName': away, 'shortDisplayName': away, 'abbreviation': away, 'logo': logos['away']}}
        ]
        url = 'https://bkvolley.kr' + path
        try:
            roster_page = fetch_text(url + '?tab=players')
            roster_parser = Text(); roster_parser.feed(roster_page)
            roster_text = ' '.join(' '.join(roster_parser.value).split())
            public_match = re.search(r'<script id="volley-public-data" type="application/json">(.*?)</script>', roster_page, re.S)
            public_data = json.loads(public_match.group(1)).get('data', {}) if public_match else {}
            match_id = int(path.rsplit('/', 1)[-1])
            fixture = next((item for item in public_data.get('upcomingMatches', []) if int(item.get('id', -1)) == match_id), {})
            team_ids = {'home': fixture.get('homeTeamId'), 'away': fixture.get('awayTeamId')}
            roster_start = roster_text.find('두 팀 등록 선수')
            def estimate(team_name, other_name):
                side = 'home' if team_name == home else 'away'
                team_id = team_ids.get(side)
                previous = []
                for record in public_data.get('setLineups', []):
                    if record.get('matchDate') and record['matchDate'] >= kickoff and team_id:
                        continue
                    team_record = next((entry for entry in record.get('teams', []) if entry.get('teamId') == team_id), None)
                    starters = [player for player in (team_record or {}).get('players', []) if player.get('role') == 'starter']
                    if len(starters) == 6 and (not previous or record.get('matchDate', '') > previous[0]):
                        previous = [record.get('matchDate', ''), [{'name': player['name'], 'position': player.get('position', ''), 'flag': ''} for player in starters]]
                if previous:
                    return previous[1]
                roster_players = [player for player in public_data.get('players', []) if player.get('teamId') == team_id and player.get('name')]
                selected = []
                for position, count in (('세터', 1), ('리베로', 1), ('미들블로커', 2), ('아웃사이드 히터', 1), ('아포짓', 1)):
                    matches = [player for player in roster_players if player.get('position') == position and player not in selected]
                    selected.extend(matches[:count])
                for player in roster_players:
                    if len(selected) >= 6: break
                    if player not in selected: selected.append(player)
                if len(selected) == 6:
                    return [{'name': player['name'], 'position': player.get('position', ''), 'flag': ''} for player in selected]
                start = roster_text.find(team_name, max(0, roster_start))
                end = roster_text.find(other_name, start + len(team_name)) if start >= 0 else -1
                segment = roster_text[start:end if end >= 0 else None] if start >= 0 else ''
                candidates = []
                pattern = r'NO\.?\s*\d+\s*([가-힣A-Za-z·\- ]+?)\s*(아웃사이드 히터|미들블로커|세터|리베로|아포짓)'
                for name, position in re.findall(pattern, segment):
                    name = name.strip()
                    if name and all(player['name'] != name for player in candidates):
                        candidates.append({'name': name, 'position': position, 'flag': ''})
                chosen = []
                for position, count in (('세터', 1), ('리베로', 1), ('미들블로커', 2), ('아웃사이드 히터', 1), ('아포짓', 1)):
                    matching = [player for player in candidates if player['position'] == position and player not in chosen]
                    chosen.extend(matching[:count])
                for player in candidates:
                    if len(chosen) >= 6: break
                    if player not in chosen: chosen.append(player)
                return chosen[:6]
            lineups = {'home': estimate(home, away), 'away': estimate(away, home)}
        except Exception:
            lineups = {'home': [], 'away': []}
        prediction = {'league': 'kovo', 'division': division, 'kickoff': kickoff, 'names': {'home': home, 'away': away}, 'teams': {'home': home, 'away': away}, 'logos': logos,
            'recentForm': recent_form, 'records': records,
            'lineups': lineups, 'injuries': {}, 'statuses': {'home': 'predicted', 'away': 'predicted'},
            'note': '등록 선수 명단과 포지션을 기준으로 구성한 6인 예상 라인업', 'source': url}
        events.append({'event': {'id': path.rsplit('/', 1)[-1], 'date': kickoff, 'competitions': [{'competitors': competitors}]}, 'prediction': prediction, 'confirmed': False})
    return events


def parse_wkbl_schedule(page, year, month):
    """Read official monthly WKBL dates; the first club is the home team."""
    schedule = re.search(r'<ul\s+class="list_schedule"[^>]*>(.*?)</ul>', page, re.S)
    if not schedule:
        raise ValueError('WKBL official schedule list is missing')
    games = []
    for block in re.findall(r'<li\b[^>]*>(.*?)</li>', schedule.group(1), re.S):
        date_match = re.search(r'class="date"[^>]*>\s*(\d{1,2})\.(\d{1,2})', block)
        teams = re.findall(r'class="team_name"[^>]*>\s*([^<]+)', block)
        place = re.search(r'class="place_block".*?(\d{1,2}:\d{2})\s*</span>', block, re.S)
        scores = [int(score) for score in re.findall(r'<em>\s*(\d+)\s*</em>', block)[:2]]
        completed = not place and len(scores) == 2 and 'game_type=01' in block
        if not date_match or len(teams) != 2 or (not place and not completed):
            continue
        found_month, day = map(int, date_match.groups())
        if found_month != month:
            continue
        try:
            start = datetime.strptime(f'{year}-{month:02}-{day:02} {place.group(1) if place else "00:00"}', '%Y-%m-%d %H:%M').replace(tzinfo=ZoneInfo('Asia/Seoul'))
        except ValueError:
            continue
        game = {'date': start.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'home': html.unescape(teams[0]).strip(), 'away': html.unescape(teams[1]).strip()}
        if len(scores) == 2:
            game['scores'] = scores
            game['completed'] = completed
        games.append(game)
    return games


def parse_wkbl_datalab_results(page, year):
    games = []
    for block in re.findall(r'<li class="game-item[^>]*data-id="([^"]+)"[^>]*>(.*?)</li>', page, re.S):
        game_id, card = block
        date = re.search(r'class="game-date">\s*(\d{2})\.(\d{2})', card)
        names = [html.unescape(re.sub(r'<[^>]+>', '', name)).strip() for name in
                 re.findall(r'<dt class="(?:home|away)-team-name">(.*?)</dt>', card, re.S)]
        scores = [re.search(r'<dd class="[^"]*team-score">\s*(\d+)\s*</dd>', side)
                  for side in re.findall(r'<dl class="(?:home|away)-team">(.*?)</dl>', card, re.S)]
        if not date or len(names) != 2 or len(scores) != 2 or not all(scores):
            continue
        month, day = map(int, date.groups())
        games.append({'id': game_id, 'date': f'{year}-{month:02}-{day:02}T00:00:00Z',
                      'home': names[0], 'away': names[1], 'scores': [int(score.group(1)) for score in scores]})
    return games


def wkbl_projected_lineups(detail, names):
    """Estimate starters from current-roster minutes, then prior head-to-head minutes."""
    title = re.search(r'<h1[^>]*>(.*?)</h1>', detail, re.S)
    if not title or not all(name in html.unescape(re.sub(r'<[^>]+>', ' ', title.group(1))) for name in names.values()):
        raise ValueError('WKBL match detail teams do not match the official schedule')
    lineups = {}
    for index, side in enumerate(('home', 'away')):
        current = re.search(r'<div role="tabpanel" id="wkbl-pregame-' + str(index) + r'-season-panel".*?</table>', detail, re.S)
        previous = re.search(r'<div role="tabpanel" id="wkbl-pregame-' + str(index) + r'-vs-panel".*?</table>', detail, re.S)
        if not current:
            raise ValueError('WKBL current roster table missing')
        def rows(table):
            if not table:
                return {}
            headings = [html.unescape(re.sub(r'<[^>]+>', '', cell)).strip() for cell in re.findall(r'<th\b[^>]*>(.*?)</th>', table.group(0), re.S)]
            minute_col = headings.index('출장') if '출장' in headings else -1
            result = {}
            for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', table.group(0), re.S):
                cells = re.findall(r'<td\b[^>]*>(.*?)</td>', row, re.S)
                name = re.search(r'<span[^>]*font-medium[^>]*>([^<]+)</span>', cells[0]) if cells else None
                position = re.search(r'text-3xs[^>]*>([GFC])</span>', cells[0]) if cells else None
                if not name:
                    continue
                try:
                    minutes = float(re.sub(r'<[^>]+>', '', cells[minute_col]).strip()) if 0 <= minute_col < len(cells) else 0
                except ValueError:
                    continue
                result[html.unescape(name.group(1)).strip()] = (minutes, position.group(1) if position else '')
            return result
        season, matchup = rows(current), rows(previous)
        if len(season) < 5:
            raise ValueError('WKBL current roster has fewer than five scored players')
        # A new season can have no games yet. Only names on the current roster qualify.
        scores = [(minutes if minutes > 0 else matchup.get(name, (0,))[0], name, position)
                  for name, (minutes, position) in season.items()]
        selected = sorted(scores, reverse=True)[:5]
        if selected[-1][0] <= 0:
            raise ValueError('WKBL minutes evidence is insufficient for five players')
        lineups[side] = [{'name': name, 'position': position, 'flag': ''} for _, name, position in selected]
    return lineups


def scrape_wkbl_official():
    today = datetime.now(ZoneInfo('Asia/Seoul')).date()
    target_days = {today.fromordinal(today.toordinal() + offset) for offset in range(WINDOW_DAYS)}
    last_day = max(target_days)
    season_year = today.year if today.month >= 10 else today.year - 1
    months = []
    year, month = season_year, 10
    while (year, month) <= (last_day.year, last_day.month):
        months.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    entries = []
    try:
        schedule = fetch_text(f'https://statgg.com/ko/wkbl/schedule?date={today.isoformat()}')
    except OSError as error:
        print('wkbl lineup schedule unavailable:', error)
        schedule = ''
    detail_paths = {}
    for path, card in re.findall(r'<a[^>]+href="(/ko/wkbl/matches/[^"]+)"[^>]*>(.*?)</a>', schedule, re.S):
        teams = re.findall(r'<span class="break-keep[^"]*">([^<]+)</span>', card)
        time = re.search(r'<span class="stat-num text-fg-muted">(\d{1,2}:\d{2})</span>', card)
        heading = list(re.finditer(r'<span class="stat-num tabular-nums">(\d{4}\.\d{2}\.\d{2})', schedule[:schedule.find(f'href="{path}"')]))
        if len(teams) == 2 and time and heading:
            day = heading[-1].group(1).replace('.', '-')
            detail_paths[(day, time.group(1), *map(html.unescape, teams))] = path
    all_games = []
    for year, month in months:
        page = fetch_text(f'https://www.wkbl.or.kr/m/game/schedule.asp?sch_ym={year}{month:02}')
        all_games.extend(parse_wkbl_schedule(page, year, month))
    target_teams = {name for game in all_games
                    if game['date'][:10] in {day.isoformat() for day in target_days}
                    for name in (game['home'], game['away'])}
    older_games = []
    if any(sum(len(game.get('scores', [])) == 2 and name in (game['home'], game['away'])
               for game in all_games) < 5 for name in target_teams):
        try:
            for month_day in ('0323', '0222', '0215'):
                url = f'https://datalab.wkbl.or.kr/game/list/month?firstGameDate={season_year}{month_day}&selectedId=&selectedGameDate='
                older_games.extend(parse_wkbl_datalab_results(fetch_text(url), season_year))
            older_games = list({game['id']: game for game in older_games}.values())
        except (OSError, ValueError) as error:
            print('wkbl previous season results unavailable:', error)
    season_games = {id(game) for game in all_games}
    seen_games = set()
    for game in all_games:
            kickoff = game['date']
            if game.get('completed'):
                continue
            if datetime.fromisoformat(kickoff.replace('Z', '+00:00')).astimezone(ZoneInfo('Asia/Seoul')).date() not in target_days:
                continue
            names = {'home': game['home'], 'away': game['away']}
            game_key = (kickoff, names['home'], names['away'])
            if game_key in seen_games:
                continue
            seen_games.add(game_key)
            local = datetime.fromisoformat(kickoff.replace('Z', '+00:00')).astimezone(ZoneInfo('Asia/Seoul'))
            path = detail_paths.get((local.date().isoformat(), local.strftime('%H:%M'), names['home'], names['away']))
            lineups = {'home': [], 'away': []}
            if path:
                try:
                    lineups = wkbl_projected_lineups(fetch_text('https://statgg.com' + path), names)
                except (OSError, ValueError) as error:
                    print('wkbl lineup unavailable:', error)
            logos = {side: basketball_logo('wkbl', name) for side, name in names.items()}
            recent_form, records = {}, {}
            for side in ('home', 'away'):
                team = names[side]
                history = []
                for prior in all_games + older_games:
                    if prior['date'] >= kickoff or len(prior.get('scores', [])) != 2 or team not in (prior['home'], prior['away']):
                        continue
                    venue = 'home' if prior['home'] == team else 'away'
                    own, other = prior['scores'] if venue == 'home' else prior['scores'][::-1]
                    history.append((prior['date'], venue, 'W' if own > other else 'L', id(prior) in season_games))
                history.sort(reverse=True)
                if history:
                    recent_form[side] = [result for _, _, result, _ in history[:5]]
                    current = [(venue, result) for _, venue, result, in_season in history if in_season]
                    wins = sum(result == 'W' for _, result in current)
                    at_venue = [result for venue, result in current if venue == side]
                    records[side] = {'record': f'{wins}-{len(current)-wins}', 'sideRecord': f'{sum(result == "W" for result in at_venue)}-{sum(result == "L" for result in at_venue)}'}
            competitors = [{'homeAway': side, 'team': {'id': names[side], 'displayName': names[side],
                            'shortDisplayName': names[side], 'abbreviation': names[side], 'logo': logos[side]}} for side in ('home', 'away')]
            prediction = {'league': 'wkbl', 'kickoff': kickoff, 'names': names, 'teams': names,
                          'logos': logos, 'lineups': lineups, 'injuries': {}, 'recentForm': recent_form, 'records': records,
                          'statuses': {'home': 'predicted', 'away': 'predicted'},
                          'note': '현재 등록 선수의 시즌 또는 최근 맞대결 출전시간 기준 예상 선발',
                          'source': 'https://www.wkbl.or.kr/m/game/schedule.asp'}
            entries.append({'event': {'id': f"wkbl-{kickoff[:10]}-{names['home']}-{names['away']}",
                                      'date': kickoff, 'competitions': [{'timeValid': True, 'competitors': competitors}]},
                            'prediction': prediction, 'confirmed': False})
    return entries


def restore_missing_lineups(entries, previous_entries):
    old_games = {entry.get('event', {}).get('id'): entry for entry in previous_entries}
    for entry in entries:
        old = old_games.get(entry.get('event', {}).get('id'))
        if not old or old.get('prediction', {}).get('names') != entry.get('prediction', {}).get('names'):
            continue
        current_lines = entry.get('prediction', {}).get('lineups', {})
        old_lines = old.get('prediction', {}).get('lineups', {})
        for side in ('home', 'away'):
            if not current_lines.get(side) and old_lines.get(side):
                current_lines[side] = old_lines[side]


def main():
    path = ROOT / 'dist' / 'projections.json'
    previous = json.loads(path.read_text()) if path.exists() else {}
    today = datetime.now(ZoneInfo('Asia/Seoul')).date()
    target_days = {today.fromordinal(today.toordinal() + offset) for offset in range(WINDOW_DAYS)}
    def within_window(entry, field):
        try:
            return datetime.fromisoformat(entry[field].replace('Z', '+00:00')).astimezone(ZoneInfo('Asia/Seoul')).date() in target_days
        except (KeyError, TypeError, ValueError):
            return False
    all_results = []
    source_status = {}
    for league, (code, kind) in SOURCES.items():
        try:
            found = scrape_page(league, code, kind)
            source_status[league] = {'fresh': True, 'checkedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}
        except Exception as error:
            print(league, 'source unavailable:', error)
            found = [item for item in previous.get('items', []) if item.get('league') == league and within_window(item, 'kickoff')]
            source_status[league] = {'fresh': False, 'checkedAt': previous.get('sourceStatus', {}).get(league, {}).get('checkedAt')}
        all_results.extend(found)
        print(league, len(found))
    try:
        europa = scrape_europa()
        source_status['uel'] = {'fresh': True, 'checkedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}
    except Exception as error:
        print('uel source unavailable:', error)
        europa = [item for item in previous.get('items', []) if item.get('league') == 'uel' and within_window(item, 'kickoff')]
        source_status['uel'] = {'fresh': False, 'checkedAt': previous.get('sourceStatus', {}).get('uel', {}).get('checkedAt')}
    all_results.extend(europa)
    print('uel', len(europa))
    for league, (espn_path, _) in ESPN_INTERNATIONAL.items():
        try:
            national = scrape_espn_international(league, espn_path, target_days)
            source_status[league] = {'fresh': True, 'checkedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}
        except Exception as error:
            print(league, 'source unavailable:', error)
            national = [item for item in previous.get('items', []) if item.get('league') == league and within_window(item, 'kickoff')]
            source_status[league] = {'fresh': False, 'checkedAt': previous.get('sourceStatus', {}).get(league, {}).get('checkedAt')}
        all_results.extend(national)
        print(league, len(national))
    try:
        nhl = scrape_nhl_dailyfaceoff()
        all_results.extend(nhl)
        source_status['nhl'] = {'fresh': True, 'checkedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}
        print('nhl-dailyfaceoff', len(nhl))
    except Exception as error:
        print('nhl Daily Faceoff unavailable:', error)
        all_results.extend(item for item in previous.get('items', []) if item.get('league') == 'nhl' and within_window(item, 'kickoff'))
        source_status['nhl'] = {'fresh': False, 'checkedAt': previous.get('sourceStatus', {}).get('nhl', {}).get('checkedAt')}
    payload = {'asOf': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), 'items': all_results, 'sourceStatus': source_status}
    payload['domestic'] = {}
    for key, scraper in (('kbo', scrape_kbo_official), ('kbl', scrape_kbl_statgg), ('wkbl', scrape_wkbl_official), ('kovo', scrape_kovo_bkvolley), ('npb', scrape_npb), ('cpbl', scrape_cpbl),
                         ('kleague1', lambda: scrape_fotmob_kleague(9080, 'kleague1')),
                         ('kleague2', lambda: scrape_fotmob_kleague(9116, 'kleague2')), ('khl', scrape_khl)):
        try:
            payload['domestic'][key] = scraper()
            source_status[key] = {'fresh': True, 'checkedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}
            print(key + ('-statgg' if key == 'kbl' else '-official'), len(payload['domestic'][key]))
        except Exception as error:
            print(key + ' source unavailable:', error)
            payload['domestic'][key] = [entry for entry in previous.get('domestic', {}).get(key, []) if within_window(entry.get('event', {}), 'date')]
            source_status[key] = {'fresh': False, 'checkedAt': previous.get('sourceStatus', {}).get(key, {}).get('checkedAt')}
        restore_missing_lineups(payload['domestic'][key], previous.get('domestic', {}).get(key, []))
    if not any(status['fresh'] for status in source_status.values()):
        raise SystemExit('No lineup sources refreshed; keeping the current snapshot')
    enrich_injury_details(payload)
    # Recent results + season/home-road record from ESPN for each match (scripts/recent_form.py).
    # A failure here never stops the lineup refresh — the items simply go out without those fields.
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location('recent_form', Path(__file__).with_name('recent_form.py'))
        recent_form = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recent_form)
        print('recent form', recent_form.enrich_recent_form(payload, previous, fetch_json))
        print('KBO recent form', recent_form.enrich_kbo_form(
            payload, previous,
            lambda day: post_json('https://www.koreabaseball.com/ws/Main.asmx/GetKboGameList',
                                  {'leId': 1, 'srId': '0,1,3,4,5,6,7,8,9', 'date': day},
                                  f'https://www.koreabaseball.com/Schedule/GameCenter/Main.aspx?gameDate={day}').get('game', []),
            fetch_text))
    except Exception as error:
        print('recent form unavailable:', error)
    if previous.get('items') == payload.get('items') and previous.get('domestic') == payload.get('domestic') and previous.get('sourceStatus') == payload.get('sourceStatus'):
        print('No lineup changes')
        return
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__':
    main()
