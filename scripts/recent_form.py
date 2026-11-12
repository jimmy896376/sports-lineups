"""Attach each team's recent results and season record from ESPN to the lineup items.

For every item in a league ESPN covers, find the ESPN event (by date and team) and read its
summary page once: `lastFiveGames` gives the team's last results (all competitions), and the
header competitors give the season record plus the home/road record. Nothing is invented — a
match that cannot be found or fetched keeps empty fields.

Fields added to an item (all optional):
  espnEventId     ESPN event id used
  recentForm      {'home': ['W','L','D',...], 'away': [...]}  oldest first, newest last, max 5
  records         {'home': {'record': '4-2', 'sideRecord': '3-0'}, 'away': {...}}
                  record = ESPN season total (soccer is W-D-L, e.g. '6-1-2'); sideRecord = this
                  team's home record when home / road record when away (ESPN gives none for soccer)
  formCheckedAt   when ESPN was read (UTC ISO)

ESPN calls per run: one scoreboard per (league, ESPN date) only for items whose event id is not
known yet, plus one summary per item whose data is older than REFRESH_SECONDS. Values from the
previous snapshot are reused in between, so a 15-minute schedule does not re-read every match.
"""
import re
import time
import unicodedata
from html.parser import HTMLParser
from datetime import datetime, timezone
from datetime import timedelta
from zoneinfo import ZoneInfo

ESPN_PATHS = {
    'nba': 'basketball/nba', 'wnba': 'basketball/wnba', 'mlb': 'baseball/mlb', 'nhl': 'hockey/nhl',
    'epl': 'soccer/eng.1', 'championship': 'soccer/eng.2', 'laliga': 'soccer/esp.1',
    'bundesliga': 'soccer/ger.1', 'seriea': 'soccer/ita.1', 'ligue1': 'soccer/fra.1',
    'eredivisie': 'soccer/ned.1', 'jupiler': 'soccer/bel.1', 'primeira': 'soccer/por.1',
    'scottish': 'soccer/sco.1', 'j1': 'soccer/jpn.1', 'mls': 'soccer/usa.1', 'ligamx': 'soccer/mex.1',
    'ucl': 'soccer/uefa.champions', 'uel': 'soccer/uefa.europa',
    'uefa_nl': 'soccer/uefa.nations', 'intl_friendly': 'soccer/fifa.friendly',
    'fifa_world': 'soccer/fifa.world', 'afc_asian_cup': 'soccer/afc.asian.cup',
    'caf_nations': 'soccer/caf.nations', 'uefa_euro': 'soccer/uefa.euro',
    'uefa_u21': 'soccer/uefa.euro_u21',
}
REFRESH_SECONDS = 3 * 3600      # form and records only change after a game; 3 hours keeps calls low
KEEP_STALE_SECONDS = 12 * 3600  # if ESPN fails, previous values younger than this are kept (they were read, not guessed)
MAX_CALLS = 80                  # per run — a ceiling so a bad day never hammers ESPN
RESULT = {'W': 'W', 'L': 'L', 'D': 'D', 'T': 'D'}


class _KboRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell, self.inside = [], None, None, False

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell, self.inside = [], True

    def handle_data(self, data):
        if self.inside:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.inside:
            self.row.append(''.join(self.cell).strip())
            self.inside = False
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def kbo_standings(html):
    """Read regular-season W-L and home/away W-L from KBO's daily team ranking."""
    parser = _KboRows()
    parser.feed(html)
    records = {}
    for row in parser.rows:
        if len(row) < 12 or not row[0].isdigit() or not row[3].isdigit() or not row[4].isdigit():
            continue
        if not re.fullmatch(r'\d+-\d+-\d+', row[10]) or not re.fullmatch(r'\d+-\d+-\d+', row[11]):
            continue
        records[row[1]] = {'record': f'{row[3]}-{row[4]}',
                           'home': '-'.join((row[10].split('-')[0], row[10].split('-')[2])),
                           'away': '-'.join((row[11].split('-')[0], row[11].split('-')[2]))}
    return records


