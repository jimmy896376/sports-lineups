import importlib.util
import json
from datetime import date, datetime
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch
from zoneinfo import ZoneInfo
spec = importlib.util.spec_from_file_location('projections', Path(__file__).with_name('update-projections.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class StartingPitchers(TestCase):
    def test_npb_published_lineups_exclude_relief_pitchers(self):
        raw = json.loads(Path(__file__).with_name('fixtures').joinpath('npb-starters.json').read_text())
        result = m.npb_pitchers(raw, [], '2021039492', date(2026,10,24))
        self.assertEqual(result['home']['name'], '石田　裕太郎')
        self.assertEqual(result['away']['name'], '上沢　直之')
        self.assertEqual(result['home']['status'], 'confirmed')
    def test_npb_announcement_before_batting_order(self):
        row = {'gameId':2021039493,'gameDate':'20261025','homePrePitcherName':'尾形　崇斗','visitorPrePitcherName':'モイネロ'}
        result = m.npb_pitchers([], [row], '2021039493', date(2026,10,25))
        self.assertEqual(result['home']['name'], '尾形　崇斗')
        self.assertEqual(result['away']['name'], 'モイネロ')
        self.assertEqual(result['away']['status'], 'probable')
        self.assertEqual(m.npb_pitchers([], [row], 'other', date(2026,10,25)), {})
        self.assertEqual(m.npb_pitchers([], [row], '2021039493', date(2026,10,24)), {})
    def test_kbo_keeps_announced_pitchers_without_batting_order(self):
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None): return cls(2026,10,24,12,tzinfo=ZoneInfo('Asia/Seoul'))
        game={'LE_ID':1,'SR_ID':0,'SEASON_ID':2026,'G_ID':'game','G_TM':'18:30','HOME_NM':'삼성','AWAY_NM':'KT','HOME_ID':'SS','AWAY_ID':'KT','B_PIT_P_NM':'홈투수','T_PIT_P_NM':'원정투수'}
        def post(url, data, referer):
            if 'GetKboGameList' in url: return {'game':[game] if data['date']=='20261024' else []}
            raise RuntimeError('batting order not available')
        with patch.object(m,'datetime',Clock),patch.object(m,'post_json',side_effect=post):
            rows=m.scrape_kbo_official()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['prediction']['startingPitchers']['home']['name'],'홈투수')
        self.assertEqual(rows[0]['prediction']['startingPitchers']['away']['name'],'원정투수')
        self.assertTrue(rows[0]['prediction']['logos']['home'].endswith('/emblem_SS.png'))
        self.assertTrue(rows[0]['prediction']['logos']['away'].endswith('/emblem_KT.png'))
        self.assertEqual(rows[0]['event']['competitions'][0]['competitors'][0]['team']['logo'],rows[0]['prediction']['logos']['home'])
        self.assertFalse(rows[0]['confirmed'])
    def test_cpbl_review_is_exact_game_and_never_overwrites_live_pitcher(self):
        names={'home':'味全龍','away':'中信兄弟'}
        result=m.reviewed_pitcher_fallback('2026-C-5','2026-10-25T09:05:00Z',names,{'home':{'name':'new official pitcher'}})
        self.assertEqual(result['home']['name'],'new official pitcher')
        self.assertEqual(result['away']['name'],'Nivaldo Rodriguez')
        self.assertEqual(m.reviewed_pitcher_fallback('2026-C-6','2026-10-25T09:05:00Z',names,{}),{})
        self.assertEqual(m.reviewed_pitcher_fallback('2026-C-5','2026-10-26T09:05:00Z',names,{}),{})
    def test_yahoo_backup_uses_team_ids_not_player_order(self):
        page = '"/npb/game/123/top" 2026年10月25日 <li class="bb-gameCard__readMoreItem--home"><a href="/npb/teams/3/schedule"> <li class="bb-gameCard__readMoreItem--away"><a href="/npb/teams/12/schedule"> <section id="strt_pit"><div class="bb-splitsHead--npbTeam12"><div class="bb-splitsPitcherStarting"><a href="/npb/player/2/top">Away pitcher</a> <div class="bb-splitsHead--npbTeam3"><div class="bb-splitsPitcherStarting"><a href="/npb/player/1/top">Home pitcher</a><div class="bb-splits bb-splits--stretch">'
        result=m.yahoo_npb_pitchers(page, '123', date(2026,10,25))
        self.assertEqual(result['home']['name'],'Home pitcher')
        self.assertEqual(result['away']['name'],'Away pitcher')
        self.assertEqual(m.yahoo_npb_pitchers(page, '123', date(2026,10,24)),{})
        self.assertEqual(m.yahoo_npb_pitchers(page, '456', date(2026,10,25)),{})
    def test_cpbl_official_field_mapping(self):
        result=m.announced_pitchers({'HomeFirstMover':'蔣銲','VisitingFirstMover':'羅戈'},{'home':'HomeFirstMover','away':'VisitingFirstMover'},'https://www.cpbl.com.tw/')
        self.assertEqual(result['home']['name'],'蔣銲')
        self.assertEqual(result['away']['name'],'羅戈')
        self.assertEqual(m.announced_pitchers({'HomeFirstMover':'未定'},{'home':'HomeFirstMover'},'source'),{})

if __name__ == '__main__': main()
