import importlib.util
from datetime import datetime
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch
from zoneinfo import ZoneInfo

spec = importlib.util.spec_from_file_location('projections', Path(__file__).with_name('update-projections.py'))
projections = importlib.util.module_from_spec(spec)
spec.loader.exec_module(projections)


class TeamLogos(TestCase):
    def test_khl_uses_fixture_images(self):
        game = {'event': {'id': 1, 'type_id': 24, 'start_at': 1793635200000,
                          'team_a': {'id': 40, 'name': 'Ak Bars', 'image': 'https://example.com/ak.png'},
                          'team_b': {'id': 44, 'name': 'SKA', 'image': 'https://example.com/ska.png'}}}
        with patch.object(projections, 'fetch_json', side_effect=[{'events': [game]}, {'events': []}, {'team': {}}, {'team': {}}]):
            row = projections.scrape_khl()[0]
        logos = row['prediction']['logos']
        self.assertEqual(logos, {'home': 'https://example.com/ak.png', 'away': 'https://example.com/ska.png'})
        teams = row['event']['competitions'][0]['competitors']
        self.assertEqual([team['team']['logo'] for team in teams], [logos['home'], logos['away']])

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
