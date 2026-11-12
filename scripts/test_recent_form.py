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


if __name__ == '__main__':
    main()