def enrich_kbo_form(payload, previous, fetch_schedule, fetch_standings, now=None, log=print):
    """Use official KBO final scores for last five and official regular-season standings."""
    fixtures = payload.get('domestic', {}).get('kbo', [])
    if not fixtures:
        return {'matches': 0, 'withForm': 0, 'withRecords': 0}
    now = now or datetime.now(timezone.utc)
    previous_by_id = {str(row.get('event', {}).get('id')): row for row in (previous or {}).get('domestic', {}).get('kbo', [])}
    try:
        standings = kbo_standings(fetch_standings('https://www.koreabaseball.com/Record/TeamRank/TeamRankDaily.aspx'))
    except Exception as error:
        log('KBO standings unavailable:', error)
        standings = {}
    boards = {}
    for fixture in fixtures:
        prediction = fixture.get('prediction', {})
        teams = prediction.get('teams', {})
        names = prediction.get('names', {})
        kickoff = datetime.fromisoformat(prediction['kickoff'].replace('Z', '+00:00')).astimezone(ZoneInfo('Asia/Seoul'))
        previous_row = previous_by_id.get(str(fixture.get('event', {}).get('id')), {})
        prior = previous_row.get('prediction', {})
        checked = prior.get('formCheckedAt')
        age = None
        if checked:
            try:
                age = (now - datetime.fromisoformat(checked.replace('Z', '+00:00'))).total_seconds()
            except ValueError:
                pass
        if age is not None and 0 <= age < REFRESH_SECONDS and prior.get('recentForm'):
            prediction['recentForm'] = prior['recentForm']
            prediction['formCheckedAt'] = checked
        else:
            forms = {'home': [], 'away': []}
            for days_back in range(1, 61):
                if all(len(form) >= 5 for form in forms.values()):
                    break
                day = (kickoff.date() - timedelta(days=days_back)).strftime('%Y%m%d')
                if day not in boards:
                    try:
                        boards[day] = fetch_schedule(day)
                    except Exception as error:
                        log('KBO result unavailable:', day, error)
                        boards[day] = []
                for game in reversed(boards[day]):
                    if str(game.get('GAME_STATE_SC')) != '3' or str(game.get('CANCEL_SC_ID')) not in ('0', 'None'):
                        continue
                    try:
                        home, away = int(game['B_SCORE_CN']), int(game['T_SCORE_CN'])
                    except (KeyError, TypeError, ValueError):
                        continue
                    for side, code, score, other in (('home', game.get('HOME_ID'), home, away), ('away', game.get('AWAY_ID'), away, home)):
                        if code == teams.get(side) and len(forms[side]) < 5:
                            forms[side].append('W' if score > other else 'L' if score < other else 'D')
            found = {side: list(reversed(form)) for side, form in forms.items() if form}
            if found:
                prediction['recentForm'] = found
                prediction['formCheckedAt'] = now.isoformat().replace('+00:00', 'Z')
            elif prior.get('recentForm'):
                prediction['recentForm'] = prior['recentForm']
                prediction['formCheckedAt'] = checked
        records = {}
        for side in ('home', 'away'):
            standing = standings.get(names.get(side))
            if standing:
                records[side] = {'record': standing['record'], 'sideRecord': standing[side]}
        if records:
            prediction['records'] = records
        elif prior.get('records'):
            prediction['records'] = prior['records']
    return {'matches': len(fixtures), 'withForm': sum(bool(f['prediction'].get('recentForm')) for f in fixtures),
            'withRecords': sum(bool(f['prediction'].get('records')) for f in fixtures)}
