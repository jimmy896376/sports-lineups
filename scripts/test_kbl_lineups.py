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
        with patch.object(module, 'datetime', Clock), patch.object(module, 'fetch_text', side_effect=[schedule, '']), patch.object(module, 'kbl_projected_lineups', return_value={}), patch.object(module, 'kbl_recent_and_records', return_value=comparison):
            row = module.scrape_kbl_statgg()[0]
        self.assertEqual(row['prediction']['logos']['home'], 'https://www.kbl.or.kr/assets/img/ico/logo/ic-sk.svg')
        self.assertEqual(row['prediction']['logos']['away'], 'https://www.kbl.or.kr/assets/img/ico/logo/ic-pega.svg')
        self.assertEqual(row['event']['competitions'][0]['competitors'][0]['team']['logo'], row['prediction']['logos']['home'])


if __name__ == '__main__':
    main()
