"""Resolve names from public search pages; never transliterate or bypass search challenges."""
import base64
from collections import Counter
import datetime as dt
import difflib
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
DOMAINS = ('namu.moe', 'transfermarkt.co.kr', 'flashscore.co.kr', 'sofascore.com', 'scorebase.kr', 'kleague.com',
           'premierleague.com', 'bundesliga.com', 'uefa.com', 'fifa.com', 'nba.com', 'mlb.com', 'nhl.com',
           'liverpoolfc.com', 'mancity.com', 'manutd.com', 'tottenhamhotspur.com', 'arsenal.com',
           'fcbayern.com', 'bvb.de', 'borussia.de', 'vfb.de', 'realmadrid.com', 'fcbarcelona.com',
           'yna.co.kr', 'yonhapnews.co.kr', 'newsis.com', 'news1.kr', 'sportsseoul.com',
           'sportschosun.com', 'sportalkorea.com', 'osen.co.kr', 'xportsnews.com', 'spotvnews.co.kr',
           'mk.co.kr', 'hankyung.com', 'chosun.com', 'donga.com', 'khan.co.kr', 'kbs.co.kr', 'sbs.co.kr')
SEARCH_HOSTS = ('www.google.com', 'www.bing.com', 'search.daum.net')
POLICY = 'precollect-names-v6'
NAMU_POLICY = 'namuwiki-team-roster-v2'
SCOREBASE_LEAGUES = ('nhl', 'nba', 'khl')
SCOREBASE_PROFILE_LIMIT = 60
SCOREBASE_TRANSFER_LIMIT = 30
SCOREBASE_FOOTBALL_POLICY = 'scorebase-bilingual-candidate-v1'
SCOREBASE_FOOTBALL_CHECK_POLICY = 'scorebase-club-punctuation-v2'
FOOTBALL_LEAGUES = {'epl', 'championship', 'laliga', 'bundesliga', 'seriea', 'ligue1', 'primeira',
                    'eredivisie', 'jupiler', 'scottish', 'ucl', 'uel', 'uefa_wcl', 'brasileirao_2',
                    'kleague1', 'kleague2', 'j1', 'mls', 'ligamx'}
KLEAGUE_POLICY = 'kleague-official-roster-v1'
KLEAGUE_TEAM_IDS = {
    'FC Seoul': ('kleague1', 'K09'), 'Ulsan HD FC': ('kleague1', 'K01'),
    'Daejeon Hana Citizen': ('kleague1', 'K10'), 'Incheon United': ('kleague1', 'K18'),
    'Jeonbuk Hyundai Motors FC': ('kleague1', 'K05'), 'Gangwon FC': ('kleague1', 'K21'),
    'Pohang Steelers': ('kleague1', 'K03'), 'Bucheon FC 1995': ('kleague1', 'K26'),
    'Jeju SK': ('kleague1', 'K04'), 'Gwangju FC': ('kleague1', 'K22'),
    'Gimcheon Sangmu': ('kleague1', 'K35'), 'FC Anyang': ('kleague1', 'K27'),
    'Seongnam FC': ('kleague2', 'K08'), 'Daegu FC': ('kleague2', 'K17'),
    'Suwon FC': ('kleague2', 'K29'), 'Gyeongnam FC': ('kleague2', 'K20'),
    'Gimhae FC 2008': ('kleague2', 'K41'), 'Hwaseong FC': ('kleague2', 'K39'),
    'Gimpo FC': ('kleague2', 'K36'), 'Ansan Greeners': ('kleague2', 'K32'),
    'Seoul E-Land FC': ('kleague2', 'K31'), 'Jeonnam Dragons': ('kleague2', 'K07'),
    'Suwon Samsung Bluewings': ('kleague2', 'K02'), 'Busan I\'Park': ('kleague2', 'K06'),
    'Chungnam Asan FC': ('kleague2', 'K34'), 'Paju Frontier': ('kleague2', 'K40'),
    'Yongin FC': ('kleague2', 'K42'), 'Cheonan City': ('kleague2', 'K38'),
}
MAX_NAMU_TEAMS = 24
MAX_INDIVIDUAL_SEARCHES = 100
GOOGLE_METHOD = 'google-search-result-v1'
DAUM_METHOD = 'daum-sports-profile-v1'


def normalize(value):
    value = ''.join(c for c in unicodedata.normalize('NFKD', str(value).translate(str.maketrans({'Ł':'L','ł':'l'}))) if not ('\u0300' <= c <= '\u036f'))
    return re.sub(r'[^\w]+|_', ' ', unicodedata.normalize('NFC', value).lower()).strip()


