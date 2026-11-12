# -*- coding: utf-8 -*-
"""Collect published match probabilities; never infer them from picks or scores."""
import concurrent.futures as futures
import datetime as dt
import html
import json
from pathlib import Path
import re
import urllib.request
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
UTC = dt.timezone.utc
KST = dt.timezone(dt.timedelta(hours=9))
PATHS = dict(re.findall(r"(\w+): \{path:'([^']+)'", (ROOT/'dist/app.js').read_text()))
HUBS = dict(ucl='champions-league', uel='europa-league', epl='premier-league', championship='championship', laliga='la-liga', bundesliga='bundesliga', seriea='serie-a', ligue1='ligue-1', eredivisie='eredivisie', jupiler='belgian-pro-league', primeira='primeira-liga', scottish='scottish-premiership', j1='j1-league', mls='mls')
WIDGET_LEAGUES = dict(nhl='NHL',khl='KHL',nba='NBA',kbl='KBL',wkbl='WKBL',kbo='KBO',kleague1='K_LEAGUE_1',kleague2='K_LEAGUE_2',v_league='V_LEAGUE',v_league_w='V_LEAGUE_W',uefa_nl='UEFA_NL',ligamx='LIGA_MX')
ALIASES = {'intermilan':'internazionale','sportinglisbon':'sportingcp','lasklinz':'lask','bayern':'bayernmunchen','bayernmunich':'bayernmunchen','fcbayernmunich':'bayernmunchen','fcbayernmunchen':'bayernmunchen','scfreiburg':'freiburg','manutd':'manchesterunited','vikingfk':'viking','realbetis':'betis','shakhtardonetsk':'shakhtardonetsk','yokohamamarinos':'yokohamafmarinos','vvarennagasaki':'vvarennagasaki'}

def key(name):
    value = ''.join(c for c in unicodedata.normalize('NFKD', name).lower() if c.isalnum() and not unicodedata.combining(c))
    return ALIASES.get(value, value)

def date(value):
    return dt.datetime.fromisoformat(value.replace('Z','+00:00'))

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent':'SportsLineups/1.0 (public match probability verification)'})
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read().decode('utf-8')

def json_fetch(url):
    return json.loads(fetch(url))

def parse_mole(source):
    event = None
    for script in re.findall(r'<script\b[^>]*>(.*?)</script>', source, re.S|re.I):
        if '"SportsEvent"' not in script:
            continue
        try:
            item = json.loads(script)
            if item.get('@type') == 'SportsEvent': event = item
        except (ValueError, AttributeError):
            continue
    if not event: return None
    home, away = event['homeTeam']['name'], event['awayTeam']['name']
    text = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', source)))
    analysis = re.search(r'most likely outcome of this match is a (.+?)(?:The most likely scoreline|Result\b|$)', text, re.I)
    if not analysis: return None
    analysis = analysis.group(1)
    probabilities = {}
    first = re.search(r'^(.+?) win with a probability of ([\d.]+)%', analysis, re.I)
    if first: probabilities[key(first.group(1))] = float(first.group(2))
    probabilities.update((key(name), float(value)) for name, value in re.findall(r'a win for (.+?) has a probability of ([\d.]+)%', analysis, re.I))
    draw = re.search(r'a draw has a probability of ([\d.]+)%', analysis, re.I)
    if not draw or key(home) not in probabilities or key(away) not in probabilities: return None
    values = dict(home=probabilities[key(home)], away=probabilities[key(away)], draw=float(draw.group(1)))
    if abs(sum(values.values())-100) > .5: return None
    return dict(homeName=home, awayName=away, kickoff=event['startDate'], values=values)

