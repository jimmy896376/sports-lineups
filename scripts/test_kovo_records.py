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

    def test_retain_started_lineups_deduplicates_by_event_id_and_names(self):
        now = datetime(2026, 11, 26, 19, 0, tzinfo=timezone.utc)
        current = [{
            'league': 'uecl', 'kickoff': '2026-11-26T17:45:00Z', 'espnEventId': '401915814',
            'teams': {'home': 'BHA', 'away': 'UCRA'},
            'names': {'home': 'Brighton', 'away': 'Universitatea Craiova'},
            'lineups': {'home': [{'name': 'A'}], 'away': [{'name': 'B'}]},
        }]
        previous = [{
            'league': 'uecl', 'kickoff': '2026-11-26T17:45:00Z', 'espnEventId': '401915814',
            'teams': {'home': 'BHA', 'away': 'CRA'},
            'names': {'home': 'Brighton', 'away': 'Universitatea Craiova'},
            'lineups': {'home': [{'name': 'A'}], 'away': [{'name': 'B'}]},
        }]
        MODULE.retain_started_lineups(current, previous, now=now)
        self.assertEqual(len(current), 1)

    def test_share_known_team_logos_fills_cross_competition_missing_logo(self):
        payload = {
            'items': [{
                'league': 'acle',
                'names': {'home': 'FC Tokyo', 'away': 'Daejeon Hana Citizen FC'},
                'logos': {'home': 'https://a.espncdn.com/i/teamlogos/soccer/500/17689.png', 'away': ''},
            }],
            'domestic': {
                'kleague1': [{
                    'prediction': {
                        'league': 'kleague1',
                        'names': {'home': 'FC Seoul', 'away': 'Daejeon Hana Citizen'},
                        'logos': {'home': 'https://example.com/seoul.png', 'away': 'https://images.fotmob.com/133900.png'},
                    }
                }]
            },
        }
        MODULE.share_known_team_logos(payload)
        self.assertEqual(payload['items'][0]['logos']['away'], 'https://images.fotmob.com/133900.png')


if __name__ == '__main__':
    unittest.main()