# Lineup-source codes that ESPN spells differently (checked against ESPN scoreboards 2026-11-03)
CODE_ALIASES = {
    'nba': {'GSW': 'GS', 'NYK': 'NY', 'NOP': 'NO', 'SAS': 'SA', 'UTA': 'UTAH', 'WAS': 'WSH', 'PHO': 'PHX', 'BRK': 'BKN'},
    'wnba': {'WAS': 'WSH', 'GSV': 'GS', 'NYL': 'NY', 'LVA': 'LV', 'LAS': 'LA', 'PHO': 'PHX', 'CON': 'CONN'},
    'mlb': {'CWS': 'CHW', 'WAS': 'WSH', 'AZ': 'ARI', 'KCR': 'KC', 'SDP': 'SD', 'SFG': 'SF', 'TBR': 'TB'},
}
NAME_NOISE = {'fc', 'cf', 'sc', 'afc', 'ac', 'ssc', 'club', 'de', 'the', 'cd', 'ud', 'rc', 'sv', 'vfl', 'vfb', 'tsg', 'bv', 'ogc', 'as'}
NAME_ALIASES = {'newyorkredbulls': 'redbullnewyork', 'losangelesfootball': 'lafc', 'losangelesgalaxy': 'lagalaxy',
                'glimt': 'bodoglimt', 'lask': 'lasklinz', 'deportivoalaves': 'alaves',
                'hamburger': 'hamburg', 'monchengladbach': 'borussiamonchengladbach',
                'fsvmainz05': 'mainz', '07elversberg': 'elversberg',
                '1koln': 'cologne', '1899hoffenheim': 'hoffenheim'}


class Blocked(Exception):
    """ESPN answered 403/429 — stop calling for this run."""


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def espn_date(kickoff):
    """ESPN scoreboards are grouped by US Eastern date."""
    moment = datetime.fromisoformat(kickoff.replace('Z', '+00:00'))
    return moment.astimezone(ZoneInfo('America/New_York')).strftime('%Y%m%d')


def name_key(value):
    text = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().lower()
    words = [w for w in re.split(r'[^a-z0-9]+', text) if w and w not in NAME_NOISE]
    key = ''.join(words)
    return NAME_ALIASES.get(key, key)


def item_key(item):
    teams = item.get('teams') or {}
    return (item.get('league'), item.get('kickoff'), teams.get('home'), teams.get('away'))


def side_matches(item, side, competitor):
    team = competitor.get('team') or {}
    wanted = name_key((item.get('names') or {}).get(side))
    if wanted and ESPN_PATHS.get(item.get('league'), '').startswith('soccer/'):
        names = {name_key(team.get(k)) for k in ('displayName', 'shortDisplayName', 'name', 'location')}
        names.discard('')
        return wanted in names
    code = str((item.get('teams') or {}).get(side) or '').upper()
    code = CODE_ALIASES.get(item.get('league'), {}).get(code, code)
    if code and code == str(team.get('abbreviation') or '').upper():
        return True
    return bool(wanted and wanted in {name_key(team.get(k)) for k in ('displayName', 'shortDisplayName', 'name', 'location')})


def match_event(item, events):
    """Return the ESPN event for this item.

    Match both teams and choose the unique closest kickoff. This avoids assigning the wrong
    opponent's record or the first game of a baseball doubleheader."""
    try:
        kickoff = datetime.fromisoformat(item['kickoff'].replace('Z', '+00:00'))
    except (KeyError, TypeError, ValueError):
        return None
    matches = []
    for event in events or []:
        competition = (event.get('competitions') or [{}])[0]
        sides = {c.get('homeAway'): c for c in competition.get('competitors') or []}
        if 'home' not in sides or 'away' not in sides:
            continue
        try:
            start = datetime.fromisoformat(str(event.get('date')).replace('Z', '+00:00'))
        except ValueError:
            continue
        difference = abs((start - kickoff).total_seconds())
        if difference > 3 * 3600:
            continue
        home, away = side_matches(item, 'home', sides['home']), side_matches(item, 'away', sides['away'])
        if home and away:
            matches.append((difference, event))
    matches.sort(key=lambda pair: pair[0])
    return matches[0][1] if matches and (len(matches) == 1 or matches[0][0] < matches[1][0]) else None


