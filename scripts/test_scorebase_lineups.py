import base64
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from scorebase_lineups import parse_detail, board_rows, board_leagues, records_from_page, html_rosters, KST


class ScorebaseLineupTests(unittest.TestCase):
    def test_only_complete_lineups_within_twelve_hours(self):
        now = datetime(2026, 11, 8, 12, tzinfo=KST)
        def page(hours, away_count=11):
            event = {'@type': 'SportsEvent', 'startDate': (now + timedelta(hours=hours)).astimezone(timezone.utc).isoformat(),
                     'homeTeam': {'name': '홈'}, 'awayTeam': {'name': '원정'}, 'organizer': {'name': '테스트 리그'}}
            lineup = {'h': {'pl': [[0, 0, 0, f'홈 {i}'] for i in range(11)]},
                      'a': {'pl': [[0, 0, 0, f'원정 {i}'] for i in range(away_count)]}}
            data = base64.urlsafe_b64encode(json.dumps(lineup).encode()).decode().rstrip('=')
            return f'<script type="application/ld+json">{json.dumps(event)}</script><a href="/lineup?d={data}">명단</a>확정 라인업'
        records = ({'home': ['W'] * 5, 'away': ['L'] * 5},
                   {'home': {'record': '3-1-1', 'sideRecord': '2-1-0'},
                    'away': {'record': '1-1-3', 'sideRecord': '0-1-2'}})
        with patch('scorebase_lineups.records_from_page', return_value=records):
            self.assertEqual(len(parse_detail(page(1), '/live/TEST/1', '축구', ('홈', '원정'), now)['teams'][0]['players']), 11)
            self.assertEqual(parse_detail(page(3), '/live/TEST/1', '축구', ('홈', '원정'), now)['teams'][0]['status'], 'predicted')
            self.assertIsNone(parse_detail(page(13), '/live/TEST/1', '축구', ('홈', '원정'), now))
            self.assertIsNone(parse_detail(page(1, 10), '/live/TEST/1', '축구', ('홈', '원정'), now))

    def test_record_shape_is_not_guessed(self):
        self.assertIsNone(records_from_page('<html>최근 5경기</html>'))

    def test_venue_record_must_fit_season_record(self):
        def chunk(home, away):
            parts = ['5승 2무 5패', '리그성적', '4승 2무 6패',
                     '홈 · 원정 강도 (홈 / 원정)', home, '기록', away] + ['W'] * 5 + ['L'] * 5
            return '<script>self.__next_f.push([1,' + json.dumps('0:' + json.dumps({'children': parts}, ensure_ascii=False)) + '])</script>'
        page = chunk('14승 8무 6패', '2승 0무 4패') + chunk('2승 2무 2패', '2승 0무 4패')
        self.assertEqual(records_from_page(page)[1]['home']['sideRecord'], '2-2-2')

    def test_board_does_not_treat_far_schedule_as_lineup(self):
        now = datetime(2026, 11, 8, 12, tzinfo=KST)
        row = '<div class="sb-row"><span class="sb-st-time">19:00</span><a href="/live/TEST/1"><span class="sb-team-home">홈</span><span class="sb-team-away">원정</span></a>'
        self.assertEqual(len(board_rows(row, now.date(), now)), 1)
        self.assertEqual(board_rows(row, now.date() + timedelta(days=1), now), [])

    def test_all_sidebar_leagues_are_kept_without_match_lineups(self):
        page = ('<aside aria-label="축구 리그 목록">'
                '<a href="/scores/UCL"><span class="truncate">UEFA 챔피언스리그</span><span>0</span></a>'
                '<a href="/scores/EPL"><span class="truncate">프리미어리그</span><span>3</span></a>'
                '</aside>')
        self.assertEqual(board_leagues(page), [{'id': 'ucl', 'name': 'UEFA 챔피언스리그'},
                                               {'id': 'epl', 'name': '프리미어리그'}])

    def test_published_basketball_and_volleyball_rosters_without_encoded_lineup(self):
        now = datetime(2026, 11, 10, 8, tzinfo=KST)
        event = {'@type': 'SportsEvent', 'startDate': (now + timedelta(hours=2)).astimezone(timezone.utc).isoformat(),
                 'homeTeam': {'name': '홈'}, 'awayTeam': {'name': '원정'}, 'organizer': {'name': '테스트 리그'}}
        schema = f'<script type="application/ld+json">{json.dumps(event)}</script>'
        for sport, count, wrapper in [('농구', 5, '<section><h2>예상 선발 라인업</h2>{}</section>'),
                                      ('배구', 7, '<div data-live-sec="lineup"><div>예상 선발 라인업</div>{}</div>')]:
            grid = '<div class="grid gap-5 sm:grid-cols-2">' + ''.join(
                '<div class="min-w-0">' + ''.join(f'<a href="/players/{side}{number}">{side} 선수 {number}</a>'
                                                 for number in range(count)) + '</div>' for side in ('홈', '원정')) + '</div>'
            page = schema + wrapper.format(grid)
            self.assertEqual([len(team) for team in html_rosters(page)], [count, count])
            match = parse_detail(page, '/live/TEST/1', sport, ('홈', '원정'), now)
            self.assertEqual([len(team['players']) for team in match['teams']], [count, count])
            self.assertEqual(match['teams'][0]['status'], 'predicted')
            self.assertEqual(match['recentForm'], {})

    def test_incomplete_hockey_roster_is_not_published(self):
        now = datetime(2026, 11, 10, 8, tzinfo=KST)
        event = {'@type': 'SportsEvent', 'startDate': (now + timedelta(hours=2)).astimezone(timezone.utc).isoformat(),
                 'homeTeam': {'name': '홈'}, 'awayTeam': {'name': '원정'}}
        page = f'<script type="application/ld+json">{json.dumps(event)}</script>'
        page += '<section><h2>예상 출전 명단</h2><div class="grid sm:grid-cols-2">' + ''.join(
            '<div>' + ''.join(f'<a href="/players/{side}{number}">{side} 선수 {number}</a>'
                                for number in range(17)) + '</div>' for side in ('홈', '원정')) + '</div></section>'
        self.assertEqual([len(team) for team in html_rosters(page)], [17, 17])
        self.assertIsNone(parse_detail(page, '/live/NHL/1', '하키', ('홈', '원정'), now))


if __name__ == '__main__':
    unittest.main()