def source_domain(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443):
        return None
    host = (parsed.hostname or '').lower()
    return next((d for d in DOMAINS if host == d or host.endswith('.' + d)), None)


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.raw = html
        self.parts, self.links, self.headings = [], [], []
        self.skip, self.anchor, self.heading = None, None, None
        self.panel_titles = []
        self.panel = None
        self.depth = 0
        self.feed(html)
        self.text = ' '.join(self.parts)

    def handle_starttag(self, tag, attrs):
        if tag not in ('br', 'img', 'input', 'meta', 'link', 'hr', 'wbr', 'source', 'area', 'base', 'embed', 'param', 'track', 'col'):
            self.depth += 1
        if tag in ('script', 'style', 'noscript'):
            self.skip = tag
        if self.skip:
            return
        attrs = dict(attrs)
        if attrs.get('data-attrid') in ('title', 'title:'):
            self.panel = [self.depth, []]
        if tag == 'a':
            self.anchor = [attrs.get('href', ''), []]
        if tag in ('title', 'h1', 'h2', 'h3'):
            self.heading = [tag, []]

    def handle_endtag(self, tag):
        if self.panel and self.depth == self.panel[0]:
            self.panel_titles.append(' '.join(self.panel[1]))
            self.panel = None
        self.depth = max(0, self.depth - 1)
        if tag == self.skip:
            self.skip = None
        if self.skip:
            return
        if tag == 'a' and self.anchor:
            self.links.append((self.anchor[0], ' '.join(self.anchor[1])))
            self.anchor = None
        if self.heading and tag == self.heading[0]:
            self.headings.append(' '.join(self.heading[1]))
            self.heading = None

    def handle_data(self, data):
        if self.skip or not data.strip():
            return
        self.parts.append(data.strip())
        if self.panel:
            self.panel[1].append(data.strip())
        if self.anchor:
            self.anchor[1].append(data.strip())
        if self.heading:
            self.heading[1].append(data.strip())


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not source_domain(newurl) and urllib.parse.urlsplit(newurl).hostname not in SEARCH_HOSTS:
            raise ValueError('redirect-outside-reviewed-domains')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_page(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'SportsLineupsNameReview/1.0', 'Accept-Language': 'ko-KR,ko;q=0.9'})
    with urllib.request.build_opener(SafeRedirect()).open(request, timeout=20) as response:
        if 'html' not in response.headers.get('Content-Type', ''):
            raise ValueError('not-html')
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('page-too-large')
        page = Page(raw.decode(response.headers.get_content_charset() or 'utf-8', 'replace'))
    if re.search(r'unusual traffic|verify you are human|자동입력 방지문자|비정상적인 접근|보안 확인을 완료|마지막 한 단계|계속하려면 아래 과제 해결|one last step|solve the puzzle', page.text, re.I):
        raise ValueError('search-challenge')
    if urllib.parse.urlsplit(url).hostname in SEARCH_HOSTS and not search_links(page, 'google') and not page.panel_titles and re.search(r'Google Search.*(?:이동하지 않는 경우|redirected)', page.text, re.I):
        raise ValueError('search-results-unavailable')
    if urllib.parse.urlsplit(url).hostname == 'www.bing.com' and not re.search(r'id=["\']b_results["\']', page.raw, re.I) and not re.search(r'검색 결과가 없습니다|no results found', page.text, re.I):
        raise ValueError('search-results-unavailable')
    return page


def search_links(page, engine):
    links = {}
    for url, title in page.links:
        if engine == 'google' and url.startswith('/url?'):
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            url = (query.get('q') or query.get('url') or [''])[0]
        if engine == 'bing' and urllib.parse.urlsplit(url).hostname == 'www.bing.com':
            target = (urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get('u') or [''])[0]
            try:
                url = base64.urlsafe_b64decode(target[2:] + '===').decode() if target.startswith('a1') else ''
            except (ValueError, UnicodeError, base64.binascii.Error):
                url = ''
        if source_domain(url):
            url = urllib.parse.urldefrag(url)[0]
            if len(title) > len(links.get(url, '')):
                links[url] = title
    return list(links.items())[:8]


def candidates(headings):
    result = set()
    for heading in headings:
        title = re.split(r'\s+[|–—-]\s+|[|:(（]', unescape(heading))[0].strip()
        title = re.sub(r'\s+(선수 프로필|프로필|선수 정보|통계).*$', '', title).strip()
        if re.fullmatch(r'[가-힣]{1,12}(?:[ ·ㆍ-][가-힣]{1,12}){0,5}', title) and not re.search(r'선수|뉴스|축구|야구|농구|경기|하이라이트|프로필|통계', title):
            result.add(title)
    return result


def evidence(row, url, page, title, engines, team_dictionary):
    full = normalize(page.text)
    name = normalize(row['name'])
    # Adjacent bilingual full names establish identity; surname matches are never accepted.
    result = []
    for korean in candidates(page.headings + [title]):
        ko = normalize(korean)
        paired = re.search(r'(?<!\w)' + re.escape(ko + ' ' + name) + r'(?!\w)', full) or re.search(r'(?<!\w)' + re.escape(name + ' ' + ko) + r'(?!\w)', full)
        if not paired:
            continue
        team = row.get('team', '')
        aliases = [team, team_dictionary.get(team, '')]
        team_match = any(len(normalize(alias)) > 2 and normalize(alias) in full for alias in aliases)
        result.append({'korean': korean, 'url': url, 'domain': source_domain(url), 'engines': sorted(engines),
                       'teamMatched': team_match, 'bilingualNameMatched': True,
                       'contentHash': hashlib.sha256(page.text.encode()).hexdigest()})
    return result