def parse_volley(source):
    script = re.search(r'<script[^>]*id="volley-public-data"[^>]*>(.*?)</script>', source, re.S)
    if not script: return []
    data = json.loads(html.unescape(script[1]))['data']
    matches = {str(m['id']):m for m in data.get('upcomingMatches',[])}
    rows = []
    for briefing in data.get('briefings',[]):
        match = matches.get(str(briefing.get('matchId')))
        probability = briefing.get('modelEstimate',{}).get('setAnalysis',{}).get('homeMatchProbability')
        if not match or not isinstance(probability,(int,float)) or not 0 <= probability <= 1: continue
        expires = briefing.get('modelEstimate',{}).get('expiresAt')
        if expires and date(expires) <= dt.datetime.now(UTC): continue
        if briefing.get('homeTeamId') != match.get('homeTeamId') or briefing.get('awayTeamId') != match.get('awayTeamId'): continue
        rows.append(dict(eventId=str(match['id']), homeName=match['homeTeamName'], awayName=match['awayTeamName'], kickoff=match['matchDate'], sourceExpiresAt=expires, publishedAt=briefing.get('generatedAt'), values=dict(home=probability*100,away=(1-probability)*100,draw=0)))
    return rows

def parse_scorebase_widget(source):
    rows = []
    for item in re.findall(r'<li\b[^>]*>(.*?)</li>', source, re.S|re.I):
        line = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', item))).strip()
        match = re.fullmatch(r'(\d{1,2})\.\s*(\d{1,2})\.\s*\([^)]+\)\s*(\d{1,2}):(\d{2})\s+(.+?)\s+vs\s+(.+?)\s+홈\s+(\d{1,3})\s*%\s+(?:무\s+(\d{1,3})\s*%\s+)?원정\s+(\d{1,3})\s*%', line)
        if not match: continue
        month, day, hour, minute, home, away, home_pct, draw_pct, away_pct = match.groups()
        values = dict(home=float(home_pct), away=float(away_pct), draw=float(draw_pct or 0))
        if not all(0 <= value <= 100 for value in values.values()) or abs(sum(values.values())-100) > .5: continue
        rows.append(dict(month=int(month), day=int(day), hour=int(hour), minute=int(minute), homeName=home, awayName=away, values=values))
    return rows

def scorebase_key(name):
    value = re.sub(r'[^a-z0-9가-힣]', '', unicodedata.normalize('NFC',re.sub(r'^HC\s+', '', name, flags=re.I)).lower())
    aliases = {
        '몬트리올캐네디언스':'몬트리올캐나디언스','로스앤젤레스킹스':'la킹스','밴쿠버커넉스':'밴쿠버캐넉스','내슈빌프레데터즈':'내슈빌프레데터스','아브토모빌리스트예카테린부르크':'아프토모빌리스트예카테린부르크','상하이드래곤즈':'상하이드래곤스','메탈루르그마그니토고르스크':'메탈루르크마그니토고르스크',
        '부산kcc이지스':'부산kcc','창원lg세이커스':'창원lg','울산현대모비스피버스':'울산현대모비스','서울삼성썬더스':'서울삼성','고양소노스카이거너스':'고양소노',
        '우리은행':'아산우리은행','bnk썸':'부산bnk썸','삼성생명':'용인삼성생명','kb스타즈':'청주kb스타즈','하나은행':'부천하나은행','신한은행':'인천신한은행',
        '수원한국전력빅스톰':'한국전력빅스톰','kb손해보험':'kb손해보험스타즈','인천대한항공점보스':'대한항공점보스','대전삼성화재블루팡스':'삼성화재블루팡스','서울우리카드우리won':'우리카드우리won','현대캐피탈':'현대캐피탈스카이워커스','부산ok저축은행읏맨':'ok저축은행읏맨',
        '흥국생명':'흥국생명핑크스파이더스','gs칼텍스서울kixx':'gs칼텍스kixx','soop수퍼스':'soop소퍼스','정관장':'정관장레드스파크스',
    }
    return aliases.get(value, value)

def target(event, league):
    competition = event['competitions'][0]
    sides = {c['homeAway']:c['team'] for c in competition['competitors']}
    return dict(league=league,eventId=str(event['id']),kickoff=event['date'],homeId=str(sides['home'].get('id','')),awayId=str(sides['away'].get('id','')),homeName=sides['home']['displayName'],awayName=sides['away']['displayName'])

