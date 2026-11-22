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
        rows = module.parse_kbl_results([
            {'gmkey': 'S49G01N65', 'gameDate': '20261112', 'gameTime': '19:00', 'isEnded': 'Y', 'scoreH': '87', 'scoreA': '88', 'tnameH': '대구 한국가스공사', 'tnameA': '고양 소노'},
            {'gmkey': 'wrong-date', 'gameDate': '20261113', 'gameTime': '19:00', 'isEnded': 'Y', 'scoreH': '87', 'scoreA': '88', 'tnameH': 'A', 'tnameA': 'B'},
            {'gmkey': 'not-final', 'gameDate': '20261112', 'gameTime': '19:00', 'isEnded': 'N', 'scoreH': '0', 'scoreA': '0', 'tnameH': 'A', 'tnameA': 'B'},
        ], datetime(2026, 11, 9, tzinfo=timezone.utc), now, 'checked')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['eventId'], 'S49G01N65')
        self.assertEqual(rows[0]['kickoff'], datetime(2026, 11, 12, 10, tzinfo=timezone.utc).isoformat())
        self.assertEqual(rows[0]['winner'], 'away')


    def test_fotmob_final_result_uses_fixture_id(self):
        start = datetime(2026, 11, 20, tzinfo=timezone.utc)
        now = datetime(2026, 11, 23, tzinfo=timezone.utc)
        payload = {'fixtures': {'allMatches': [
            {'id': 6503838, 'status': {'finished': True, 'utcTime': '2026-11-21T05:00:00Z', 'scoreStr': '0 - 1'},
             'home': {'name': 'Jeonbuk Hyundai Motors FC'}, 'away': {'name': 'FC Seoul'}},
            {'id': 6503954, 'status': {'finished': True, 'utcTime': '2026-11-21T05:00:00Z', 'scoreStr': '1 - 1'},
             'home': {'name': 'Pohang Steelers'}, 'away': {'name': 'FC Anyang'}},
            {'id': 123, 'status': {'finished': True, 'cancelled': True, 'utcTime': '2026-11-21T05:00:00Z', 'scoreStr': '0 - 0'},
             'home': {'name': 'A'}, 'away': {'name': 'B'}},
            {'id': 6503839, 'status': {'finished': False, 'utcTime': '2026-11-21T07:30:00Z', 'scoreStr': '0 - 0'},
             'home': {'name': 'Gangwon FC', 'score': 0}, 'away': {'name': 'Daejeon Hana Citizen', 'score': 0}},
        ]}}
        rows = module.parse_fotmob_results(payload, 'kleague1', start, now, 'checked')
        self.assertEqual([row['eventId'] for row in rows], ['6503838', '6503954'])
        self.assertEqual(rows[0]['winner'], 'away')
        self.assertEqual((rows[1]['homeScore'], rows[1]['awayScore'], rows[1]['winner']), (1, 1, 'draw'))

    def test_wkbl_final_uses_official_result_page(self):
        now = datetime(2026, 11, 23, tzinfo=timezone.utc)
        page = '<li><a class="link_detail" href="/m/game/result.asp?game_no=19"><span class="date">11.22</span><strong class="team_name">KB스타즈</strong><em>70</em><strong class="team_name">삼성생명</strong><em>44</em></a></li>'
        detail = '<strong class="txt_time">2026.11.22(일)&nbsp;16:00&nbsp;청주체육관</strong><div class="score_block"><em>70</em></div><div class="score_block"><em>44</em></div>'
        original = module.fetch_text
        module.fetch_text = lambda url: detail
        try:
            rows = module.parse_wkbl_schedule(page, '202611', datetime(2026, 11, 19, tzinfo=timezone.utc), now, 'checked')
        finally:
            module.fetch_text = original
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['eventId'], 'wkbl-2026-11-22-KB스타즈-삼성생명')
        self.assertEqual(rows[0]['homeScore'], 70)


if __name__ == '__main__':
    main()