def read_summary(summary, kickoff=None):
    """lastFiveGames + header records → {'home': {...}, 'away': {...}} keyed by side."""
    competitors = ((summary.get('header') or {}).get('competitions') or [{}])[0].get('competitors') or []
    by_team = {str((g.get('team') or {}).get('id')): g.get('events') or [] for g in summary.get('lastFiveGames') or []}
    cutoff = datetime.fromisoformat(kickoff.replace('Z', '+00:00')) if kickoff else None
    result = {}
    for competitor in competitors:
        side = competitor.get('homeAway')
        if side not in ('home', 'away'):
            continue
        entry = {}
        games = sorted(by_team.get(str((competitor.get('team') or {}).get('id')), []), key=lambda g: str(g.get('gameDate') or ''))
        if cutoff:
            games = [g for g in games if g.get('gameDate') and datetime.fromisoformat(g['gameDate'].replace('Z', '+00:00')) < cutoff]
        form = [RESULT[g.get('gameResult')] for g in games if g.get('gameResult') in RESULT]
        if form:
            entry['form'] = form[-5:]
        records = {r.get('type'): r.get('summary') for r in competitor.get('record') or [] if r.get('summary')}
        if records.get('total'):
            entry['record'] = str(records['total'])[:40]
        own = records.get('home') if side == 'home' else (records.get('road') or records.get('away'))
        if own:
            entry['sideRecord'] = str(own)[:40]
        if entry:
            result[side] = entry
    return result


