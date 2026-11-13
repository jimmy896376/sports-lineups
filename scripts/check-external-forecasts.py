# -*- coding: utf-8 -*-
"""Contract tests for published probability parsers (no network)."""
import importlib.util
import json
from pathlib import Path
spec = importlib.util.spec_from_file_location('forecasts',Path(__file__).with_name('update-external-forecasts.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
event = {'@type':'SportsEvent','homeTeam':{'name':'Home FC'},'awayTeam':{'name':'Away FC'},'startDate':'2026-10-22T18:00:00Z'}
source = '<script type="application/ld+json">'+json.dumps(event)+'</script><p>Our analysis suggests the most likely outcome of this match is a <b>Away FC</b> win with a probability of <b>45.1%</b>. A win for <b>Home FC</b> has a probability of <b>29.9%</b> and a draw has a probability of <b>25.0%</b>.</p>'
row = module.parse_mole(source)
assert row['values']=={'home':29.9,'away':45.1,'draw':25.0},'Do not assume first mentioned team is home'
assert module.parse_mole(source.replace('45.1%','95.1%')) is None
assert module.parse_mole(source.replace('Away FC</b> win','Other FC</b> win')) is None
assert module.parse_mole('<p>Home FC 80% confidence pick</p>') is None
draw_second = source.replace('A win for <b>Home FC</b> has a probability of <b>29.9%</b> and a draw has a probability of <b>25.0%</b>', 'A draw has a probability of <b>25.0%</b> and a win for <b>Home FC</b> has a probability of <b>29.9%</b>')
assert module.parse_mole(draw_second)['values']==row['values'],'Accept either sentence order'
assert module.key('FC Bayern Munich') == module.key('Bayern')
assert module.key('SC Freiburg') == module.key('Freiburg')
match = {'id':1,'homeTeamId':13,'awayTeamId':14,'homeTeamName':'Home','awayTeamName':'Away','matchDate':'2026-10-22T13:00:00+09:00'}
briefing = {'matchId':1,'homeTeamId':13,'awayTeamId':14,'modelEstimate':{'setAnalysis':{'homeSetProbability':.8,'homeMatchProbability':.513}}}
data = {'data':{'upcomingMatches':[match],'briefings':[briefing]}}
source = '<script id="volley-public-data" type="application/json">'+json.dumps(data)+'</script>'
row = module.parse_volley(source)[0]
assert abs(row['values']['home']-51.3)<1e-8,'Use match probability, never set probability'
briefing['homeTeamId']=14
assert not module.parse_volley('<script id="volley-public-data">'+json.dumps(data)+'</script>')
widget = '<li><span>11. 14. (토) 01:00</span><span>토르페도 니즈니노브고로드</span><span>vs</span><span>라다 톨리야티</span><span>홈 <!-- -->72<!-- -->%</span><span>원정 <!-- -->28<!-- -->%</span></li>'
rows = module.parse_scorebase_widget(widget)
assert len(rows)==1 and rows[0]['values']=={'home':72.0,'away':28.0,'draw':0},'Keep Scorebase home/away orientation'
assert module.scorebase_key('HC 라다 톨리야티')==module.scorebase_key('라다 톨리야티')
assert module.scorebase_key('로스앤젤레스 킹스')==module.scorebase_key('LA 킹스')
for feed_name, widget_name in [('부산 KCC 이지스','부산 KCC'),('창원 LG 세이커스','창원 LG'),('울산 현대모비스 피버스','울산 현대모비스'),('서울 삼성 썬더스','서울 삼성'),('우리은행','아산 우리은행'),('BNK 썸','부산 BNK 썸'),('삼성생명','용인 삼성생명'),('KB스타즈','청주 KB스타즈'),('하나은행','부천 하나은행'),('신한은행','인천 신한은행'),('수원 한국전력 빅스톰','한국전력 빅스톰'),('KB손해보험','KB손해보험 스타즈'),('인천 대한항공 점보스','대한항공 점보스'),('대전 삼성화재 블루팡스','삼성화재 블루팡스'),('서울 우리카드 우리WON','우리카드 우리WON'),('현대캐피탈','현대캐피탈 스카이워커스'),('부산 OK저축은행 읏맨','OK저축은행 읏맨'),('흥국생명','흥국생명 핑크스파이더스'),('GS칼텍스 서울 KIXX','GS칼텍스 KIXX'),('SOOP 수퍼스','SOOP 소퍼스'),('정관장','정관장 레드스파크스')]:
    assert module.scorebase_key(feed_name)==module.scorebase_key(widget_name),(feed_name,widget_name)
assert module.scorebase_key('서울 삼성 썬더스')!=module.scorebase_key('용인 삼성생명'), 'Different teams must not merge'
for feed_name, publisher_name in [('수원 한국전력 빅스톰','한국전력'),('인천 대한항공 점보스','대한항공'),('대전 삼성화재 블루팡스','삼성화재'),('서울 우리카드 우리WON','우리카드'),('부산 OK저축은행 읏맨','OK저축은행'),('IBK기업은행 알토스','IBK기업은행'),('GS칼텍스 서울 KIXX','GS칼텍스'),('현대건설 힐스테이트','현대건설'),('한국도로공사 하이패스','한국도로공사')]:
    assert module.scorebase_key(feed_name)==module.scorebase_key(publisher_name),(feed_name,publisher_name)
assert module.parse_scorebase_widget(widget.replace('28<!-- -->%','38<!-- -->%'))==[], 'Reject probabilities that do not sum to 100'
assert module.parse_scorebase_widget(widget.replace('홈 <!-- -->72<!-- -->%','AI 예측 준비 중'))==[], 'Do not invent missing predictions'
football=widget.replace('홈 <!-- -->72<!-- -->%','홈 <!-- -->42<!-- -->%<span>무 <!-- -->30<!-- -->%</span>')
assert module.parse_scorebase_widget(football)[0]['values']=={'home':42.0,'away':28.0,'draw':30.0}, 'Include football draw probability'
print('Published probabilities: full-match parsing, home/away mapping, sum checks and rejected unrelated picks passed.')
