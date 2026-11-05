import importlib.util
from pathlib import Path
import unittest
import tempfile
from unittest.mock import MagicMock, patch
import json
spec = importlib.util.spec_from_file_location('resolver', Path(__file__).with_name('resolve-player-names.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

class NameVerification(unittest.TestCase):
    def test_current_feed_names_take_search_priority(self):
        now=r.dt.datetime(2026,11,5,tzinfo=r.dt.timezone.utc)
        state={'players':{}}
        visible={'james justin'}
        current={'name':'James Justin','eventDate':'2026-11-07T00:00:00Z','kind':'lineup'}
        older={'name':'Other Player','eventDate':'2026-11-05T01:00:00Z','kind':'lineup'}
        self.assertLess(r.priority(current,state,now,visible),r.priority(older,state,now,visible))
    def test_kleague_official_roster_requires_team_and_unique_jersey(self):
        rows=[{'name':'Dong-Jun Kim','team':'Jeju SK','league':'kleague1','number':'1'},
              {'name':'Other Player','team':'Jeju SK','league':'kleague1','number':'2'},
              {'name':'Wrong Club','team':'Gwangju FC','league':'kleague1','number':'1'}]
        page=r.Page('<span class="name">김동준<span class="small">제주</span></span><span class="num campton">No.1</span>'
                    '<span class="name">선수 갑<span class="small">제주</span></span><span class="num campton">No.2</span>'
                    '<span class="name">선수 을<span class="small">제주</span></span><span class="num campton">No.2</span>')
        def get(url):
            if 'teamId=K22' in url: raise ValueError('club unavailable')
            return page
        approved=r.kleague_official_names(rows,get)
        self.assertEqual([(x['name'],x['korean']) for x in approved],[('Dong-Jun Kim','김동준')])
        self.assertEqual(approved[0]['sources'][0]['clubCode'],'K04')

    def test_scorebase_nhl_roster_pairs_english_and_korean_in_same_player_card(self):
        rows=[{'name':'Matthew Knies','team':'Columbus Blue Jackets','league':'nhl'},
              {'name':'Unknown Player','team':'Columbus Blue Jackets','league':'nhl'}]
        league=r.Page('<a href="/teams/722">콜럼버스 블루재키츠</a>')
        roster=r.Page('<a href="/players/8482720"><img alt="Matthew Knies">'
                      '<div class="font-semibold text-sm truncate">매튜 나이스</div></a>'
                      '<a href="/players/1?league=NHL"><img alt="Other Person">'
                      '<div class="font-semibold text-sm truncate">다른 선수</div></a>')
        def get(url):
            return league if url.endswith('/leagues/NHL') else roster
        entries=r.scorebase_roster_names(rows,'nhl',get)
        self.assertEqual([(e['name'],e['korean']) for e in entries],[('Matthew Knies','매튜 나이스')])
        self.assertEqual(entries[0]['sources'][0]['playerUrl'],'https://www.scorebase.kr/players/8482720?league=NHL')
        self.assertEqual(r.scorebase_roster_names([{'name':'Matthew Knies','league':'nba'}],'nhl',get),[])

    def test_scorebase_nba_roster_adds_verified_korean_name(self):
        league=r.Page('<a href="/teams/527">샬럿 호네츠</a>')
        roster=r.Page('<a href="/players/123?league=NBA"><img alt="Coby White">'
                      '<div class="font-semibold text-sm">코비 화이트</div></a>')
        def get(url):
            return league if url.endswith('/leagues/NBA') else roster
        entries=r.scorebase_roster_names([{'name':'Coby White','league':'nba','team':'Charlotte Hornets'}],'nba',get)
        self.assertEqual([(e['name'],e['korean'],e['method']) for e in entries],
                         [('Coby White','코비 화이트','scorebase-nba-roster-v1')])

    def test_scorebase_nhl_conflicting_names_stay_unverified(self):
        league=r.Page('<a href="/teams/1">A</a><a href="/teams/2">B</a><a href="/teams/3">C</a>')
        names={'1':'매튜 나이스','2':'매슈 나이스','3':'매튜 나이스'}
        def get(url):
            if url.endswith('/leagues/NHL'):
                return league
            name=names[url.rsplit('/',1)[-1]]
            return r.Page(f'<a href="/players/1?league=NHL"><img alt="Matthew Knies"><div class="font-semibold">{name}</div></a>')
        self.assertEqual(r.scorebase_roster_names([{'name':'Matthew Knies','league':'nhl'}],'nhl',get),[])

    def test_scorebase_khl_profile_matches_reversed_english_and_korean(self):
        league=r.Page('<a href="/teams/612934">토르페도</a>')
        team=r.Page('<a href="/players/abc123?league=KHL">선수</a>')
        player=r.Page('<meta name="description" content="KHL 드미트리 슈가예프(Dmitry Shugayev) 프로필 — 기록"/>')
        def get(url):
            return league if '/leagues/' in url else team if '/teams/' in url else player
        rows=[{'name':'Shugayev Dmitry','league':'khl','team':'Torpedo'},
              {'name':'Other Player','league':'khl','team':'Torpedo'}]
        cache={}
        found,checked=r.scorebase_khl_profiles(rows,cache,get)
        self.assertEqual((checked,[(x['name'],x['korean']) for x in found]),(1,[('Shugayev Dmitry','드미트리 슈가예프')]))
        self.assertEqual(r.scorebase_khl_profiles(rows,cache,get)[1],0)
        self.assertEqual(r.scorebase_khl_profiles([{'name':'Dmitry Shugayev','league':'nhl'}],cache,get),([],0))

    def test_scorebase_khl_profile_failure_does_not_block_next_batch(self):
        league=r.Page('<a href="/teams/1">팀</a>')
        team=r.Page('<a href="/players/first?league=KHL">첫 선수</a>'
                    '<a href="/players/second?league=KHL">둘째 선수</a>')
        player=r.Page('<meta name="description" content="KHL 데니스 코스틴(Denis Kostin) 프로필"/>')
        def get(url):
            if '/leagues/' in url:return league
            if '/teams/' in url:return team
            if '/first?' in url:raise ValueError('temporarily unavailable')
            return player
        found,checked=r.scorebase_khl_profiles([{'name':'Kostin Denis','league':'khl'}],{},get)
        self.assertEqual((checked,found[0]['korean']),(2,'데니스 코스틴'))

    def test_scorebase_khl_variant_requires_same_club(self):
        league=r.Page('<a href="/teams/1">아드미랄</a><a href="/teams/2">아방가르드</a>')
        clubs={'1':r.Page('<title>아드미랄 블라디보스토크 하키 팀</title>'
                          '<a href="/players/one?league=KHL">알렉산드르</a>'),
               '2':r.Page('<title>아방가르드 옴스크 하키 팀</title>'
                          '<a href="/players/two?league=KHL">알렉산드르</a>')}
        profiles={'one':r.Page('<meta name="description" content="KHL 알렉산드르 볼코프(Alexander Volkov) 프로필"/>'),
                  'two':r.Page('<meta name="description" content="KHL 다른 볼코프(Alexander Volkov) 프로필"/>')}
        def get(url):
            if '/leagues/' in url:return league
            if '/teams/' in url:return clubs[url.rsplit('/',1)[-1]]
            return profiles[url.split('/players/')[1].split('?')[0]]
        row={'name':'Volkov Alexander S.','team':'Admiral','league':'khl'}
        found,_=r.scorebase_khl_profiles([row],{},get,{'Admiral':'아드미랄 블라디보스토크'})
        self.assertEqual([(x['korean'],x['method']) for x in found],
                         [('알렉산드르 볼코프','scorebase-khl-roster-variant-v1')])

    row = {'name': 'Moritz Nicolas', 'team': 'Borussia Monchengladbach', 'league': 'bundesliga'}
    def page(self, korean='모리츠 니콜라스', english='Moritz Nicolas', team='Borussia Monchengladbach'):
        return r.Page(f'<title>{korean} - 선수 프로필</title><h1>{korean}</h1><p>{korean} ({english}) {team}</p>')
    def proof(self, url, **kwargs):
        return r.evidence(self.row, url, self.page(**kwargs), '', {'google'}, {})
    def test_asian_names_remain_distinct_for_search(self):
        self.assertEqual(r.normalize('Łukasz Skorupski'),r.normalize('Lukasz Skorupski'))
        self.assertEqual(r.normalize('尾形　崇斗'), '尾形 崇斗')
        self.assertEqual(r.normalize('岳政華'), '岳政華')
        self.assertNotEqual(r.normalize('尾形　崇斗'), r.normalize('石田　裕太郎'))
        self.assertNotEqual(r.normalize('ベイスターズ'), r.normalize('ヘイスターズ'))
        self.assertNotEqual(r.normalize('Александр Овечкин'), r.normalize('Алексей Овечкин'))
        self.assertNotEqual(r.normalize('محمد علي'), r.normalize('محمد حسن'))
    def test_google_result_registers_without_second_source(self):
        calls=[]
        def get(url):
            calls.append(url)
            return self.page()
        approved, report=r.resolve(self.row,get)
        self.assertEqual(approved['method'],'google-search-result-v1')
        self.assertEqual(approved['korean'],'모리츠 니콜라스')
        self.assertEqual(len(calls),1)
        self.assertEqual(report['status'],'verified')
    def test_google_redirect_shell_is_not_a_search_result(self):
        response=MagicMock()
        response.__enter__.return_value=response
        response.headers.get.return_value='text/html'
        response.headers.get_content_charset.return_value='utf-8'
        response.read.return_value='<title>Google Search</title><a href="/retry">여기</a>몇 초 안에 이동하지 않는 경우'.encode()
        opener=MagicMock()
        opener.open.return_value=response
        with patch.object(r.urllib.request,'build_opener',return_value=opener):
            with self.assertRaisesRegex(ValueError,'search-results-unavailable'):
                r.fetch_page('https://www.google.com/search?q=Moritz+Nicolas')
    def test_bing_challenge_and_empty_shell_are_unavailable(self):
        response=MagicMock()
        response.__enter__.return_value=response
        response.headers.get.return_value='text/html'
        response.headers.get_content_charset.return_value='utf-8'
        opener=MagicMock();opener.open.return_value=response
        with patch.object(r.urllib.request,'build_opener',return_value=opener):
            response.read.return_value='<html>마지막 한 단계 계속하려면 아래 과제 해결</html>'.encode()
            with self.assertRaisesRegex(ValueError,'search-challenge'):
                r.fetch_page('https://www.bing.com/search?q=Moritz+Nicolas')
            response.read.return_value=b'<html><title>Bing Search</title></html>'
            with self.assertRaisesRegex(ValueError,'search-results-unavailable'):
                r.fetch_page('https://www.bing.com/search?q=Moritz+Nicolas')
    def test_google_knowledge_panel(self):
        page=r.Page('<div data-attrid="title"><span>모리츠 니콜라스</span></div><p>Moritz Nicolas Borussia Monchengladbach</p>')
        self.assertEqual(r.google_result(self.row,'https://www.google.com/search?q=test',page,{})['korean'],'모리츠 니콜라스')
    def test_daum_sports_profile_requires_original_name_sport_and_club(self):
        html='<a href="?w=profile2&coll=person-main&spId=123">모리츠 니콜라스</a><p>축구선수 Moritz Nicolas</p><a>보루시아 묀헨글라트바흐</a>'
        team={'Borussia Mönchengladbach':'보루시아 묀헨글라트바흐'}
        url='https://search.daum.net/search?w=tot&q=Moritz+Nicolas'
        approved=r.daum_result(self.row,url,r.Page(html),team)
        self.assertEqual(approved['korean'],'모리츠 니콜라스')
        self.assertEqual(approved['method'],r.DAUM_METHOD)
        for invalid in (html.replace('Moritz Nicolas','Other Player'),html.replace('축구선수','배우'),html.replace('보루시아 묀헨글라트바흐','다른 팀')):
            self.assertIsNone(r.daum_result(self.row,url,r.Page(invalid),team))
    def test_daum_custom_profile_card_is_read(self):
        html=('<c-title slot="title" data-href="?w=profile2&amp;DA=PRF&amp;coll=person-main&amp;spId=123">모리츠 니콜라스</c-title>'
              '<p>축구선수 Moritz Nicolas</p><p>소속팀 보루시아 묀헨글라트바흐</p>')
        team={'Borussia Mönchengladbach':'보루시아 묀헨글라트바흐'}
        approved=r.daum_result(self.row,'https://search.daum.net/search?w=tot&q=Moritz+Nicolas',r.Page(html),team)
        self.assertEqual(approved['korean'],'모리츠 니콜라스')
    def test_daum_profile_recovers_when_google_is_blocked(self):
        html='<a href="?w=profile2&coll=person-main&spId=123">모리츠 니콜라스</a><p>축구선수 Moritz Nicolas</p><a>보루시아 묀헨글라트바흐</a>'
        def get(url):
            if 'google.com' in url: raise ValueError('search-challenge')
            if 'daum.net' in url: return r.Page(html)
            self.fail('Bing should not run after exact profile approval')
        approved, report=r.resolve(self.row,get,{'Borussia Mönchengladbach':'보루시아 묀헨글라트바흐'})
        self.assertEqual(approved['korean'],'모리츠 니콜라스')
        self.assertEqual(report['searches']['daum']['status'],'direct-name-result')
    def test_google_wrong_identity_rejected(self):
        for page in (self.page(english='Other Nicolas'), self.page(team='Other FC'), r.Page('<h1>모리츠 니콜라스</h1>')):
            self.assertIsNone(r.google_result(self.row,'https://www.google.com/search?q=test',page,{}))
    def test_google_conflicting_names_rejected(self):
        page=r.Page('<h1>모리츠 니콜라스</h1><h1>모리츠 니콜라스스</h1><p>모리츠 니콜라스 (Moritz Nicolas) 모리츠 니콜라스스 (Moritz Nicolas) Borussia Monchengladbach</p>')
        self.assertIsNone(r.google_result(self.row,'https://www.google.com/search?q=test',page,{}))
    def test_priority_is_upcoming_starters_before_future_and_injury(self):
        now=r.dt.datetime(2026,10,24,tzinfo=r.dt.timezone.utc)
        state={'players':{}}
        rows=[{'name':'A','kind':'lineup','eventDate':'2026-10-28T01:00:00Z'},
              {'name':'B','kind':'injury','eventDate':'2026-10-24T01:00:00Z'},
              {'name':'Z','kind':'lineup','eventDate':'2026-10-24T01:00:00Z'}]
        self.assertEqual([x['name'] for x in sorted(rows,key=lambda x:r.priority(x,state,now))],['Z','B','A'])
    def test_google_h3_result(self):
        page=r.Page('<h3>모리츠 니콜라스</h3><p>모리츠 니콜라스 (Moritz Nicolas) Borussia Monchengladbach</p>')
        self.assertIsNotNone(r.google_result(self.row,'https://www.google.com/search?q=test',page,{}))
    def test_main_persists_multiple_google_approvals_and_deduplicates_accents(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'scripts').mkdir();(root/'dist').mkdir()
            now=r.dt.datetime.now(r.dt.timezone.utc).isoformat()
            records=[{'name':name,'korean':name,'team':'Test FC','kind':'lineup','eventDate':now} for name in ['Adrià Test','Adria Test','Other Person']]
            (root/'scripts/player-name-live-inventory.json').write_text(json.dumps({'at':now,'records':records}))
            (root/'dist/team-ko.json').write_text('{}')
            def resolve(row,**kw):
                return {'name':row['name'],'korean':'테스트','method':'google-search-result-v1','sources':[]},{'searches':{'google':{'status':'direct-name-result'}},'status':'verified'}
            with patch.object(r,'ROOT',root),patch.object(r,'resolve',side_effect=resolve),patch.object(r.time,'sleep'):
                r.main()
            saved=json.loads((root/'scripts/player-name-auto-review.json').read_text())
            self.assertEqual(len(saved['entries']),2)
            self.assertEqual(json.loads((root/'scripts/player-name-run-report.json').read_text())['approved'],2)
    def test_main_continues_after_unreadable_google_result(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'scripts').mkdir();(root/'dist').mkdir()
            now=r.dt.datetime.now(r.dt.timezone.utc).isoformat()
            records=[{'name':name,'korean':name,'team':'Test FC','kind':'lineup','eventDate':now}
                     for name in ['First Player','Second Player']]
            (root/'scripts/player-name-live-inventory.json').write_text(json.dumps({'at':now,'records':records}))
            (root/'dist/team-ko.json').write_text('{}')
            def resolve(row,**kw):
                if row['name']=='First Player':
                    return None,{'searches':{'google':{'status':'no-readable-trusted-results'}},'status':'needs-verification'}
                return {'name':row['name'],'korean':'두 번째 선수','method':'google-search-result-v1','sources':[]},{'searches':{'google':{'status':'direct-name-result'}},'status':'verified'}
            with patch.object(r,'ROOT',root),patch.object(r,'resolve',side_effect=resolve) as search,patch.object(r.time,'sleep'):
                r.main()
            self.assertEqual(search.call_count,2)
            report=json.loads((root/'scripts/player-name-run-report.json').read_text())
            self.assertEqual((report['searchChecked'],report['approved']),(2,1))
            self.assertEqual(report['searchApproved'],1)
            self.assertEqual(report['pendingByLeague'],{'unknown':2})
    def test_main_stops_repeated_google_rate_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'scripts').mkdir();(root/'dist').mkdir()
            now=r.dt.datetime.now(r.dt.timezone.utc).isoformat()
            rows=[{'name':f'Blocked Player {i}','korean':f'Blocked Player {i}',
                   'team':'Test FC','kind':'lineup','eventDate':now} for i in range(5)]
            (root/'scripts/player-name-live-inventory.json').write_text(json.dumps({'at':now,'records':rows}))
            (root/'dist/team-ko.json').write_text('{}')
            report={'searches':{'google':{'status':'unavailable','httpStatus':403}},'status':'needs-verification'}
            with patch.object(r,'ROOT',root),patch.object(r,'resolve',return_value=(None,report)) as search,patch.object(r.time,'sleep'):
                r.main()
            self.assertEqual(search.call_count,3)
            self.assertTrue(json.loads((root/'scripts/player-name-run-report.json').read_text())['searchUnavailable'])
    def test_main_keeps_checking_daum_after_other_engines_stall(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'scripts').mkdir();(root/'dist').mkdir()
            now=r.dt.datetime.now(r.dt.timezone.utc).isoformat()
            rows=[{'name':f'Blocked Player {i}','korean':f'Blocked Player {i}',
                   'team':'Test FC','kind':'lineup','eventDate':now} for i in range(8)]
            (root/'scripts/player-name-live-inventory.json').write_text(json.dumps({'at':now,'records':rows}))
            (root/'dist/team-ko.json').write_text('{}')
            report={'searches':{'google':{'status':'unavailable'},'daum':{'status':'no-readable-trusted-results'},'bing':{'status':'no-readable-trusted-results'}},'status':'needs-verification'}
            with patch.object(r,'ROOT',root),patch.object(r,'resolve',return_value=(None,report)) as search,patch.object(r.time,'sleep'):
                r.main()
            self.assertEqual(search.call_count,8)
            self.assertFalse(json.loads((root/'scripts/player-name-run-report.json').read_text())['searchUnavailable'])
    def test_namu_roster_rechecks_names_before_google_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'scripts').mkdir();(root/'dist').mkdir()
            now=r.dt.datetime.now(r.dt.timezone.utc)
            name='Current Starter'
            (root/'scripts/player-name-live-inventory.json').write_text(json.dumps({'at':now.isoformat(),'records':[{'name':name,'korean':name,'team':'Test FC','kind':'lineup','eventDate':now.isoformat()}]}))
            (root/'scripts/player-name-search-state.json').write_text(json.dumps({'schemaVersion':1,'players':{r.normalize(name):{'policy':r.POLICY,'nextCheckAt':(now+r.dt.timedelta(days=1)).isoformat()}}}))
            (root/'dist/team-ko.json').write_text('{"Test FC":"테스트 FC"}')
            checked=[]
            def roster(team,korean,rows):
                checked.extend(rows)
                return {}
            with patch.object(r,'ROOT',root),patch.object(r,'namu_team_roster',side_effect=roster),patch.object(r,'resolve') as search,patch.object(r.time,'sleep'):
                r.main()
            self.assertEqual([row['name'] for row in checked],[name])
            search.assert_not_called()
            state=json.loads((root/'scripts/player-name-search-state.json').read_text())
            self.assertEqual(state['players'][r.normalize(name)]['namuPolicy'],r.NAMU_POLICY)
    def test_two_sources_same_identity(self):
        proof = self.proof('https://namu.moe/w/Test') + self.proof('https://www.transfermarkt.co.kr/test')
        self.assertEqual(r.verify(self.row, proof)['korean'], '모리츠 니콜라스')
    def test_same_domain_not_independent(self):
        proof = self.proof('https://namu.moe/w/A') + self.proof('https://www.namu.moe/w/B')
        self.assertIsNone(r.verify(self.row, proof))
    def test_conflict_stays_english(self):
        proof = self.proof('https://namu.moe/w/A') + self.proof('https://www.transfermarkt.co.kr/B', korean='모리츠 니콜라스스')
        self.assertIsNone(r.verify(self.row, proof))
    def test_wrong_full_name_rejected(self):
        self.assertEqual(self.proof('https://namu.moe/w/A', english='Other Nicolas'), [])
    def test_wrong_team_rejected(self):
        proof = self.proof('https://namu.moe/w/A', team='Other FC') + self.proof('https://www.transfermarkt.co.kr/B', team='Other FC')
        self.assertIsNone(r.verify(self.row, proof))
    def test_search_excerpt_not_evidence(self):
        self.assertEqual(r.evidence(self.row, 'https://namu.moe/w/A', r.Page('<p>No player information</p>'), '모리츠 니콜라스', {'google'}, {}), [])
    def test_google_and_bing_attempted_with_failure(self):
        calls=[]
        def get(url):
            calls.append(url)
            raise ValueError('search-challenge')
        approved, report=r.resolve(self.row,get)
        self.assertIsNone(approved)
        self.assertEqual(len(calls),3)
        self.assertEqual(set(report['searches']),{'google','daum','bing'})
        self.assertTrue(all(x['status']=='unavailable' for x in report['searches'].values()))
    def test_blocked_engines_are_skipped_while_daum_remains_available(self):
        calls=[]
        def get(url):
            calls.append(url)
            return r.Page('<main id="daumContent">검색 결과가 없습니다</main>')
        approved, report=r.resolve(self.row,get,enabled_engines={'daum'})
        self.assertIsNone(approved)
        self.assertEqual(len(calls),1)
        self.assertIn('daum.net',calls[0])
        self.assertEqual(report['searches']['google']['status'],'disabled-after-block')
    def test_bing_recovers_verified_name_when_google_unavailable(self):
        sources=['https://namu.moe/w/Moritz','https://www.transfermarkt.co.kr/Moritz']
        def tracked(url):
            target='a1'+r.base64.urlsafe_b64encode(url.encode()).decode().rstrip('=')
            return 'https://www.bing.com/ck/a?u='+target
        def get(url):
            if 'google.com/search' in url:
                raise ValueError('search-challenge')
            if 'bing.com/search' in url:
                return r.Page(''.join(f'<a href="{tracked(source)}">모리츠 니콜라스</a>' for source in sources)
                              + f'<a href="{tracked("https://ko.wikipedia.org/wiki/Moritz")}">Wikipedia</a>')
            return self.page()
        approved, report=r.resolve(self.row,get)
        self.assertEqual(approved['korean'],'모리츠 니콜라스')
        self.assertEqual(len(approved['sources']),2)
        self.assertEqual(report['searches']['google']['status'],'unavailable')
        self.assertEqual(report['searches']['bing']['status'],'results')
    def test_safe_links_and_html(self):
        page=r.Page('<script>fake player</script><a href="/url?q=https%3A%2F%2Fko.wikipedia.org%2Fwiki%2FA">모리츠 니콜라스</a><a href="http://127.0.0.1/private">bad</a>')
        self.assertNotIn('fake player',page.text)
        self.assertEqual(r.search_links(page,'google'),[])
        self.assertIsNone(r.source_domain('https://wikipedia.org.evil.test/A'))
        self.assertIsNone(r.source_domain('https://user:password@wikipedia.org/A'))
    def test_pipeline_with_public_sources(self):
        def get(url):
            if 'google.com/search' in url:
                return r.Page('<a href="https://namu.moe/w/A">모리츠 니콜라스</a><a href="https://www.transfermarkt.co.kr/B">모리츠 니콜라스</a>')
            return self.page()
        approved, report=r.resolve(self.row,get)
        self.assertEqual(approved['korean'],'모리츠 니콜라스')
        self.assertEqual(approved['sources'][0]['engines'],['google'])
        self.assertEqual(report['status'],'verified')
    def test_namu_roster_accepts_only_exact_team_and_bilingual_row(self):
        html='<h1>포틀랜드 팀버스</h1><p>Portland Timbers</p><table><tr><th>한글 성명</th><th>로마자 성명</th></tr><tr><td>브랜든 바이</td><td>Brandon Bye</td></tr><tr><td>다른 선수</td><td>Other Player</td></tr></table>'
        row={'name':'Brandon Bye','team':'Portland Timbers','league':'mls'}
        found=r.namu_team_roster('Portland Timbers','포틀랜드 팀버스',[row],lambda url:r.Page(html))
        self.assertEqual(found['brandon bye']['korean'],'브랜든 바이')
        self.assertEqual(found['brandon bye']['method'],r.NAMU_POLICY)
        self.assertEqual(r.namu_team_roster('Portland Timbers','포틀랜드 팀버스',[row],lambda url:r.Page(html.replace('Portland Timbers','Other Club'))),{})
        self.assertEqual(r.namu_team_roster('Portland Timbers','포틀랜드 팀버스',[row],lambda url:r.Page(html.replace('Brandon Bye','Different Player'))),{})
        self.assertEqual(r.namu_team_roster('Portland Timbers','포틀랜드 팀버스',[row],lambda url:r.Page(html.replace('<h1>포틀랜드 팀버스</h1>','<h1>다른 팀</h1>'))),{})
    def test_namu_roster_tries_mirror_after_primary_error(self):
        html='<h1>포틀랜드 팀버스</h1><p>Portland Timbers</p><table><tr><th>한글 성명</th><th>로마자 성명</th></tr><tr><td>브랜든 바이</td><td>Brandon Bye</td></tr></table>'
        calls=[]
        def get(url):
            calls.append(url)
            if url.startswith('https://namu.moe/'):
                raise RuntimeError('HTTP 403')
            return r.Page(html)
        found=r.namu_team_roster('Portland Timbers','포틀랜드 팀버스',[{'name':'Brandon Bye','team':'Portland Timbers','league':'mls'}],get)
        self.assertEqual(found['brandon bye']['korean'],'브랜든 바이')
        self.assertTrue(found['brandon bye']['sources'][0]['url'].startswith('https://d.namu.moe/'))
        self.assertEqual(len(calls),2)
    def test_main_searches_more_than_thirty_without_wikipedia(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'scripts').mkdir();(root/'dist').mkdir()
            now=r.dt.datetime.now(r.dt.timezone.utc).isoformat()
            rows=[{'name':f'Player {i}','korean':f'Player {i}','team':'Test FC','kind':'lineup','eventDate':now} for i in range(35)]
            (root/'scripts/player-name-live-inventory.json').write_text(json.dumps({'at':now,'records':rows}))
            (root/'dist/team-ko.json').write_text('{}')
            result=(None,{'searches':{'google':{'status':'no-readable-trusted-results'}},'status':'needs-verification'})
            with patch.object(r,'ROOT',root),patch.object(r,'resolve',return_value=result) as search,patch.object(r.time,'sleep'):
                r.main()
            self.assertEqual(search.call_count,35)
            self.assertEqual(json.loads((root/'scripts/player-name-run-report.json').read_text())['searchChecked'],35)

if __name__=='__main__': unittest.main()