def enrich_recent_form(payload, previous, fetch_json, now=None, log=print, pause=0.25):
    """Add recentForm/records to payload['items'] in place. Returns counts for the run log."""
    now = now or time.time()
    before = {item_key(item): item for item in (previous or {}).get('items', [])}
    stats = {'items': 0, 'withForm': 0, 'reused': 0, 'scoreboardCalls': 0, 'summaryCalls': 0, 'logoDirectoryCalls': 0, 'notFound': 0, 'failed': 0, 'blocked': False}
    boards = {}
    calls = 0

    def get(url):
        nonlocal calls
        if stats['blocked'] or calls >= MAX_CALLS:
            raise Blocked('call ceiling or blocked')
        calls += 1
        if pause:
            time.sleep(pause)
        try:
            return fetch_json(url)
        except Exception as error:
            if re.search(r'\b(403|429)\b', str(error)):
                stats['blocked'] = True
                raise Blocked(str(error))
            raise

    def checked_age(old):
        try:
            return now - datetime.fromisoformat(old['formCheckedAt'].replace('Z', '+00:00')).timestamp()
        except (KeyError, TypeError, ValueError, AttributeError):
            return None

    def keep_previous(item, old, limit):
        age = checked_age(old) if old else None
        if age is None or age > limit:
            return False
        for field in ('espnEventId', 'recentForm', 'records', 'formCheckedAt', 'logos'):
            if old.get(field) is not None:
                item[field] = old[field]
        return True

    for item in payload.get('items', []):
        path = ESPN_PATHS.get(item.get('league'))
        if not path:
            continue
        stats['items'] += 1
        old = before.get(item_key(item))
        known_logos = {**((old or {}).get('logos') or {}), **(item.get('logos') or {})}
        needs_logos = not all(known_logos.get(side) for side in ('home', 'away')) and (checked_age(old) is None or checked_age(old) > REFRESH_SECONDS)
        if not needs_logos and keep_previous(item, old, REFRESH_SECONDS):
            stats['reused'] += 1
        else:
            try:
                event_id = item.get('espnEventId') or (old or {}).get('espnEventId')
                event = None
                if not event_id or needs_logos:
                    board_key = (path, espn_date(item['kickoff']))
                    if board_key not in boards:
                        boards[board_key] = get(f'https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard?dates={board_key[1]}&limit=500').get('events', [])
                        stats['scoreboardCalls'] += 1
                    event = match_event(item, boards[board_key])
                    event_id = event and str(event.get('id'))
                if event:
                    competitors = (event.get('competitions') or [{}])[0].get('competitors') or []
                    logos = {side: (next((c for c in competitors if c.get('homeAway') == side), {}).get('team') or {}).get('logo') for side in ('home', 'away')}
                    item['logos'] = {**known_logos, **{side: logo for side, logo in logos.items() if logo}}
                if not event_id:
                    stats['notFound'] += 1
                    keep_previous(item, old, KEEP_STALE_SECONDS)
                elif old and checked_age(old) is not None and checked_age(old) <= REFRESH_SECONDS:
                    current_logos = item.get('logos')
                    keep_previous(item, old, REFRESH_SECONDS)
                    item['logos'] = {**(item.get('logos') or {}), **(current_logos or {})}
                    item['espnEventId'] = event_id
                    stats['reused'] += 1
                else:
                    summary = get(f'https://site.api.espn.com/apis/site/v2/sports/{path}/summary?event={event_id}')
                    stats['summaryCalls'] += 1
                    sides = read_summary(summary, item['kickoff'])
                    item['espnEventId'] = event_id
                    item['formCheckedAt'] = datetime.fromtimestamp(now, timezone.utc).isoformat().replace('+00:00', 'Z')
                    form = {side: v['form'] for side, v in sides.items() if v.get('form')}
                    records = {side: {k: v[k] for k in ('record', 'sideRecord') if v.get(k)} for side, v in sides.items() if v.get('record') or v.get('sideRecord')}
                    if form:
                        item['recentForm'] = form
                    if records:
                        item['records'] = records
            except Blocked:
                keep_previous(item, old, KEEP_STALE_SECONDS)
            except Exception as error:
                stats['failed'] += 1
                log('recent form', item.get('league'), item.get('kickoff'), 'failed:', error)
                keep_previous(item, old, KEEP_STALE_SECONDS)
        if item.get('recentForm'):
            stats['withForm'] += 1
    # Some valid fixtures are absent from ESPN scoreboards. Match their clubs in ESPN's team directory.
    missing = {}
    for item in payload.get('items', []):
        path = ESPN_PATHS.get(item.get('league'), '')
        if (path.startswith('soccer/') or path == 'hockey/nhl') and any(not (item.get('logos') or {}).get(side) for side in ('home', 'away')):
            missing.setdefault(path, []).append(item)
    for path, items in missing.items():
        try:
            directory = get(f'https://site.api.espn.com/apis/site/v2/sports/{path}/teams?limit=500')
            stats['logoDirectoryCalls'] += 1
            teams = [entry.get('team') or {} for sport in directory.get('sports', [])
                     for league in sport.get('leagues', []) for entry in league.get('teams', [])]
            for item in items:
                for side in ('home', 'away'):
                    if (item.get('logos') or {}).get(side):
                        continue
                    wanted = name_key((item.get('names') or {}).get(side))
                    code = str((item.get('teams') or {}).get(side) or '').upper()
                    matches = [team for team in teams if (wanted and wanted in {name_key(team.get(k)) for k in ('displayName', 'shortDisplayName', 'name', 'location')})
                               or (path == 'hockey/nhl' and code and code == str(team.get('abbreviation') or '').upper())]
                    if len(matches) == 1:
                        team = matches[0]
                        logo = team.get('logo') or next((value.get('href') for value in team.get('logos', []) if 'default' in value.get('rel', [])), None)
                        if logo:
                            item.setdefault('logos', {})[side] = logo
        except Blocked:
            break
        except Exception as error:
            stats['failed'] += 1
            log('logo directory', path, 'failed:', error)
    return stats