def verify(row, proofs):
    variants = {normalize(p['korean']) for p in proofs}
    if len(variants) != 1:
        return None
    if len({p['domain'] for p in proofs}) < 2 or not any(p['teamMatched'] for p in proofs):
        return None
    return {'name': row['name'], 'korean': proofs[0]['korean'], 'team': row.get('team'),
            'league': row.get('league'), 'method': 'independent-bilingual-sources-v1', 'sources': proofs}


def google_result(row, url, page, team_dictionary):
    """Accept an identifiable Google result without requiring a second publisher."""
    proofs = evidence(row, url, page, '', {'google'}, team_dictionary)
    # Knowledge-panel titles need the exact queried player and sports identity on the page.
    full = normalize(page.text)
    name = normalize(row['name'])
    team = row.get('team', '')
    team_match = any(len(normalize(t)) > 2 and normalize(t) in full
                     for t in (team, team_dictionary.get(team, '')))
    panels = candidates(page.panel_titles)
    if len(panels) == 1 and re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', full) and team_match:
        proofs.append({'korean': next(iter(panels)), 'teamMatched': True,
                       'bilingualNameMatched': False, 'knowledgePanelMatched': True})
    eligible = [p for p in proofs if p['teamMatched']]
    if not eligible or len({normalize(p['korean']) for p in eligible}) != 1:
        return None
    proof = {**eligible[0], 'url': url, 'domain': 'google.com', 'engines': ['google'],
             'contentHash': hashlib.sha256(page.text.encode()).hexdigest()}
    return {'name': row['name'], 'korean': proof['korean'], 'team': team,
            'league': row.get('league'), 'method': GOOGLE_METHOD, 'sources': [proof]}


def daum_result(row, url, page, team_dictionary):
    """Use only Daum's sports person card with exact original name and club."""
    profiles = []
    card_titles = re.findall(r'<c-title\b[^>]*data-href=["\']([^"\']+)["\'][^>]*>([^<]+)</c-title>', page.raw, re.I)
    for href, title in page.links + card_titles:
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(unescape(href)).query)
        if query.get('w') == ['profile2'] and query.get('coll') == ['person-main']:
            profiles.extend(candidates([title]))
    if len(set(profiles)) != 1:
        return None
    full, name = normalize(page.text), normalize(row['name'])
    profile = full[full.find(normalize(profiles[0])):][:500]
    if not re.search(r'(?:축구|야구|농구|배구|하키|아이스하키|e스포츠) ?선수 ' + re.escape(name) + r'(?!\w)', profile):
        return None
    team = row.get('team', '')
    korean_team = next((korean for alias, korean in team_dictionary.items() if normalize(alias) == normalize(team)), '')
    if not korean_team or normalize(korean_team) not in profile:
        return None
    proof = {'url': url, 'domain': 'daum.net', 'teamMatched': True,
             'originalNameMatched': True, 'sportsProfileMatched': True,
             'contentHash': hashlib.sha256(page.text.encode()).hexdigest()}
    return {'name': row['name'], 'korean': profiles[0], 'team': team,
            'league': row.get('league'), 'method': DAUM_METHOD, 'sources': [proof]}


