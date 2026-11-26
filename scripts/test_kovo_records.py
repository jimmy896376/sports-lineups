import importlib.util
import pathlib
import unittest
from datetime import datetime, timezone

SPEC = importlib.util.spec_from_file_location(
    'update_projections',
    pathlib.Path(__file__).resolve().parent / 'update-projections.py',
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class KovoRecordsTests(unittest.TestCase):
    def test_kovo_records_before_uses_current_season_oldest_first(self):
        games = [
            {'kickoff': datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc), 'home': '인천 대한항공 점보스', 'away': '현대캐피탈', 'home_won': True},
            {'kickoff': datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc), 'home': '인천 대한항공 점보스', 'away': '삼성화재', 'home_won': False},
            {'kickoff': datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc), 'home': '한국전력', 'away': '인천 대한항공 점보스', 'home_won': True},
            {'kickoff': datetime(2026, 11, 8, 10, 0, tzinfo=timezone.utc), 'home': '인천 대한항공 점보스', 'away': '우리카드', 'home_won': False},
            {'kickoff': datetime(2026, 11, 15, 10, 0, tzinfo=timezone.utc), 'home': 'KB손해보험', 'away': '인천 대한항공 점보스', 'home_won': False},
            {'kickoff': datetime(2026, 11, 22, 10, 0, tzinfo=timezone.utc), 'home': 'OK저축은행', 'away': '인천 대한항공 점보스', 'home_won': False},
            # Future game after kickoff must be ignored
            {'kickoff': datetime(2026, 11, 28, 10, 0, tzinfo=timezone.utc), 'home': '인천 대한항공 점보스', 'away': '현대캐피탈', 'home_won': True},
        ]
        kickoff = datetime(2026, 11, 27, 10, 0, tzinfo=timezone.utc)
        recent_form, records = MODULE.kovo_records_before(games, '대한항공', '현대캐피탈', kickoff)
        self.assertEqual(recent_form['home'], ['L', 'L', 'L', 'W', 'W'])
        self.assertEqual(records['home'], {'record': '3-3', 'sideRecord': '1-2'})
        self.assertEqual(recent_form['away'], ['L'])
        self.assertEqual(records['away'], {'record': '0-1', 'sideRecord': '0-1'})


if __name__ == '__main__':
    unittest.main()
