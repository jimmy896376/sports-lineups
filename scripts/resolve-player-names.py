"""Resolve names from public search pages; never transliterate or bypass search challenges."""
import base64
from collections import Counter
import datetime as dt
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
DOMAINS = ('namu.moe', 'transfermarkt.co.kr', 'flashscore.co.kr', 'sofascore.com', 'scorebase.kr',
           'premierleague.com', 'bundesliga.com', 'uefa.com', 'fifa.com', 'nba.com', 'mlb.com', 'nhl.com',
           'liverpoolfc.com', 'mancity.com', 'manutd.com', 'tottenhamhotspur.com', 'arsenal.com',
           'fcbayern.com', 'bvb.de', 'borussia.de', 'vfb.de', 'realmadrid.com', 'fcbarcelona.com',
           'yna.co.kr', 'yonhapnews.co.kr', 'newsis.com', 'news1.kr', 'sportsseoul.com',
           'sportschosun.com', 'sportalkorea.com', 'osen.co.kr', 'xportsnews.com', 'spotvnews.co.kr',
           'mk.co.kr', 'hankyung.com', 'chosun.com', 'donga.com', 'khan.co.kr', 'kbs.co.kr', 'sbs.co.kr')
SEARCH_HOSTS = ('www.google.com', 'www.bing.com', 'search.daum.net')
POLICY = 'precollect-names-v5'
NAMU_POLICY = 'namuwiki-team-roster-v2'
SCOREBASE_NHL_POLICY = 'scorebase-nhl-roster-v1'
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
    for href, title in page.links:
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)
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


def priority(row, state, now):
    try: hours = (dt.datetime.fromisoformat(row.get('eventDate', '').replace('Z', '+00:00')) - now).total_seconds()/3600
    except (ValueError, TypeError): hours = 9999
    return (0 if -3 <= hours < 48 else 1, 0 if row.get('kind') in ('lineup', 'starting-pitcher') else 1,
            state['players'].get(normalize(row['name']), {}).get('checkedAt', ''), hours, normalize(row['name']))


def scorebase_nhl_names(rows, get=fetch_page):
    pending = {normalize(row['name']): row for row in rows if row.get('league') == 'nhl'}
    if not pending:
        return []
    league = get('https://www.scorebase.kr/leagues/NHL')
    team_paths = list(dict.fromkeys(re.findall(r'href=["\'](/teams/[0-9]+)["\']', league.raw)))[:40]
    found = {}
    for path in team_paths:
        url = 'https://www.scorebase.kr' + path
        try:
            page = get(url)
        except (ValueError, OSError, urllib.error.URLError):
            continue
        for player_path, card in re.findall(r'<a[^>]+href=["\'](/players/[0-9]+(?:\?league=NHL)?)["\'][^>]*>(.*?)</a>', page.raw, re.S):
            image = re.search(r'<img[^>]+alt=["\']([^"\']+)["\']', card)
            label = re.search(r'<div[^>]*class=["\'][^"\']*font-semibold[^"\']*["\'][^>]*>([^<]+)</div>', card)
            if not image or not label:
                continue
            english, korean = unescape(image.group(1)).strip(), unescape(label.group(1)).strip()
            key = normalize(english)
            if key not in pending or not re.search(r'[가-힣]', korean):
                continue
            source = {'url': url, 'playerUrl': 'https://www.scorebase.kr' + player_path,
                      'domain': 'scorebase.kr', 'englishNameMatched': True, 'koreanNameMatched': True,
                      'contentHash': hashlib.sha256(page.raw.encode()).hexdigest()}
            if key in found:
                if found[key] and found[key]['korean'] != korean:
                    found[key] = None
            else:
                row = pending[key]
                found[key] = {'name': row['name'], 'korean': korean, 'team': row.get('team'),
                              'league': 'nhl', 'method': SCOREBASE_NHL_POLICY, 'sources': [source]}
    return [entry for entry in found.values() if entry]


def main():
    now = dt.datetime.now(dt.timezone.utc)
    inventory = read(ROOT / 'scripts/player-name-live-inventory.json', {})
    if not inventory.get('records') or now - dt.datetime.fromisoformat(inventory['at'].replace('Z', '+00:00')) > dt.timedelta(hours=2):
        raise ValueError('Fresh non-empty player inventory required')
    approved_path = ROOT / 'scripts/player-name-auto-review.json'
    state_path = ROOT / 'scripts/player-name-search-state.json'
    approved = read(approved_path, {'schemaVersion': 1, 'entries': []})
    state = read(state_path, {'schemaVersion': 1, 'players': {}})
    known = {normalize(r['name']) for r in approved['entries']}
    # Normalize persisted keys so accents and punctuation do not consume duplicate searches.
    state['players'] = {normalize(k): v for k, v in state['players'].items()}
    pending = {}
    contexts = {}
    for row in inventory['records']:
        key = normalize(row['name'])
        if row.get('team'): contexts.setdefault(key, set()).add(normalize(row['team']))
        if any(char.isalpha() and not ('가' <= char <= '힣') for char in row['name']) and key == normalize(row.get('korean', row['name'])) and key not in known:
            if key not in pending or priority(row, state, now) < priority(pending[key], state, now): pending[key] = row
    candidates_for_review = [row for key, row in pending.items() if len(contexts.get(key, set())) == 1]
    candidates_for_review.sort(key=lambda row: priority(row, state, now))
    eligible = [row for row in candidates_for_review if
                state['players'].get(normalize(row['name']), {}).get('policy') != POLICY
                or state['players'].get(normalize(row['name']), {}).get('nextCheckAt', '') <= now.isoformat()]
    eligible.sort(key=lambda row: priority(row, state, now))
    teams = read(ROOT / 'dist/team-ko.json', {})
    scorebase_approved = 0
    try:
        for entry in scorebase_nhl_names(candidates_for_review):
            key = normalize(entry['name'])
            if key in known:
                continue
            entry['verifiedAt'] = now.isoformat()
            approved['entries'].append(entry)
            known.add(key)
            scorebase_approved += 1
        write(approved_path, approved)
    except (ValueError, OSError, urllib.error.URLError) as exc:
        print('Scorebase NHL roster unavailable:', type(exc).__name__)
    deadline = time.monotonic() + 600
    groups = {}
    for row in candidates_for_review:
        team = row.get('team')
        record = state['players'].get(normalize(row['name']), {})
        if team in teams and (record.get('namuPolicy') != NAMU_POLICY or record.get('nextNamuCheckAt', '') <= now.isoformat()):
            groups.setdefault(team, []).append(row)
    checked = namu_checked = namu_approved = search_approved = search_unavailable = 0
    added = scorebase_approved
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
               'eligible': len(eligible), 'scorebaseNhlApproved': scorebase_approved,
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