def collect():
    now = dt.datetime.now(UTC)
    start = now.astimezone(KST).replace(hour=0,minute=0,second=0,microsecond=0)
    end = start + dt.timedelta(days=5)
    checked = now.isoformat()
    errors, targets, forecasts = [], [], []
    def attempt(label, fn):
        try: return fn()
        except Exception as error:
            errors.append(dict(source=label,error=str(error)[:160]))
            return None
    dates = [(start.astimezone(UTC).date()+dt.timedelta(days=i)).strftime('%Y%m%d') for i in range(6)]
    def scoreboard(pair):
        league, day = pair
        response = json_fetch(f'https://site.api.espn.com/apis/site/v2/sports/{PATHS[league]}/scoreboard?dates={day}&limit=200')
        return [target(e,league) for e in response.get('events',[]) if start <= date(e['date']) < end]
    with futures.ThreadPoolExecutor(max_workers=8) as pool:
        jobs = {pool.submit(scoreboard,(league,day)):f'{league}/{day}' for league in PATHS for day in dates}
        for job in futures.as_completed(jobs):
            result = attempt(jobs[job],job.result)
            if result: targets.extend(result)
    projections = attempt('lineups',lambda:json_fetch('https://raw.githubusercontent.com/jimmy896376/sports-lineups/main/dist/projections.json')) or {}
    for league, entries in projections.get('domestic',{}).items():
        for entry in entries:
            event = entry['event']
            if start <= date(event['date']) < end: targets.append(target(event,league))
    targets = list({(t['league'],t['eventId']):t for t in targets}.values())
    print(f'Schedule identities checked: {len(targets)}', flush=True)
    def save(t, values, provider, url, note='', metadata=None):
        if not all(isinstance(v,(int,float)) and 0 <= v <= 100 for v in values.values()) or abs(sum(values.values())-100)>.5: return
        forecasts.append(dict(t,values=values,provider=provider,sourceUrl=url,checkedAt=checked,kind='published-model',note=note,**(metadata or {})))
    def espn(t):
        url = f"https://site.api.espn.com/apis/site/v2/sports/{PATHS[t['league']]}/summary?event={t['eventId']}"
        data = json_fetch(url)
        predictor = data.get('predictor') or {}
        home, away = predictor.get('homeTeam',{}), predictor.get('awayTeam',{})
        event = data.get('header',{}).get('competitions',[{}])[0]
        if str(home.get('id')) != t['homeId'] or str(away.get('id')) != t['awayId'] or abs((date(event['date'])-date(t['kickoff'])).total_seconds())>60: return
        save(t, dict(home=float(home['gameProjection']),away=float(away['gameProjection']),draw=0), 'ESPN', url)
    with futures.ThreadPoolExecutor(max_workers=6) as pool:
        jobs = {pool.submit(espn,t):f"ESPN/{t['eventId']}" for t in targets if t['league'] in ('nba','wnba','mlb','nhl','ncaam')}
        for job in futures.as_completed(jobs): attempt(jobs[job],job.result)
    def mole_league(league):
        hub = f'https://www.sportsmole.co.uk/football/{HUBS[league]}/fixtures.html'
        source = fetch(hub)
        links = set(re.findall(r'href=[\"\']([^\"\']+_game_\d+\.html)',source))
        print(f'Sports Mole {league}: {len(links)} match pages', flush=True)
        for link in sorted(links):
            url = 'https://www.sportsmole.co.uk'+link if link.startswith('/') else link
            row = attempt(url,lambda:parse_mole(fetch(url)))
            if not row: continue
            for t in targets:
                # Some source JSON-LD timestamps have a one-hour DST discrepancy.
                # Exact league and both full team identities remain mandatory.
                if t['league']==league and key(t['homeName'])==key(row['homeName']) and key(t['awayName'])==key(row['awayName']) and abs((date(t['kickoff'])-date(row['kickoff'])).total_seconds())<=5400:
                    save(t,row['values'],'Sports Mole',url,'Match result over regular time; source rounding retained.')
    with futures.ThreadPoolExecutor(max_workers=5) as pool:
        jobs = {pool.submit(mole_league,l):f'Sports Mole/{l}' for l in HUBS if any(t['league']==l for t in targets)}
        for job in futures.as_completed(jobs): attempt(jobs[job],job.result)
    rows = attempt('KOVO',lambda:parse_volley(fetch('https://www.bkvolley.kr/insight?a=13&b=14'))) or []
    for row in rows:
        for t in targets:
            # Stable match ID plus date and both sides guards rescheduled fixtures.
            if t['league']=='kovo' and t['eventId']==row['eventId'] and key(t['homeName'])==key(row['homeName']) and key(t['awayName'])==key(row['awayName']) and date(t['kickoff']).astimezone(KST).date()==date(row['kickoff']).astimezone(KST).date():
                save(t,row['values'],'BK Volley',f"https://www.bkvolley.kr/matches/{row['eventId']}",'Publisher marks its model uncalibrated; probability is not a validated success rate.',dict(sourceExpiresAt=row.get('sourceExpiresAt'),publishedAt=row.get('publishedAt')))
    feed = attempt('displayed lineups',lambda:json.loads((ROOT/'dist/nude-feed.json').read_text())) or {}
    displayed = [m for m in feed.get('matches',[]) if m.get('league') in WIDGET_LEAGUES and m.get('eventId') and len(m.get('teams',[])) == 2 and start <= dt.datetime.fromtimestamp(m.get('kickoff',0)/1000,UTC) < end]
    for league, widget_league in WIDGET_LEAGUES.items():
        if not any(m['league']==league for m in displayed): continue
        url = f'https://www.scorebase.kr/embed/fixtures?league={widget_league}&days=7&limit=100'
        def widget():
            request = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 (compatible; NudeLineups/1.0)','Accept':'text/html'})
            with urllib.request.urlopen(request,timeout=25) as response: return response.read().decode('utf-8')
        source = attempt('Scorebase/'+league,widget)
        if not source: continue
        rows = parse_scorebase_widget(source)
        if not rows: errors.append(dict(source='Scorebase/'+league,error='No published probabilities in widget')); continue
        for m in displayed:
            if m['league'] != league: continue
            kickoff = dt.datetime.fromtimestamp(m['kickoff']/1000,KST)
            home, away = m['teams']
            matches = [r for r in rows if (r['month'],r['day'],r['hour'],r['minute']) == (kickoff.month,kickoff.day,kickoff.hour,kickoff.minute) and scorebase_key(r['homeName']) == scorebase_key(home['name']) and scorebase_key(r['awayName']) == scorebase_key(away['name'])]
            if len(matches) != 1: continue
            t = dict(league=league,eventId=str(m['eventId']),kickoff=kickoff.isoformat(),homeId=str(home['id']),awayId=str(away['id']),homeName=home['name'],awayName=away['name'])
            save(t,matches[0]['values'],'Scorebase',url)
    unique = list({(r['league'],r['eventId']):r for r in forecasts}.values())
    output = dict(schemaVersion=1,asOf=checked,windowStart=start.isoformat(),windowEnd=end.isoformat(),items=unique,coverage=dict(scheduled=len(targets),external=len(unique)),errors=errors)
    path = ROOT/'dist/external-forecasts.json'
    # Atomic replacement. Failed requests never extend an old forecast's freshness.
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    temporary.replace(path)
    print(json.dumps(dict(coverage=output['coverage'],providers={p:sum(r['provider']==p for r in unique) for p in sorted({r['provider'] for r in unique})},errors=len(errors))))
    if not unique: raise SystemExit('No external probabilities collected; inspect provider errors.')

if __name__=='__main__': collect()
