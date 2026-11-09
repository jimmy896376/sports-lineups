import importlib.util
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo
from unittest import TestCase, main

spec = importlib.util.spec_from_file_location('projections_kbl', Path(__file__).with_name('update-projections.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class KBLProjectedLineups(TestCase):
    def test_wkbl_includes_five_days_only(self):
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 11, 4, 6, tzinfo=ZoneInfo('Asia/Seoul'))
        games = [
            {'date': f'2026-11-{day:02}T10:00:00Z', 'home': 'KB스타즈', 'away': '우리은행'}
            for day in (6, 7, 9)
        ]
        with patch.object(module, 'datetime', Clock), patch.object(module, 'fetch_text', return_value=''), patch.object(module, 'parse_wkbl_schedule', return_value=games):
            rows = module.scrape_wkbl_official()
        self.assertEqual([row['event']['date'] for row in rows], ['2026-11-06T10:00:00Z', '2026-11-07T10:00:00Z'])

    def test_schedule_excludes_easl_and_includes_day_after_tomorrow(self):
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 11, 4, 6, tzinfo=ZoneInfo('Asia/Seoul'))
        schedule = ('<span class="stat-num tabular-nums">2026.11.05</span>'
                    '<a href="/ko/kbl/matches/EASL">예정<span class="stat-num text-fg-muted">19:10</span>'
                    '<span class="break-keep text-lg">부산 KCC</span>'
                    '<span class="break-keep text-lg">마카오 호우촌</span></a>'
                    '<span class="stat-num tabular-nums">2026.11.06</span>'
                    '<a href="/ko/kbl/matches/KBL">예정<span class="stat-num text-fg-muted">19:00</span>'
                    '<span class="break-keep text-lg">서울 SK</span>'
                    '<span class="break-keep text-lg">수원 KT</span></a>')
        comparison = {'recentForm': {}, 'records': {'home': [{'summary': '6-3'}]}}
        venue = {'서울 SK': {'record': '6-3', 'home': '5-2', 'away': '1-1'},
                 '수원 KT': {'record': '6-5', 'home': '3-2', 'away': '3-3'}}
        with patch.object(module, 'datetime', Clock), patch.object(module, 'fetch_text', side_effect=[schedule, '']), patch.object(module, 'kbl_projected_lineups', return_value={}), patch.object(module, 'kbl_recent_and_records', return_value=comparison), patch.object(module, 'scorebase_venue_records', return_value=venue):
            rows = module.scrape_kbl_statgg()
        self.assertEqual([row['event']['id'] for row in rows], ['KBL'])
        self.assertEqual(rows[0]['prediction']['records']['home']['sideRecord'], '5-2')
        self.assertEqual(rows[0]['prediction']['records']['away']['sideRecord'], '3-3')

    def test_current_preview_table_keeps_home_and_away(self):
        def team(name, player):
            row = '<tr><td><a><span class="flex items-center gap-1.5 whitespace-nowrap font-medium">' + player + '</span></a></td>' + '<td>1</td>' * 5 + '<td>35.3</td><td>80.0%</td></tr>'
            return '<h3 data-no-section-index="true" class="font-semibold">' + name + '</h3><table><thead><tr>' + ''.join('<th>' + col + '</th>' for col in ('선수', '경기', '득점', '리바운드', '어시스트', 'TS%', '출장', '야투%')) + '</tr></thead><tbody class="stats">' + row + '</tbody></table>'
        detail = team('서울 SK', '자밀 워니') + team('수원 KT', '허훈')
        lineups = module.kbl_projected_lineups(detail, ['서울 SK', '수원 KT'])
        self.assertEqual(lineups['home'][0]['name'], '자밀 워니')
        self.assertEqual(lineups['away'][0]['name'], '허훈')
        self.assertEqual(module.kbl_projected_lineups(team('다른 팀', '오류 선수'), ['서울 SK', '수원 KT']), {})

    def test_recent_and_record_keep_home_away_sides(self):
        recent = '<div data-compare-row="recent"><div class="x col-start-1 row-start-1 y"><span aria-hidden="true">W</span><span aria-hidden="true">L</span></div><div class="x col-start-3 row-start-1 y"><span aria-hidden="true">L</span></div></div>'
        record = '<div data-compare-row="record"><div class="x col-start-1 row-start-1 y">2-1</div><div class="x col-start-3 row-start-1 y">3-5</div></div>'
        parsed = module.kbl_recent_and_records(recent + record)
        self.assertEqual(parsed['recentForm'], {'home': ['W', 'L'], 'away': ['L']})
        self.assertEqual(parsed['records']['home'][0]['summary'], '2-1')
        self.assertEqual(parsed['records']['away'][0]['summary'], '3-5')

    def test_schedule_uses_official_team_logos(self):
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 11, 4, 6, tzinfo=ZoneInfo('Asia/Seoul'))
        schedule = ('<span class="stat-num tabular-nums">2026.11.04</span>'
                    '<a href="/ko/kbl/matches/S49G01N53">예정'
                    '<span class="stat-num text-fg-muted">19:00</span>'
                    '<span class="break-keep text-lg">서울 SK</span>'
                    '<span class="break-keep text-lg">대구 한국가스공사</span></a>')
        comparison = {'recentForm': {}, 'records': {}}
        with patch.object(module, 'datetime', Clock), patch.object(module, 'fetch_text', side_effect=[schedule, '']), patch.object(module, 'kbl_projected_lineups', return_value={}), patch.object(module, 'kbl_recent_and_records', return_value=comparison), patch.object(module, 'scorebase_venue_records', return_value={}):
            row = module.scrape_kbl_statgg()[0]
        self.assertEqual(row['prediction']['logos']['home'], 'https://www.kbl.or.kr/assets/img/ico/logo/ic-sk.svg')
        self.assertEqual(row['prediction']['logos']['away'], 'https://www.kbl.or.kr/assets/img/ico/logo/ic-pega.svg')
        self.assertEqual(row['event']['competitions'][0]['competitors'][0]['team']['logo'], row['prediction']['logos']['home'])

    def test_scorebase_team_stats_only_accept_consistent_venue_totals(self):
        page = ('<h2>팀 통계</h2><table><tr><th>팀</th><th>승-패</th><th>홈</th><th>원정</th></tr>'
                '<tr><td><a>1서울 SK</a></td><td>6-3</td><td>5-2</td><td>1-1</td></tr>'
                '<tr><td><a>2수원 KT</a></td><td>6-4</td><td>3-2</td><td>2-2</td></tr></table>')
        self.assertEqual(module.scorebase_venue_records('KBL', page),
                         {'서울 SK': {'record': '6-3', 'home': '5-2', 'away': '1-1'}})

    def test_khl_venue_record_requires_matching_official_season_total(self):
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 11, 10, 6, tzinfo=ZoneInfo('Asia/Seoul'))
        teams = [{'id': 72, 'name': 'CSKA'}, {'id': 70, 'name': 'Sibir'}]
        game = {'id': 123, 'type_id': 18, 'start_at': int(datetime(2026, 11, 10, 9, tzinfo=ZoneInfo('Asia/Seoul')).timestamp() * 1000),
                'team_a': teams[0], 'team_b': teams[1]}
        table = [{'season': '2026/2027', 'stages': [{'type': 'regular', 'regular': [
            {'id': 72, 'w': 3, 'l': 1}, {'id': 70, 'w': 1, 'l': 3}]}]}]
        def fetch(url):
            if 'events_v2' in url:
                return [game] if 'order_direction=asc' in url else []
            if 'tables_v2' in url:
                return table
            return {'team': {'players': []}}
        records = {'CSKA 모스크바': {'record': '3-1', 'home': '2-0', 'away': '1-1'},
                   '시비르 노보시비르스크': {'record': '2-2', 'home': '1-1', 'away': '1-1'}}
        with patch.object(module, 'datetime', Clock), patch.object(module, 'fetch_json', side_effect=fetch), patch.object(module, 'scorebase_venue_records', return_value=records):
            result = module.scrape_khl()[0]['prediction']['records']
        self.assertEqual(result['home'], {'record': '3-1', 'sideRecord': '2-0'})
        self.assertEqual(result['away'], {'record': '1-3'})


if __name__ == '__main__':
    main()
