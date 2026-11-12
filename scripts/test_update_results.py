import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from unittest import TestCase, main

spec = importlib.util.spec_from_file_location('update_results', Path(__file__).with_name('update-results.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class KBLResults(TestCase):
    def test_uses_official_id_date_and_final_score(self):
        now = datetime(2026, 11, 12, 15, tzinfo=timezone.utc)
        rows = module.parse_kbl_results({'object': [
            {'gmkey': 'S49G01N65', 'gameDate': '20261112', 'gameTime': '19:00', 'isEnded': 'Y', 'scoreH': '87', 'scoreA': '88', 'tnameH': '대구 한국가스공사', 'tnameA': '고양 소노'},
            {'gmkey': 'wrong-date', 'gameDate': '20261113', 'gameTime': '19:00', 'isEnded': 'Y', 'scoreH': '87', 'scoreA': '88', 'tnameH': 'A', 'tnameA': 'B'},
            {'gmkey': 'not-final', 'gameDate': '20261112', 'gameTime': '19:00', 'isEnded': 'N', 'scoreH': '0', 'scoreA': '0', 'tnameH': 'A', 'tnameA': 'B'},
        ]}, datetime(2026, 11, 9, tzinfo=timezone.utc), now, 'checked')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['eventId'], 'S49G01N65')
        self.assertEqual(rows[0]['kickoff'], datetime(2026, 11, 12, 10, tzinfo=timezone.utc).isoformat())
        self.assertEqual(rows[0]['winner'], 'away')


if __name__ == '__main__':
    main()
