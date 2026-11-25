import importlib.util
import json
from pathlib import Path
from unittest import TestCase, main

spec = importlib.util.spec_from_file_location('recent_form', Path(__file__).with_name('recent_form.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
FIXTURES = Path(__file__).with_name('fixtures')


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


def fake_espn(urls):
    """Serve the saved ESPN responses (real responses from 2026-11-03, trimmed) and record every call."""
    files = {
        'basketball/nba/scoreboard?dates=20261102': 'espn-scoreboard-nba-20261102.json',
        'soccer/usa.1/scoreboard?dates=20261107': 'espn-scoreboard-mls-20261107.json',
        'basketball/nba/summary?event=401909907': 'espn-summary-nba-401909907.json',
        'soccer/eng.1/summary?event=401879244': 'espn-summary-epl-401879244.json',
    }
    def fetch(url):
        urls.append(url)
        for key, name in files.items():
            if key in url:
                return fixture(name)
        raise RuntimeError('HTTP 404 ' + url)
    return fetch


NBA_ITEM = {'league': 'nba', 'kickoff': '2026-11-03T00:00:00Z', 'teams': {'home': 'CLE', 'away': 'OKC'}, 'names': {}}


class RecentForm(TestCase):
    def test_summary_gives_oldest_first_form_and_records(self):
        sides = module.read_summary(fixture('espn-summary-nba-401909907.json'))
        self.assertEqual(sides['home'], {'form': ['W', 'W', 'W', 'L', 'W'], 'record': '4-2', 'sideRecord': '3-0'})
        self.assertEqual(sides['away'], {'form': ['W', 'W', 'W', 'L', 'L'], 'record': '4-2', 'sideRecord': '1-2'})

    def test_order_comes_from_game_dates_not_from_espn_list_order(self):
        summary = fixture('espn-summary-nba-401909907.json')
        for team in summary['lastFiveGames']:
            team['events'].reverse()
        self.assertEqual(module.read_summary(summary)['home']['form'], ['W', 'W', 'W', 'L', 'W'])

    def test_soccer_keeps_draws_and_has_no_invented_home_record(self):
        sides = module.read_summary(fixture('espn-summary-epl-401879244.json'))
        self.assertEqual(sides['home']['form'], ['W', 'D', 'L', 'L', 'W'])   # Brighton: league, Conference League, cup — all competitions
        self.assertEqual(sides['home']['record'], '6-1-2')                     # ESPN soccer total is W-D-L
        self.assertNotIn('sideRecord', sides['home'])

    def test_soccer_venue_record_requires_complete_matching_season(self):
        def game(date, own_side, own_score, other_score, neutral=False):
            return {'date': date, 'competitions': [{'neutralSite': neutral, 'status': {'type': {'completed': True}},
                'competitors': [{'team': {'id': '1'}, 'homeAway': own_side, 'score': {'value': own_score}},
                                {'team': {'id': '2'}, 'homeAway': 'away' if own_side == 'home' else 'home', 'score': {'value': other_score}}]}]}
        schedule = {'events': [game('2026-11-01T12:00:00Z', 'home', 2, 0),
                               game('2026-11-02T12:00:00Z', 'away', 1, 1),
                               game('2026-11-03T12:00:00Z', 'home', 1, 0, True)]}
        cutoff = '2026-11-20T12:00:00Z'
        self.assertEqual(module.venue_record(schedule, '1', 'home', '2-1-0', cutoff), '1-0-0')
        self.assertIsNone(module.venue_record(schedule, '1', 'home', '3-0-0', cutoff))
        self.assertIsNone(module.venue_record(schedule, '1', 'home', '2-1-0', '2026-11-02T00:00:00Z'))

    def test_soccer_enrich_fills_verified_venue_record(self):
        item = {'league': 'epl', 'kickoff': '2026-11-20T12:00:00Z', 'espnEventId': 'next',
                'logos': {'home': 'home.png', 'away': 'away.png'}, 'teams': {'home': 'H', 'away': 'A'}}
        summary = {'header': {'season': {'year': 2026}, 'competitions': [{'competitors': [
            {'homeAway': 'home', 'team': {'id': '1'}, 'record': [{'type': 'total', 'summary': '1-0-0'}]},
            {'homeAway': 'away', 'team': {'id': '2'}, 'record': [{'type': 'total', 'summary': '0-0-1'}]}]}]}}
        schedule = {'events': [{'date': '2026-11-01T12:00:00Z', 'competitions': [{
            'status': {'type': {'completed': True}}, 'neutralSite': False, 'competitors': [
                {'team': {'id': '1'}, 'homeAway': 'home', 'score': {'value': 2}},
                {'team': {'id': '2'}, 'homeAway': 'away', 'score': {'value': 0}}]}]}]}
        calls = []
        def fetch(url):
            calls.append(url)
            return summary if '/summary?' in url else schedule
        module.enrich_recent_form({'items': [item]}, {}, fetch, pause=0)
        self.assertEqual(item['records']['home'], {'record': '1-0-0', 'sideRecord': '1-0-0'})
        self.assertEqual(item['records']['away'], {'record': '0-0-1', 'sideRecord': '0-0-1'})
        self.assertEqual(len(calls), 3)
        old = dict(item, records={'home': {'record': '1-0-0'}, 'away': {'record': '0-0-1'}},
                   formCheckedAt=module.now_iso())
        old.pop('venueCheckedAt', None)
        calls.clear()
        renewed = dict(item, records={})
        module.enrich_recent_form({'items': [renewed]}, {'items': [old]}, fetch, pause=0)
        self.assertEqual(renewed['records']['home']['sideRecord'], '1-0-0')
        self.assertIn('venueCheckedAt', renewed)
        calls.clear()
        reused = dict(item, records={})
        module.enrich_recent_form({'items': [reused]}, {'items': [renewed]}, fetch, pause=0)
        self.assertEqual(calls, [])

    def test_soccer_reuses_venue_record_when_season_total_is_unchanged(self):
        now = 1795348800
        item = {'league': 'epl', 'kickoff': '2026-11-24T12:00:00Z', 'espnEventId': 'next',
                'logos': {'home': 'home.png', 'away': 'away.png'}, 'teams': {'home': 'H', 'away': 'A'}}
        old = dict(item, formCheckedAt='2026-11-22T00:00:00Z', venueCheckedAt='2026-11-22T11:00:00Z',
                   records={'home': {'record': '1-0-0', 'sideRecord': '1-0-0'},
                            'away': {'record': '0-0-1', 'sideRecord': '0-0-1'}})
        summary = {'header': {'season': {'year': 2026}, 'competitions': [{'competitors': [
            {'homeAway': 'home', 'team': {'id': '1'}, 'record': [{'type': 'total', 'summary': '1-0-0'}]},
            {'homeAway': 'away', 'team': {'id': '2'}, 'record': [{'type': 'total', 'summary': '0-0-1'}]}]}]}}
        calls = []
        def fetch(url):
            calls.append(url)
            return summary
        module.enrich_recent_form({'items': [item]}, {'items': [old]}, fetch, now=now, pause=0)
        self.assertEqual(len(calls), 1)
        self.assertIn('/summary?', calls[0])
        self.assertEqual(item['records']['home']['sideRecord'], '1-0-0')
        self.assertEqual(item['records']['away']['sideRecord'], '0-0-1')

    def test_more_than_80_matches_reach_summary(self):
        items = [dict(NBA_ITEM, espnEventId=str(index), logos={'home': 'home.png', 'away': 'away.png'},
                      teams={'home': f'H{index}', 'away': f'A{index}'}) for index in range(81)]
        calls = []
        def fetch(url):
            calls.append(url)
            return {}
        stats = module.enrich_recent_form({'items': items}, {}, fetch, pause=0)
        self.assertEqual(stats['summaryCalls'], 81)
        self.assertEqual(len(calls), 81)

    def test_mls_playoff_records_fall_back_to_regular_season_standings(self):
        item = {'league': 'mls', 'kickoff': '2026-11-23T00:00:00Z', 'espnEventId': 'playoff',
                'logos': {'home': 'home.png', 'away': 'away.png'},
                'teams': {'home': 'NSH', 'away': 'CIN'},
                'names': {'home': 'Nashville SC', 'away': 'FC Cincinnati'}}
        summary = {'header': {'competitions': [{'competitors': [
            {'homeAway': 'home', 'team': {'displayName': 'Nashville SC'}, 'record': []},
            {'homeAway': 'away', 'team': {'displayName': 'FC Cincinnati'}, 'record': []}]}]}}
        standings = {'children': [{'standings': {'entries': [
            {'team': {'id': '1', 'displayName': 'Nashville SC'}, 'stats': [{'name': 'overall', 'displayValue': '1-0-0'}]},
            {'team': {'id': '2', 'displayName': 'FC Cincinnati'}, 'stats': [{'name': 'overall', 'displayValue': '0-0-1'}]}]}}]}
        season = {'events': [{'season': {'slug': 'regular-season'}, 'status': {'type': {'completed': True}},
                              'competitions': [{'competitors': [
                                  {'homeAway': 'home', 'team': {'id': '1'}, 'score': '2'},
                                  {'homeAway': 'away', 'team': {'id': '2'}, 'score': '1'}]}]}]}
        urls = []
        def fetch(url):
            urls.append(url)
            return standings if '/standings?' in url else season if '/scoreboard?' in url else summary
        module.enrich_recent_form({'items': [item]}, {}, fetch, pause=0)
        self.assertEqual(item['records'], {'home': {'record': '1-0-0', 'sideRecord': '1-0-0'},
                                           'away': {'record': '0-0-1', 'sideRecord': '0-0-1'}})
        self.assertEqual(len(urls), 3)

    def test_mls_venue_record_requires_standings_match(self):
        item = {'league': 'mls', 'kickoff': '2026-11-23T00:00:00Z', 'espnEventId': 'playoff',
                'logos': {'home': 'home.png', 'away': 'away.png'},
                'teams': {'home': 'NSH', 'away': 'CIN'},
                'names': {'home': 'Nashville SC', 'away': 'FC Cincinnati'}}
        summary = {'header': {'competitions': [{'competitors': []}]}}
        standings = {'children': [{'standings': {'entries': [
            {'team': {'id': '1', 'displayName': 'Nashville SC'}, 'stats': [{'name': 'overall', 'displayValue': '2-0-0'}]},
            {'team': {'id': '2', 'displayName': 'FC Cincinnati'}, 'stats': [{'name': 'overall', 'displayValue': '0-0-2'}]}]}}]}
        season = {'events': [{'season': {'slug': 'regular-season'}, 'status': {'type': {'completed': True}},
                              'competitions': [{'competitors': [
                                  {'homeAway': 'home', 'team': {'id': '1'}, 'score': '2'},
                                  {'homeAway': 'away', 'team': {'id': '2'}, 'score': '1'}]}]}]}
        module.enrich_recent_form({'items': [item]}, {},
                                  lambda url: standings if '/standings?' in url else season if '/scoreboard?' in url else summary,
                                  pause=0)
        self.assertEqual(item['records'], {'home': {'record': '2-0-0'}, 'away': {'record': '0-0-2'}})

    def test_rotowire_codes_espn_spells_differently(self):
        board = fixture('espn-scoreboard-nba-20261102.json')['events']
        for home, away in (('SAS', 'UTA'), ('GSW', 'PHX'), ('NYK', 'BKN'), ('MEM', 'NOP')):
            item = {'league': 'nba', 'kickoff': '2026-11-03T01:00:00Z', 'teams': {'home': home, 'away': away}, 'names': {}}
            self.assertIsNotNone(module.match_event(item, board), home + ' vs ' + away)

    def test_known_name_aliases_match_both_sides(self):
        board = fixture('espn-scoreboard-mls-20261107.json')['events']
        for home, away, kickoff in (('New York Red Bulls', 'Atlanta United', '2026-11-07T21:00:00Z'),
                                    ('Seattle Sounders FC', 'Los Angeles Football Club', '2026-11-08T00:00:00Z'),
                                    ('Real Salt Lake', 'Los Angeles Galaxy', '2026-11-08T00:00:00Z')):
            item = {'league': 'mls', 'kickoff': kickoff, 'teams': {'home': 'X1', 'away': 'X2'}, 'names': {'home': home, 'away': away}}
            self.assertIsNotNone(module.match_event(item, board), home)

    def test_verified_club_aliases_match_espn_directory(self):
        for source, espn in [('Deportivo Alaves', 'Alavés'), ('Hamburger SV', 'Hamburg SV'),
                             ('Mönchengladbach', 'Borussia Mönchengladbach'),
                             ('FSV Mainz 05', 'Mainz'), ('SV 07 Elversberg', 'SV Elversberg'),
                             ('1. FC Köln', 'FC Cologne'), ('1899 Hoffenheim', 'TSG Hoffenheim')]:
            self.assertEqual(module.name_key(source), module.name_key(espn), source)

    def test_shared_abbreviation_does_not_swap_manchester_and_bayern(self):
        item = {'league': 'ucl', 'kickoff': '2026-11-03T20:00:00Z',
                'teams': {'home': 'MUN', 'away': 'ROM'},
                'names': {'home': 'Manchester United', 'away': 'Roma'}}
        wrong = {'id': 'bayern', 'date': item['kickoff'], 'competitions': [{'competitors': [
            {'homeAway': 'home', 'team': {'abbreviation': 'MUN', 'displayName': 'Bayern Munich'}},
            {'homeAway': 'away', 'team': {'abbreviation': 'ROM', 'displayName': 'Roma'}}]}]}
        right = {'id': 'united', 'date': item['kickoff'], 'competitions': [{'competitors': [
            {'homeAway': 'home', 'team': {'abbreviation': 'MAN', 'displayName': 'Manchester United'}},
            {'homeAway': 'away', 'team': {'abbreviation': 'ROMA', 'displayName': 'AS Roma'}}]}]}
        self.assertEqual(module.match_event(item, [wrong, right])['id'], 'united')

    def test_verified_scoreboard_logos_follow_team_sides(self):
        board = fixture('espn-scoreboard-nba-20261102.json')
        event = module.match_event(NBA_ITEM, board['events'])
        for side in event['competitions'][0]['competitors']:
            side['team']['logo'] = 'https://example.com/' + side['team']['abbreviation'] + '.png'
        def fetch(url):
            return board if 'scoreboard?' in url else fixture('espn-summary-nba-401909907.json')
        payload = {'items': [dict(NBA_ITEM)]}
        module.enrich_recent_form(payload, {}, fetch, pause=0)
        self.assertEqual(payload['items'][0]['logos'], {
            'home': 'https://example.com/CLE.png', 'away': 'https://example.com/OKC.png'})

    def test_missing_scoreboard_uses_verified_team_directory_for_logos(self):
        item = {'league': 'ucl', 'kickoff': '2026-11-03T20:00:00Z',
                'teams': {'home': 'GLI', 'away': 'LIL'}, 'names': {'home': 'Glimt', 'away': 'Lille'}}
        teams = [{'team': {'displayName': name, 'id': id, 'logos': [
            {'href': f'https://a.espncdn.com/i/teamlogos/soccer/500/{id}.png', 'rel': ['default']}]}}
            for name, id in [('Bodo/Glimt', '2980'), ('Lille', '166'), ('Bayern Munich', '132')]]
        urls = []
        def fetch(url):
            urls.append(url)
            return {'sports': [{'leagues': [{'teams': teams}]}]} if '/teams?' in url else {'events': []}
        payload = {'items': [item]}
        stats = module.enrich_recent_form(payload, {}, fetch, pause=0)
        self.assertEqual(stats['logoDirectoryCalls'], 1)
        self.assertEqual(item['logos'], {'home': 'https://a.espncdn.com/i/teamlogos/soccer/500/2980.png',
                                         'away': 'https://a.espncdn.com/i/teamlogos/soccer/500/166.png'})
        self.assertEqual(len(urls), 2)

    def test_match_requires_both_teams_and_nearest_kickoff(self):
        def event(event_id, kickoff, away):
            return {'id': event_id, 'date': kickoff, 'competitions': [{'competitors': [
                {'homeAway': 'home', 'team': {'abbreviation': 'BOS'}},
                {'homeAway': 'away', 'team': {'abbreviation': away}},
            ]}]}
        item = {'league': 'mlb', 'kickoff': '2026-11-03T19:00:00Z',
                'teams': {'home': 'BOS', 'away': 'NYY'}, 'names': {}}
        earlier = event('first', '2026-11-03T17:00:00Z', 'NYY')
        exact = event('second', item['kickoff'], 'NYY')
        self.assertEqual(module.match_event(item, [earlier, exact])['id'], 'second')
        self.assertIsNone(module.match_event(item, [event('wrong', item['kickoff'], 'NYM')]))
        self.assertIsNone(module.match_event(item, [exact, event('ambiguous', item['kickoff'], 'NYY')]))

    def test_recent_form_excludes_the_current_game(self):
        summary = fixture('espn-summary-nba-401909907.json')
        summary['lastFiveGames'][0]['events'].append({
            'gameDate': '2026-11-03T00:00:00Z', 'gameResult': 'L',
        })
        self.assertEqual(module.read_summary(summary, '2026-11-03T00:00:00Z')['home']['form'],
                         ['W', 'W', 'W', 'L', 'W'])

    def test_unknown_teams_are_not_guessed(self):
        board = fixture('espn-scoreboard-mls-20261107.json')['events']
        item = {'league': 'mls', 'kickoff': '2026-11-07T21:00:00Z', 'teams': {'home': 'AAA', 'away': 'BBB'}, 'names': {'home': 'Nobody FC', 'away': 'Nowhere'}}
        self.assertIsNone(module.match_event(item, board))

    def test_enrich_counts_calls_and_reuses_previous_run(self):
        urls = []
        payload = {'items': [dict(NBA_ITEM)]}
        stats = module.enrich_recent_form(payload, {}, fake_espn(urls), pause=0)
        item = payload['items'][0]
        self.assertEqual(item['espnEventId'], '401909907')
        self.assertEqual(item['recentForm']['home'], ['W', 'W', 'W', 'L', 'W'])
        self.assertEqual(item['records']['away'], {'record': '4-2', 'sideRecord': '1-2'})
        self.assertEqual((stats['scoreboardCalls'], stats['summaryCalls']), (1, 1))
        # 15 minutes later: nothing is fetched again
        urls.clear()
        again = {'items': [dict(NBA_ITEM)]}
        stats = module.enrich_recent_form(again, payload, fake_espn(urls), now=module.time.time() + 900, pause=0)
        self.assertEqual(urls, [])
        self.assertEqual(again['items'][0]['recentForm'], item['recentForm'])
        # 4 hours later: missing logos trigger a scoreboard retry before the summary.
        stats = module.enrich_recent_form({'items': [dict(NBA_ITEM)]}, payload, fake_espn(urls), now=module.time.time() + 4 * 3600, pause=0)
        self.assertEqual(len(urls), 2)
        self.assertIn('scoreboard?dates=20261102', urls[0])
        self.assertIn('summary?event=401909907', urls[1])

    def test_one_failure_leaves_only_that_match_empty(self):
        urls = []
        broken = {'league': 'nba', 'kickoff': '2026-11-03T03:00:00Z', 'teams': {'home': 'LAL', 'away': 'MIA'}, 'names': {}}
        payload = {'items': [broken, dict(NBA_ITEM)]}
        stats = module.enrich_recent_form(payload, {}, fake_espn(urls), pause=0)
        self.assertEqual(stats['failed'], 1)                       # LAL summary is not in the fixtures → 404
        self.assertNotIn('recentForm', payload['items'][0])
        self.assertEqual(payload['items'][1]['recentForm']['home'], ['W', 'W', 'W', 'L', 'W'])

    def test_blocked_stops_calling(self):
        urls = []
        def blocked(url):
            urls.append(url)
            raise RuntimeError('HTTP Error 403: Forbidden')
        items = [dict(NBA_ITEM, kickoff='2026-11-0%dT00:00:00Z' % day) for day in (3, 4, 5, 6)]
        stats = module.enrich_recent_form({'items': items}, {}, blocked, pause=0)
        self.assertTrue(stats['blocked'])
        self.assertEqual(len(urls), 1)
        self.assertFalse(any(item.get('recentForm') for item in items))

    def test_leagues_espn_does_not_cover_are_left_alone(self):
        urls = []
        payload = {'items': [{'league': 'kbo', 'kickoff': '2026-11-03T09:30:00Z', 'teams': {'home': 'LG', 'away': 'KT'}}]}
        stats = module.enrich_recent_form(payload, {}, fake_espn(urls), pause=0)
        self.assertEqual((stats['items'], urls), (0, []))

    def test_kbo_official_results_and_records(self):
        fixture = {'event': {'id': 'next'}, 'prediction': {'kickoff': '2026-11-06T09:30:00Z',
            'teams': {'home': 'SS', 'away': 'KT'}, 'names': {'home': '삼성', 'away': 'KT'}}}
        payload = {'domestic': {'kbo': [fixture]}}
        games = {}
        for index, day in enumerate(('20261105', '20261104', '20261103', '20261102', '20261101')):
            games[day] = [{'G_ID': str(index), 'GAME_STATE_SC': '3', 'CANCEL_SC_ID': '0',
                           'HOME_ID': 'SS', 'AWAY_ID': 'KT',
                           'B_SCORE_CN': '5' if index % 2 == 0 else '1', 'T_SCORE_CN': '2'}]
        html = '<table><tr><td>1</td><td>KT</td><td>144</td><td>90</td><td>49</td><td>5</td><td></td><td></td><td></td><td></td><td>45-2-24</td><td>45-3-25</td></tr>' \
               '<tr><td>2</td><td>삼성</td><td>144</td><td>83</td><td>58</td><td>3</td><td></td><td></td><td></td><td></td><td>43-1-29</td><td>40-2-29</td></tr></table>'
        checked = []
        result = module.enrich_kbo_form(payload, {}, lambda day: (checked.append(day), games.get(day, []))[1], lambda _: html)
        self.assertEqual(result, {'matches': 1, 'withForm': 1, 'withRecords': 1})
        self.assertEqual(checked, list(games))
        self.assertEqual(fixture['prediction']['recentForm']['home'], ['W', 'L', 'W', 'L', 'W'])
        self.assertEqual(fixture['prediction']['recentForm']['away'], ['L', 'W', 'L', 'W', 'L'])
        self.assertEqual(fixture['prediction']['records']['home'], {'record': '83-58', 'sideRecord': '43-29'})
        self.assertEqual(fixture['prediction']['records']['away'], {'record': '90-49', 'sideRecord': '45-25'})

    def test_kbo_unavailable_results_retain_verified_previous(self):
        old = {'event': {'id': 'next'}, 'prediction': {'recentForm': {'home': ['W']}, 'records': {'home': {'record': '83-58'}}}}
        fixture = {'event': {'id': 'next'}, 'prediction': {'kickoff': '2026-11-06T09:30:00Z',
            'teams': {'home': 'SS', 'away': 'KT'}, 'names': {'home': '삼성', 'away': 'KT'}}}
        module.enrich_kbo_form({'domestic': {'kbo': [fixture]}}, {'domestic': {'kbo': [old]}},
                               lambda _: [], lambda _: '', log=lambda *args: None)
        self.assertEqual(fixture['prediction']['recentForm'], {'home': ['W']})
        self.assertEqual(fixture['prediction']['records'], {'home': {'record': '83-58'}})

    def test_live_status_uses_one_board_and_removes_finished_games(self):
        kickoff = '2026-11-12T19:45:00Z'
        rows = [{'league': 'uefa_nl', 'kickoff': kickoff, 'espnEventId': event_id}
                for event_id in ('live', 'done')]
        calls = []
        def fetch(url):
            calls.append(url)
            return {'events': [{'id': 'live', 'status': {'type': {'state': 'in', 'completed': False}}},
                               {'id': 'done', 'status': {'type': {'state': 'post', 'completed': True}}}]}
        result = module.refresh_match_status({'items': rows}, fetch, now=1794517200)
        self.assertEqual(result, {'boards': 1, 'checked': 2})
        self.assertEqual([row['matchStatus'] for row in rows], ['live', 'finished'])
        self.assertEqual(len(calls), 1)

    def test_ligamx_playoff_uses_standings_and_team_schedule_records(self):
        item = {
            'league': 'ligamx',
            'kickoff': '2026-11-27T01:00:00Z',
            'teams': {'home': 'GDL', 'away': 'CAZ'},
            'names': {'home': 'Guadalajara', 'away': 'Cruz Azul'},
            'espnEventId': '999001',
            'formCheckedAt': '2026-11-26T00:00:00Z',
            'recentForm': {'home': ['W', 'D'], 'away': ['W', 'W']},
        }
        standings = {
            'children': [{
                'name': '2026 Torneo Apertura',
                'standings': {
                    'entries': [
                        {'team': {'id': '219', 'displayName': 'Guadalajara'}, 'stats': [{'name': 'overall', 'displayValue': '1-1-0'}]},
                        {'team': {'id': '218', 'displayName': 'Cruz Azul'}, 'stats': [{'name': 'overall', 'displayValue': '1-0-1'}]},
                    ]
                }
            }]
        }
        schedules = {
            '219': {'events': [
                {'date': '2026-11-10T01:00:00Z', 'competitions': [{'status': {'type': {'completed': True}}, 'competitors': [
                    {'homeAway': 'home', 'team': {'id': '219'}, 'score': {'value': 2}},
                    {'homeAway': 'away', 'team': {'id': '100'}, 'score': {'value': 0}},
                ]}]},
                {'date': '2026-11-15T01:00:00Z', 'competitions': [{'status': {'type': {'completed': True}}, 'competitors': [
                    {'homeAway': 'away', 'team': {'id': '219'}, 'score': {'value': 1}},
                    {'homeAway': 'home', 'team': {'id': '101'}, 'score': {'value': 1}},
                ]}]},
            ]},
            '218': {'events': [
                {'date': '2026-11-11T01:00:00Z', 'competitions': [{'status': {'type': {'completed': True}}, 'competitors': [
                    {'homeAway': 'away', 'team': {'id': '218'}, 'score': {'value': 3}},
                    {'homeAway': 'home', 'team': {'id': '102'}, 'score': {'value': 1}},
                ]}]},
                {'date': '2026-11-16T01:00:00Z', 'competitions': [{'status': {'type': {'completed': True}}, 'competitors': [
                    {'homeAway': 'home', 'team': {'id': '218'}, 'score': {'value': 0}},
                    {'homeAway': 'away', 'team': {'id': '103'}, 'score': {'value': 2}},
                ]}]},
            ]},
        }
        def fetch(url):
            if '/soccer/mex.1/standings?season=2026' in url:
                return standings
            if '/teams/219/schedule?season=2026' in url:
                return schedules['219']
            if '/teams/218/schedule?season=2026' in url:
                return schedules['218']
            raise AssertionError('unexpected url: ' + url)

        now_ts = 1795568400  # 2026-11-26T01:00:00Z
        module.enrich_recent_form({'items': [item]}, {'items': [dict(item)]}, fetch, now=now_ts, pause=0)
        self.assertEqual(item['records']['home'], {'record': '1-1-0', 'sideRecord': '1-0-0'})
        self.assertEqual(item['records']['away'], {'record': '1-0-1', 'sideRecord': '1-0-0'})


if __name__ == '__main__':
    main()
