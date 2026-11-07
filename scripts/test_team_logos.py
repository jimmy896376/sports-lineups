import importlib.util
from io import BytesIO
from datetime import datetime
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch
from zoneinfo import ZoneInfo

spec = importlib.util.spec_from_file_location('projections', Path(__file__).with_name('update-projections.py'))
projections = importlib.util.module_from_spec(spec)
spec.loader.exec_module(projections)


class TeamLogos(TestCase):
    def test_kleague_results_use_only_completed_games_before_kickoff(self):
        upcoming = {'home': {'id': 'A'}, 'away': {'id': 'B'}, 'status': {'utcTime': '2026-11-08T05:00:00Z'}}
        def played(day, home, away, score, **status):
            return {'home': {'id': home}, 'away': {'id': away},
                    'status': {'utcTime': f'2026-11-{day:02}T05:00:00Z', 'finished': True, 'scoreStr': score, **status}}
        games = [played(1, 'A', 'B', '2 - 1'), played(2, 'C', 'A', '1 - 1'),
                 played(3, 'B', 'C', '0 - 1'), played(4, 'A', 'C', '3 - 0'),
                 played(5, 'C', 'B', '2 - 0'), played(6, 'A', 'C', '4 - 0', awarded=True),
                 played(9, 'B', 'A', '2 - 0')]
        form, records = projections.fotmob_records(games, upcoming)
        self.assertEqual(form, {'home': ['W', 'D', 'W'], 'away': ['L', 'L', 'L']})
        self.assertEqual(records, {'home': {'record': '2-1-0', 'sideRecord': '2-0-0'},
                                   'away': {'record': '0-0-3', 'sideRecord': '0-0-2'}})

    def test_kleague_uses_last_starters_and_header_logos(self):
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 11, 5, 6, tzinfo=ZoneInfo('Asia/Seoul'))
        home = {'id': '133898', 'name': 'Jeju SK'}
        away = {'id': '245905', 'name': 'Gwangju FC'}
        match = {'id': '6503951', 'home': home, 'away': away,
                 'status': {'utcTime': '2026-11-07T05:00:00Z', 'finished': False}}
        detail = {'content': {'lineup': {'lineupType': 'lastStarting11',
                  'homeTeam': {'starters': [{'name': f'Home {i}', 'shirtNumber': str(i+1)} for i in range(11)]},
                  'awayTeam': {'starters': [{'name': f'Away {i}'} for i in range(11)]}}},
                  'header': {'teams': [{'id': 133898, 'imageUrl': 'https://example.com/jeju.png'},
                                       {'id': 245905, 'imageUrl': 'https://example.com/gwangju.png'}]}}
        with patch.object(projections, 'datetime', Clock), patch.object(
                projections, 'fetch_json', side_effect=[{'fixtures': {'allMatches': [match]}}, detail]):
            row = projections.scrape_fotmob_kleague(9080, 'kleague1')[0]
        self.assertEqual([len(row['prediction']['lineups'][side]) for side in ('home', 'away')], [11, 11])
        self.assertEqual(row['prediction']['lineups']['home'][0]['number'], '1')
        self.assertEqual(row['prediction']['logos'], {'home': 'https://example.com/jeju.png',
                                                      'away': 'https://example.com/gwangju.png'})
        self.assertEqual([team['team']['logo'] for team in row['event']['competitions'][0]['competitors']],
                         ['https://example.com/jeju.png', 'https://example.com/gwangju.png'])

    def test_shakhtar_logo_is_in_legacy_projection(self):
        def team(side, code, name):
            players = ''.join(f'<li class="lineup__player"><a title="Player {i}"></a></li>' for i in range(11))
            return (f'<a class="lineup__team is-{side}">' + (f'<img class="lineup__logo" src="https://assets.rotowire.com/images/teamlogo/soccer/Sporting-CP.png?v=11">' if code == 'LIS' else '') + f'<div class="lineup__abbr">{code}</div></a>'
                    f'<div class="lineup__mteam is-{side}">{name}</div>'
                    f'<ul class="lineup__list is-{side}">{players}</ul>')
        page = ('<div class="lineup is-soccer"><div class="lineup__time">November 3 12:45 PM ET</div>'
                + team('home', 'DON', 'FC Shakhtar Donetsk') + team('visit', 'LIS', 'Sporting CP'))
        response = BytesIO(page.encode())
        with patch('urllib.request.urlopen', return_value=response):
            row = projections.scrape_page('ucl', 'UCL', 'soccer')[0]
        self.assertEqual(row['logos']['home'], 'https://a.espncdn.com/i/teamlogos/soccer/500/493.png')
        self.assertEqual(row['logos']['away'], 'https://assets.rotowire.com/images/teamlogo/soccer/Sporting-CP.png?v=11')

    def test_khl_uses_fixture_images(self):
        game = {'event': {'id': 1, 'type_id': 24, 'start_at': 1793635200000,
                          'team_a': {'id': 40, 'name': 'Ak Bars', 'image': 'https://example.com/ak.png'},
                          'team_b': {'id': 44, 'name': 'SKA', 'image': 'https://example.com/ska.png'}}}
        past = {'event': {'id': 2, 'type_id': 24, 'start_at': 1793548800000, 'score': '3:2',
                          'team_a': {'id': 40}, 'team_b': {'id': 44}}}
        today = projections.datetime.now(ZoneInfo('Asia/Seoul')).date()
        season = f'{today.year}/{today.year + 1}' if today.month >= 7 else f'{today.year - 1}/{today.year}'
        table = [{'season': season, 'stages': [{'type': 'regular', 'regular': [
            {'id': 40, 'w': '3', 'otw': '1', 'sow': '0', 'l': '2', 'otl': '1', 'sol': '0'},
            {'id': 44, 'w': '2', 'otw': '0', 'sow': '0', 'l': '3', 'otl': '0', 'sol': '0'}]}]}]
        responses = [{'events': [game]}, {'events': [past]}, table, {'event': {}}, {'team': {}}, {'team': {}}]
        with patch.object(projections, 'fetch_json', side_effect=responses):
            row = projections.scrape_khl()[0]
        logos = row['prediction']['logos']
        self.assertEqual(logos, {'home': 'https://example.com/ak.png', 'away': 'https://example.com/ska.png'})
        teams = row['event']['competitions'][0]['competitors']
        self.assertEqual([team['team']['logo'] for team in teams], [logos['home'], logos['away']])
        self.assertEqual(row['prediction']['recentForm'], {'home': ['W'], 'away': ['L']})
        self.assertEqual(row['prediction']['records']['home']['record'], '4-3')

    def test_nhl_uses_scoreboard_team_logos(self):
        def team(side, code, logo):
            return {'homeAway': side, 'team': {'displayName': f'{code} Club', 'abbreviation': code, 'logo': logo}}
        event = {'id': '1', 'date': '2026-11-04T00:00:00Z', 'competitions': [{'competitors': [
            team('home', 'HOM', 'https://example.com/home.png'),
            team('away', 'AWY', 'https://example.com/away.png')]}]}
        page = ''.join(f'<span id="{section}">' + ''.join(
            f'<a href="/players/news/{i}">{section} {i}</a>' for i in range(count)) + '</span>'
            for section, count in [('forwards', 3), ('defense', 2), ('goalies', 1)])
        with patch.object(projections, 'fetch_json', return_value={'events': [event]}), patch.object(projections, 'fetch_text', return_value=page):
            row = projections.scrape_nhl_dailyfaceoff()[0]
        self.assertEqual(row['logos'], {'home': 'https://example.com/home.png', 'away': 'https://example.com/away.png'})

    def test_kovo_uses_official_emblems(self):
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 11, 2, 12, tzinfo=ZoneInfo('Asia/Seoul'))
        page = '<div>2026년 11월 3일 19:00</div><a href="/matches/123">GS칼텍스 vs 한국도로공사</a>'
        with patch.object(projections, 'datetime', Clock), patch.object(projections, 'fetch_text', side_effect=[page, '<div>두 팀 등록 선수</div>']):
            row = projections.scrape_kovo_bkvolley()[0]
        logos = row['prediction']['logos']
        self.assertEqual(logos, {'home': 'https://cdn.kovo.co.kr/emblems/kixx.svg',
                                 'away': 'https://cdn.kovo.co.kr/emblems/hipass.svg'})
        teams = row['event']['competitions'][0]['competitors']
        self.assertEqual([team['team']['logo'] for team in teams], [logos['home'], logos['away']])


if __name__ == '__main__':
    main()