def namu_team_roster(team, korean_team, rows, get=fetch_page):
    """Match names only within the same row of the club's bilingual roster."""
    page = None
    url = ''
    last_error = None
    for host in ('namu.moe', 'd.namu.moe', 'm.namu.moe', 'www.namu.moe'):
        candidate = 'https://' + host + '/w/' + urllib.parse.quote(korean_team, safe='')
        try:
            current = get(candidate)
        except Exception as error:
            last_error = error
            continue
        if current.headings and normalize(current.headings[0]) == normalize(korean_team) and re.search(r'(?<!\w)' + re.escape(normalize(team)) + r'(?!\w)', normalize(current.text)):
            page, url = current, candidate
            break
    if page is None:
        if last_error:
            raise last_error
        return {}
    wanted = {normalize(row['name']): row for row in rows}
    matches = {}
    korean_column = roman_column = None
    # shortcut: nested roster tables may be missed; use a table parser if those clubs need coverage.
    for table_row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', page.raw, re.I | re.S):
        cells = [Page(cell).text.strip() for cell in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', table_row, re.I | re.S)]
        if '한글 성명' in cells and '로마자 성명' in cells:
            korean_column, roman_column = cells.index('한글 성명'), cells.index('로마자 성명')
            continue
        if korean_column is None or len(cells) <= max(korean_column, roman_column):
            continue
        row = wanted.get(normalize(cells[roman_column]))
        korean = cells[korean_column]
        if row and candidates([korean]) == {korean}:
            matches.setdefault(normalize(row['name']), set()).add(korean)
    digest = hashlib.sha256(page.raw.encode()).hexdigest()
    return {key: {'name': wanted[key]['name'], 'korean': next(iter(names)), 'team': team,
                  'league': wanted[key].get('league'), 'method': NAMU_POLICY,
                  'sources': [{'url': url, 'domain': 'namu.moe', 'teamMatched': True,
                               'englishNameMatched': True, 'rowMatched': True, 'contentHash': digest}]}
            for key, names in matches.items() if len(names) == 1}


def scorebase_transfer_names(rows, team_dictionary, get=fetch_page):
    """Pair Scorebase's two language profiles by player ID, checking both club names."""
    approved = []
    checked = 0
    for row in rows:
        if checked >= SCOREBASE_TRANSFER_LIMIT:
            break
        if row.get('league') not in FOOTBALL_LEAGUES or len(normalize(row['name']).split()) < 2:
            continue
        team = team_dictionary.get(row.get('team', ''), row.get('team', ''))
        club_words = [word for word in re.findall(r'[가-힣]{2,}', team) if word not in ('대한민국',)]
        if not club_words:
            continue
        checked += 1
        search_url = 'https://www.scorebase.kr/search?' + urllib.parse.urlencode({'q': row['name']})
        try:
            search = get(search_url)
        except (ValueError, OSError, urllib.error.URLError):
            continue
        found = {}
        for path, title in search.links:
            if not re.fullmatch(r'/transfers/[a-z0-9]+', path):
                continue
            korean = re.sub(r'\s+몸값·커리어 상세$', '', title).strip()
            if candidates([korean]) != {korean}:
                continue
            found[path] = korean
        matched = []
        for path, korean in list(found.items())[:5]:
            profile_url = 'https://www.scorebase.kr' + path
            try:
                profile = get(profile_url)
            except (ValueError, OSError, urllib.error.URLError):
                continue
            heading = normalize(profile.headings[0]) if profile.headings else ''
            if not heading.startswith(normalize(korean) + ' 프로필') or not any(normalize(word) in heading for word in club_words):
                continue
            independent = None
            for host in ('namu.moe', 'd.namu.moe', 'm.namu.moe', 'www.namu.moe'):
                namu_url = 'https://' + host + '/w/' + urllib.parse.quote(korean, safe='')
                try:
                    namu = get(namu_url)
                except (ValueError, OSError, urllib.error.URLError):
                    continue
                text = normalize(namu.text)
                if (namu.headings and normalize(namu.headings[0]) == normalize(korean)
                        and re.search(r'(?<!\w)' + re.escape(normalize(row['name'])) + r'(?!\w)', text)
                        and any(normalize(word) in text[:5000] for word in club_words)):
                    independent = {'url': namu_url, 'domain': 'namu.moe',
                                   'englishNameMatched': True, 'koreanNameMatched': True,
                                   'teamMatched': True, 'contentHash': hashlib.sha256(namu.raw.encode()).hexdigest()}
                    break
            korean_source = {'url': profile_url, 'domain': 'scorebase.kr',
                             'koreanNameMatched': True, 'teamMatched': True,
                             'contentHash': hashlib.sha256(profile.raw.encode()).hexdigest()}
            if independent:
                matched.append({'name': row['name'], 'korean': korean, 'team': row['team'],
                                'league': row['league'], 'method': 'scorebase-namu-profile-v1',
                                'sources': [korean_source, independent]})
                continue
            english_url = 'https://www.scorebase.kr/en' + path
            try:
                english = get(english_url)
            except (ValueError, OSError, urllib.error.URLError):
                continue
            english_heading = normalize(english.headings[0]) if english.headings else ''
            if not (english_heading.startswith(normalize(row['name']) + ' ')
                    and (re.search(r'[가-힣]', row['team']) or
                         normalize(row['team']).replace(' ', '') in english_heading.replace(' ', ''))):
                continue
            matched.append({'name': row['name'], 'korean': korean, 'team': row['team'],
                            'league': row['league'], 'method': SCOREBASE_FOOTBALL_POLICY,
                            'sources': [korean_source, {'url': english_url, 'domain': 'scorebase.kr',
                                                         'englishNameMatched': True, 'teamMatched': True,
                                                         'contentHash': hashlib.sha256(english.raw.encode()).hexdigest()}]})
        if len({item['korean'] for item in matched}) == 1 and matched:
            approved.append(matched[0])
    return approved, checked


def resolve(row, get=fetch_page, team_dictionary=None, enabled_engines=None):
    query = row['name'] + ' ' + (row.get('team') or '') + ' -site:wikipedia.org'
    urls = {'google': 'https://www.google.com/search?' + urllib.parse.urlencode({'q': query, 'hl': 'ko'}),
            'daum': 'https://search.daum.net/search?' + urllib.parse.urlencode({'w': 'tot', 'q': row['name']}),
            'bing': 'https://www.bing.com/search?' + urllib.parse.urlencode({'q': row['name'] + ' 한글 이름 -site:wikipedia.org', 'setlang': 'ko'})}
    found, searches, errors = {}, {}, []
    for engine, url in urls.items():
        if enabled_engines is not None and engine not in enabled_engines:
            searches[engine] = {'url': url, 'status': 'disabled-after-block'}
            continue
        try:
            page = get(url)
            if engine == 'google':
                approved = google_result(row, url, page, team_dictionary or {})
                if approved:
                    return approved, {'searches': {'google': {'url': url, 'status': 'direct-name-result'}},
                                      'sourceErrors': [], 'status': 'verified'}
            if engine == 'daum':
                approved = daum_result(row, url, page, team_dictionary or {})
                if approved:
                    searches[engine] = {'url': url, 'status': 'direct-name-result'}
                    return approved, {'searches': searches, 'sourceErrors': [], 'status': 'verified'}
            links = search_links(page, engine)
            searches[engine] = {'url': url, 'status': 'results' if links else 'no-readable-trusted-results'}
            for link, title in links:
                item = found.setdefault(link, {'title': title, 'engines': set()})
                item['engines'].add(engine)
        except (ValueError, OSError, urllib.error.URLError) as exc:
            searches[engine] = {'url': url, 'status': 'unavailable', 'reason': type(exc).__name__,
                                'detail': str(exc)[:120], 'httpStatus': getattr(exc, 'code', None)}
    proofs = []
    for url, result in found.items():
        try:
            proofs.extend(evidence(row, url, get(url), result['title'], result['engines'], team_dictionary or {}))
        except (ValueError, OSError, urllib.error.URLError) as exc:
            errors.append({'url': url, 'reason': type(exc).__name__})
    approved = verify(row, proofs)
    return approved, {'searches': searches, 'sourceErrors': errors, 'status': 'verified' if approved else 'needs-verification'}


def read(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def write(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def priority(row, state, now, visible=frozenset()):
    try: hours = (dt.datetime.fromisoformat(row.get('eventDate', '').replace('Z', '+00:00')) - now).total_seconds()/3600
    except (ValueError, TypeError): hours = 9999
    return (0 if normalize(row['name']) in visible else 1, 0 if -3 <= hours < 48 else 1,
            0 if row.get('kind') in ('lineup', 'starting-pitcher') else 1,
            state['players'].get(normalize(row['name']), {}).get('checkedAt', ''), hours, normalize(row['name']))


def kleague_official_names(rows, get=fetch_page):
    """Use the official current club roster when a team and jersey number match uniquely."""
    grouped = {}
    for row in rows:
        club = KLEAGUE_TEAM_IDS.get(row.get('team'))
        number = str(row.get('number') or '').strip()
        if club and club[0] == row.get('league') and number.isdecimal():
            grouped.setdefault((row['team'], *club), []).append(row)
    found = []
    for (team, league, code), pending in grouped.items():
        url = 'https://www.kleague.com/club/club.do?' + urllib.parse.urlencode({'teamId': code})
        try:
            page = get(url)
        except (ValueError, OSError, urllib.error.URLError):
            continue
        names = {}
        for korean, number in re.findall(r'<span class="name">\s*([^<]+)<span class="small">[^<]*</span>\s*</span>\s*<span class="num campton">No\.([0-9]+)</span>', page.raw):
            if re.search(r'[가-힣]', korean):
                names.setdefault(number, set()).add(unescape(korean).strip())
        digest = hashlib.sha256(page.raw.encode()).hexdigest()
        for row in pending:
            choices = names.get(str(row['number']).strip(), set())
            if len(choices) != 1:
                continue
            found.append({'name': row['name'], 'korean': next(iter(choices)), 'team': team,
                          'league': league, 'method': KLEAGUE_POLICY,
                          'sources': [{'url': url, 'domain': 'kleague.com', 'clubCode': code,
                                       'teamMatched': True, 'jerseyMatched': True, 'contentHash': digest}]})
    return found


def scorebase_roster_names(rows, league_code, get=fetch_page):
    pending = {normalize(row['name']): row for row in rows if row.get('league') == league_code}
    if not pending:
        return []
    code = league_code.upper()
    league = get(f'https://www.scorebase.kr/leagues/{code}')
    team_paths = list(dict.fromkeys(re.findall(r'href=["\'](/teams/[0-9]+)["\']', league.raw)))[:40]
    found = {}
    for path in team_paths:
        url = 'https://www.scorebase.kr' + path
        try:
            page = get(url)
        except (ValueError, OSError, urllib.error.URLError):
            continue
        for player_path, card in re.findall(r'<a[^>]+href=["\'](/players/[0-9]+(?:\?league=' + code + r')?)["\'][^>]*>(.*?)</a>', page.raw, re.S):
            image = re.search(r'<img[^>]+alt=["\']([^"\']+)["\']', card)
            label = re.search(r'<div[^>]*class=["\'][^"\']*font-semibold[^"\']*["\'][^>]*>([^<]+)</div>', card)
            if not image or not label:
                continue
            english, korean = unescape(image.group(1)).strip(), unescape(label.group(1)).strip()
            key = normalize(english)
            if key not in pending or not re.search(r'[가-힣]', korean):
                continue
            source = {'url': url, 'playerUrl': 'https://www.scorebase.kr' + player_path + ('' if '?' in player_path else '?league=' + code),
                      'domain': 'scorebase.kr', 'englishNameMatched': True, 'koreanNameMatched': True,
                      'contentHash': hashlib.sha256(page.raw.encode()).hexdigest()}
            if key in found:
                if found[key] and found[key]['korean'] != korean:
                    found[key] = None
            else:
                row = pending[key]
                found[key] = {'name': row['name'], 'korean': korean, 'team': row.get('team'),
                              'league': league_code, 'method': f'scorebase-{league_code}-roster-v1', 'sources': [source]}
    return [entry for entry in found.values() if entry]


def scorebase_khl_profiles(rows, cache, get=fetch_page, team_dictionary=None):
    """Review KHL player profiles in bounded batches; each profile prints both names."""
    pending = {normalize(row['name']): row for row in rows if row.get('league') == 'khl'}
    if not pending:
        return [], 0
    try:
        league = get('https://www.scorebase.kr/leagues/KHL')
        team_paths = list(dict.fromkeys(re.findall(r'href=["\'](/teams/[0-9]+)["\']', league.raw)))[:40]
    except (ValueError, OSError, urllib.error.URLError):
        team_paths = []
    profiles = {}
    for path in team_paths:
        try:
            page = get('https://www.scorebase.kr' + path)
        except (ValueError, OSError, urllib.error.URLError):
            continue
        title = re.search(r'<title>([^<]+) 하키 팀', page.raw)
        team_name = unescape(title.group(1)).strip() if title else ''
        for player_path in re.findall(r'href=["\'](/players/[a-z0-9]+\?league=KHL)["\']', page.raw):
            profiles.setdefault('https://www.scorebase.kr' + player_path, []).append((path, team_name))
    checked = 0
    found = {}
    now = dt.datetime.now(dt.timezone.utc)
    # A previously verified profile remains usable when the league's team links change.
    # Only exact name order (or a provider middle initial) may match without a team link.
    for url in dict.fromkeys([*profiles, *cache]):
        item = cache.get(url, {})
        if (url not in cache or item.get('retryAt', '9999') <= now.isoformat()) and checked < SCOREBASE_PROFILE_LIMIT:
            checked += 1
            try:
                page = get(url)
                description = re.search(r'<meta name=["\']description["\'] content=["\']KHL\s+([^<(]+)\(([^)]+)\)\s+프로필', page.raw)
                cache[url] = {'korean': unescape(description.group(1)).strip(),
                              'english': unescape(description.group(2)).strip(),
                              'contentHash': hashlib.sha256(page.raw.encode()).hexdigest()} if description else {
                                  'retryAt': (now + dt.timedelta(days=1)).isoformat()}
            except (ValueError, OSError, urllib.error.URLError):
                cache[url] = {'retryAt': (now + dt.timedelta(hours=6)).isoformat()}
                continue
        item = cache.get(url, {})
        english, korean = item.get('english', ''), item.get('korean', '')
        if candidates([korean]) != {korean}:
            continue
        forms = {normalize(english)}
        parts = english.split()
        if len(parts) == 2:
            forms.add(normalize(' '.join(reversed(parts))))
        base_forms = forms.copy()
        for key, row in pending.items():
            provider = row['name'].split()
            if len(provider) == 3 and re.fullmatch(r'[A-Za-z]{1,3}\.', provider[-1]):
                if normalize(' '.join(provider[:-1])) in forms:
                    forms.add(key)
        matches = forms & pending.keys()
        # Provider initials and Russian romanization vary; require the same club for near matches.
        if not matches and korean:
            for key, row in pending.items():
                original = row['name'].split()
                if len(original) == 3 and original[-1].endswith('.'):
                    original = original[:-1]
                if len(original) != 2 or len(parts) != 2:
                    continue
                team_aliases = [row.get('team', ''), (team_dictionary or {}).get(row.get('team', ''), '')]
                team_match = next(((path, title) for path, title in profiles.get(url, []) if title and
                                   any(len(alias) >= 4 and difflib.SequenceMatcher(None, normalize(alias), normalize(title)).ratio() >= .9
                                       for alias in team_aliases)), None)
                if not team_match:
                    continue
                surname = difflib.SequenceMatcher(None, normalize(original[0]), normalize(parts[-1])).ratio()
                given = difflib.SequenceMatcher(None, normalize(original[1]), normalize(parts[0])).ratio()
                if surname >= .85 and given >= .7 and (surname + given) / 2 >= .8:
                    matches.add(key)
        for key in matches:
            row = pending[key]
            variant = key not in base_forms
            team_match = next(((path, title) for path, title in profiles.get(url, []) if title and
                               any(len(alias) >= 4 and difflib.SequenceMatcher(None, normalize(alias), normalize(title)).ratio() >= .9
                                   for alias in (row.get('team', ''), (team_dictionary or {}).get(row.get('team', ''), '')))), None)
            if variant and not team_match and (url in profiles or not (len(row['name'].split()) == 3 and
                                                   normalize(' '.join(row['name'].split()[:-1])) in
                                                   base_forms)):
                continue
            proof = {'url': url, 'domain': 'scorebase.kr', 'englishNameMatched': True,
                     'koreanNameMatched': True, 'leagueMatched': True, 'contentHash': item['contentHash']}
            if variant and team_match:
                proof.update({'teamUrl': 'https://www.scorebase.kr' + team_match[0],
                              'teamMatched': True, 'providerNameVariantMatched': True})
            entry = {'name': row['name'], 'korean': korean, 'team': row.get('team'),
                     'league': 'khl', 'method': 'scorebase-khl-roster-variant-v1' if variant and team_match else 'scorebase-khl-profile-v1', 'sources': [proof]}
            if key in found:
                if found[key] is None or found[key]['korean'] != korean:
                    found[key] = None
            else:
                found[key] = entry
    return [entry for entry in found.values() if entry], checked


def main():
    now = dt.datetime.now(dt.timezone.utc)
    inventory = read(ROOT / 'scripts/player-name-live-inventory.json', {})
    if not inventory.get('records') or now - dt.datetime.fromisoformat(inventory['at'].replace('Z', '+00:00')) > dt.timedelta(hours=2):
        raise ValueError('Fresh non-empty player inventory required')
    approved_path = ROOT / 'scripts/player-name-auto-review.json'
    scorebase_queue_path = ROOT / 'scripts/scorebase-name-candidates.json'
    state_path = ROOT / 'scripts/player-name-search-state.json'
    approved = read(approved_path, {'schemaVersion': 1, 'entries': []})
    scorebase_queue = read(scorebase_queue_path, {'schemaVersion': 1, 'entries': []})
    for entry in scorebase_queue['entries']:
        if entry.get('method') == SCOREBASE_FOOTBALL_POLICY:
            entry['status'] = 'scorebase-bilingual-verified'
    state = read(state_path, {'schemaVersion': 1, 'players': {}})
    feed = read(ROOT / 'dist/nude-feed.json', {'matches': []})
    visible = {normalize(player['name']) for match in feed.get('matches', []) for team in match.get('teams', [])
               for player in team.get('players', []) if isinstance(player.get('name'), str)}
    known = {normalize(r['name']) for r in approved['entries']}
    # Normalize persisted keys so accents and punctuation do not consume duplicate searches.
    state['players'] = {normalize(k): v for k, v in state['players'].items()}
    pending = {}
    contexts = {}
    for row in inventory['records']:
        key = normalize(row['name'])
        if row.get('team'): contexts.setdefault(key, set()).add(normalize(row['team']))
        if any(char.isalpha() and not ('가' <= char <= '힣') for char in row['name']) and key == normalize(row.get('korean', row['name'])) and key not in known:
            if key not in pending or priority(row, state, now, visible) < priority(pending[key], state, now, visible): pending[key] = row
    candidates_for_review = [row for key, row in pending.items() if len(contexts.get(key, set())) == 1]
    candidates_for_review.sort(key=lambda row: priority(row, state, now, visible))
    eligible = [row for row in candidates_for_review if
                state['players'].get(normalize(row['name']), {}).get('policy') != POLICY
                or state['players'].get(normalize(row['name']), {}).get('nextCheckAt', '') <= now.isoformat()]
    eligible.sort(key=lambda row: priority(row, state, now, visible))
    teams = read(ROOT / 'dist/team-ko.json', {})
    scorebase_approved = 0
    scorebase_by_league = dict.fromkeys(SCOREBASE_LEAGUES, 0)
    for league_code in SCOREBASE_LEAGUES:
        try:
            for entry in scorebase_roster_names(candidates_for_review, league_code):
                key = normalize(entry['name'])
                if key in known:
                    continue
                entry['verifiedAt'] = now.isoformat()
                approved['entries'].append(entry)
                known.add(key)
                scorebase_approved += 1
                scorebase_by_league[league_code] += 1
            write(approved_path, approved)
        except (ValueError, OSError, urllib.error.URLError) as exc:
            print('Scorebase', league_code.upper(), 'roster unavailable:', type(exc).__name__)
    profile_cache_path = ROOT / 'scripts/scorebase-khl-profile-cache.json'
    profile_cache = read(profile_cache_path, {})
    scorebase_profiles_checked = 0
    try:
        profile_entries, scorebase_profiles_checked = scorebase_khl_profiles(candidates_for_review, profile_cache, team_dictionary=teams)
        for entry in profile_entries:
            key = normalize(entry['name'])
            if key in known:
                continue
            entry['verifiedAt'] = now.isoformat()
            approved['entries'].append(entry)
            known.add(key)
            scorebase_approved += 1
            scorebase_by_league['khl'] += 1
        write(profile_cache_path, profile_cache)
        write(approved_path, approved)
    except (ValueError, OSError, urllib.error.URLError) as exc:
        print('Scorebase KHL profiles unavailable:', type(exc).__name__)
    transfer_approved = transfer_checked = transfer_candidates_saved = 0
    transfer_candidates = [row for row in candidates_for_review if row.get('league') in FOOTBALL_LEAGUES
                           and len(normalize(row['name']).split()) >= 2
                           and re.search(r'[가-힣]{2,}', teams.get(row.get('team', ''), row.get('team', '')))
                           and (state['players'].get(normalize(row['name']), {}).get('scorebasePolicy') != SCOREBASE_FOOTBALL_CHECK_POLICY
                                or state['players'].get(normalize(row['name']), {}).get('nextScorebaseCheckAt', '') <= now.isoformat())]
    transfer_entries, transfer_checked = scorebase_transfer_names(transfer_candidates, teams)
    for row in transfer_candidates[:transfer_checked]:
        state['players'].setdefault(normalize(row['name']), {}).update({
            'scorebasePolicy': SCOREBASE_FOOTBALL_CHECK_POLICY,
            'nextScorebaseCheckAt': (now + dt.timedelta(hours=24)).isoformat()})
    for entry in transfer_entries:
        key = normalize(entry['name'])
        if key in known:
            continue
        if entry['method'] == SCOREBASE_FOOTBALL_POLICY:
            entry['status'] = 'scorebase-bilingual-verified'
            entry['checkedAt'] = now.isoformat()
            scorebase_queue['entries'] = [old for old in scorebase_queue['entries'] if normalize(old['name']) != key]
            scorebase_queue['entries'].append(entry)
            transfer_candidates_saved += 1
            continue
        entry['verifiedAt'] = now.isoformat()
        approved['entries'].append(entry)
        known.add(key)
        transfer_approved += 1
    write(scorebase_queue_path, scorebase_queue)
    write(approved_path, approved)
    write(state_path, state)
    kleague_approved = 0
    for entry in kleague_official_names(candidates_for_review):
        key = normalize(entry['name'])
        if key in known:
            continue
        entry['verifiedAt'] = now.isoformat()
        approved['entries'].append(entry)
        known.add(key)
        kleague_approved += 1
    write(approved_path, approved)
    deadline = time.monotonic() + 600
    groups = {}
    for row in candidates_for_review:
        team = row.get('team')
        record = state['players'].get(normalize(row['name']), {})
        if team in teams and (record.get('namuPolicy') != NAMU_POLICY or record.get('nextNamuCheckAt', '') <= now.isoformat()):
            groups.setdefault(team, []).append(row)
    checked = namu_checked = namu_approved = search_approved = search_unavailable = 0
    added = scorebase_approved + transfer_approved + kleague_approved
    blocked = {'google': 0, 'bing': 0}
    disabled = set()
    namu_errors = []
    for team, rows in list(groups.items())[:MAX_NAMU_TEAMS]:
        if time.monotonic() >= deadline: break
        try:
            matches = namu_team_roster(team, teams[team], rows)
            delay = dt.timedelta(hours=24)
        except (ValueError, OSError, urllib.error.URLError) as exc:
            matches = {}
            delay = dt.timedelta(hours=6)
            namu_errors.append(f'{team}: {type(exc).__name__}')
        namu_checked += 1
        for row in rows:
            key = normalize(row['name'])
            record = state['players'].setdefault(key, {})
            record['namuPolicy'] = NAMU_POLICY
            record['nextNamuCheckAt'] = (now + delay).isoformat()
        for key, entry in matches.items():
            if key in known: continue
            entry['verifiedAt'] = now.isoformat()
            approved['entries'].append(entry)
            known.add(key)
            state['players'][key].update({'status': 'verified', 'policy': POLICY, 'checkedAt': now.isoformat(), 'method': NAMU_POLICY})
            namu_approved += 1
            added += 1
        write(approved_path, approved)
        write(state_path, state)
        time.sleep(1)
    for row in eligible:
        if checked >= MAX_INDIVIDUAL_SEARCHES or time.monotonic() >= deadline: break
        key = normalize(row['name'])
        if key in known: continue
        entry, report = resolve(row, team_dictionary=teams, enabled_engines={'google', 'daum', 'bing'} - disabled)
        checked += 1
        if entry:
            entry['verifiedAt'] = now.isoformat()
            approved['entries'].append(entry)
            known.add(key)
            added += 1
            search_approved += 1
        delay = dt.timedelta(hours=24) if any(s['status'] == 'results' for s in report['searches'].values()) else dt.timedelta(hours=6)
        state['players'][key] = {**state['players'].get(key, {}), **report, 'policy': POLICY, 'checkedAt': now.isoformat(), 'nextCheckAt': (now + delay).isoformat()}
        write(approved_path, approved)
        write(state_path, state)
        statuses = {engine: report['searches'].get(engine, {}).get('status', 'unavailable') for engine in ('google', 'daum', 'bing')}
        for engine in blocked:
            blocked[engine] = blocked[engine] + 1 if statuses[engine] == 'unavailable' else 0
            if blocked[engine] >= 3:
                disabled.add(engine)
        if all(status in ('unavailable', 'disabled-after-block') for status in statuses.values()):
            search_unavailable += 1
            if search_unavailable >= 3: break
        else:
            search_unavailable = 0
        time.sleep(2)
    summary = {'at': now.isoformat(), 'inventoryRecords': len(inventory['records']), 'pending': len(pending),
               'pendingByLeague': dict(sorted(Counter(row.get('league', 'unknown') for row in pending.values()).items())),
               'eligible': len(eligible), 'scorebaseNhlApproved': scorebase_by_league['nhl'],
               'scorebaseRosterApproved': scorebase_approved, 'scorebaseProfilesChecked': scorebase_profiles_checked,
               'scorebaseFootballChecked': transfer_checked, 'scorebaseFootballApproved': transfer_approved,
               'scorebaseFootballCandidates': transfer_candidates_saved,
               'kleagueOfficialApproved': kleague_approved,
               'namuTeamsChecked': namu_checked, 'namuApproved': namu_approved,
               'searchChecked': checked, 'searchApproved': search_approved, 'approved': added,
               'searchUnavailable': search_unavailable >= 3,
               'namuErrors': namu_errors,
               'collectionFailures': len(inventory.get('failures', [])), 'policy': 'Unverified names remain English'}
    write(ROOT / 'scripts/player-name-run-report.json', summary)
    print(json.dumps(summary))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as report:
            report.write('## Player name update\n\n' + '\n'.join(f'- {key}: {value}' for key, value in summary.items()) + '\n')
    if checked and not added:
        print('::warning::No new names were approved; workflow success does not mean translation success. See player-name-search-state.json; search access may be blocked.')


if __name__ == '__main__':
    main()
