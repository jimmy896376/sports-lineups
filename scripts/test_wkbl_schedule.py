import importlib.util
from pathlib import Path
from datetime import datetime
from unittest import TestCase, main
from unittest.mock import patch
from zoneinfo import ZoneInfo

spec = importlib.util.spec_from_file_location('projections_wkbl', Path(__file__).with_name('update-projections.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WKBLOfficialSchedule(TestCase):
    def test_missing_scraped_side_keeps_same_game_forecast(self):
        def game(event_id, away, home_players, away_players):
            return {'event': {'id': event_id}, 'prediction': {
                'names': {'home': '신한은행', 'away': away},
                'lineups': {'home': home_players, 'away': away_players}}}
        old = game('match-1', '우리은행', [{'name': '홈'}], [{'name': '원정'}])
        current = game('match-1', '우리은행', [], [{'name': '새 원정'}])
        wrong_team = game('match-1', 'KB스타즈', [], [])
        module.restore_missing_lineups([current, wrong_team], [old])
        self.assertEqual(current['prediction']['lineups']['home'], [{'name': '홈'}])
        self.assertEqual(current['prediction']['lineups']['away'], [{'name': '새 원정'}])
        self.assertEqual(wrong_team['prediction']['lineups']['home'], [])

    def test_projected_players_use_current_roster_and_verified_minutes(self):
        def table(index, kind, players, minutes):
            rows = ''.join('<tr><td><a><span class="font-medium">' + name +
                           '</span><span class="text-3xs">' + position +
                           '</span></a></td><td>1</td><td>' + str(value) + '</td></tr>'
                           for (name, position), value in zip(players, minutes))
            return (f'<div role="tabpanel" id="wkbl-pregame-{index}-{kind}-panel">'
                    '<table><thead><tr><th>선수</th><th>경기</th><th>출장</th></tr></thead>'
                    f'<tbody>{rows}</tbody></table></div>')
        home = [(f'홈{i}', 'G' if i < 3 else 'F') for i in range(6)]
        away = [(f'원정{i}', 'G' if i < 3 else 'F') for i in range(6)]
        detail = '<h1>신한은행 vs 우리은행</h1>' + ''.join(
            table(index, 'season', players, [0] * 6).replace('<th>출장</th>', '') +
            table(index, 'vs', players + [('이적 선수', 'F')], [10, 20, 30, 40, 50, 60, 99])
            for index, players in enumerate((home, away)))
        result = module.wkbl_projected_lineups(detail, {'home': '신한은행', 'away': '우리은행'})
        self.assertEqual([row['name'] for row in result['home']], ['홈5', '홈4', '홈3', '홈2', '홈1'])
        self.assertEqual(len(result['away']), 5)
        self.assertNotIn('이적 선수', [row['name'] for row in result['away']])
        with self.assertRaisesRegex(ValueError, 'do not match'):
            module.wkbl_projected_lineups(detail, {'home': 'KB스타즈', 'away': '우리은행'})

    def test_schedule_includes_official_team_logos(self):
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 11, 4, 6, tzinfo=ZoneInfo('Asia/Seoul'))
        page = ('<ul class="list_schedule"><li><span class="date">11.04</span>'
                '<strong class="team_name">신한은행</strong><strong class="team_name">우리은행</strong>'
                '<div class="place_block"><span>인천<br />19:00</span></div></li></ul>')
        with patch.object(module, 'datetime', Clock), patch.object(module, 'fetch_text', return_value=page):
            row = module.scrape_wkbl_official()[0]
        self.assertEqual(row['prediction']['logos']['home'], 'https://www.wkbl.or.kr/static/images/team/teamlogo_07.png')
        self.assertEqual(row['prediction']['logos']['away'], 'https://www.wkbl.or.kr/static/images/team/teamlogo_05.png')

    def test_recent_five_can_cross_seasons_without_changing_season_record(self):
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 11, 4, 6, tzinfo=ZoneInfo('Asia/Seoul'))
        def game(day, scores=None):
            row = {'date': day + 'T10:00:00Z', 'home': '신한은행', 'away': '우리은행'}
            if scores:
                row['scores'] = scores
            return row
        def schedule(page, year, month):
            if (year, month) == (2026, 10):
                return [game('2026-10-28', [70, 60]), game('2026-10-29', [60, 70]), game('2026-10-30', [70, 60])]
            return [game('2026-11-04')]
        older = [dict(game('2026-03-01', [70, 60]), id='old-1'), dict(game('2026-03-02', [60, 70]), id='old-2')]
        with patch.object(module, 'datetime', Clock), patch.object(module, 'fetch_text', return_value=''), patch.object(module, 'parse_wkbl_schedule', side_effect=schedule), patch.object(module, 'parse_wkbl_datalab_results', return_value=older):
            result = module.scrape_wkbl_official()[0]['prediction']
        self.assertEqual(result['recentForm']['home'], ['W', 'L', 'W', 'L', 'W'])
        self.assertEqual(result['records']['home'], {'record': '2-1', 'sideRecord': '2-1'})

    def test_datalab_results_extract_scores_and_home_side(self):
        page = ('<li class="game-item on" data-id="04601083"><strong class="game-date">03.28(토)</strong>'
                '<dl class="home-team"><dt class="home-team-name"><img src="logo">우리은행</dt>'
                '<dd class=" home-team-score">61</dd></dl><dl class="away-team">'
                '<dt class="away-team-name">신한은행</dt><dd class="win away-team-score">63</dd></dl></li>')
        self.assertEqual(module.parse_wkbl_datalab_results(page, 2026), [
            {'id': '04601083', 'date': '2026-03-28T00:00:00Z', 'home': '우리은행',
             'away': '신한은행', 'scores': [61, 63]}])

    def test_official_monthly_schedule_keeps_home_side_and_kst_time(self):
        page = '<ul class="list_schedule"><li><span class="date">11.01</span>' \
               '<strong class="team_name">KB스타즈</strong><strong class="team_name">BNK 썸</strong>' \
               '<div class="place_block"><span>청주<br />16:00</span></div></li></ul>'
        rows = module.parse_wkbl_schedule(page, 2026, 11)
        self.assertEqual(rows, [{'date': '2026-11-01T07:00:00Z', 'home': 'KB스타즈', 'away': 'BNK 썸'}])
        self.assertEqual(module.parse_wkbl_schedule(page, 2026, 10), [])

    def test_completed_regular_season_score_is_available_for_records(self):
        page = ('<ul class="list_schedule"><li><a href="/m/game/result.asp?game_type=01">'
                '<span class="date">11.01</span><strong class="team_name">KB스타즈</strong><em>53</em>'
                '<strong class="team_name">BNK 썸</strong><em>82</em></a></li></ul>')
        self.assertEqual(module.parse_wkbl_schedule(page, 2026, 11)[0]['scores'], [53, 82])

    def test_missing_list_fails_instead_of_reporting_no_games(self):
        with self.assertRaises(ValueError):
            module.parse_wkbl_schedule('<html></html>', 2026, 11)


if __name__ == '__main__':
    main()
