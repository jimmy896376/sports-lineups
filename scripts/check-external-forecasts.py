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
assert module.parse_scorebase_widget(widget.replace('28<!-- -->%','38<!-- -->%'))==[], 'Reject probabilities that do not sum to 100'
assert module.parse_scorebase_widget(widget.replace('홈 <!-- -->72<!-- -->%','AI 예측 준비 중'))==[], 'Do not invent missing predictions'
football=widget.replace('홈 <!-- -->72<!-- -->%','홈 <!-- -->42<!-- -->%<span>무 <!-- -->30<!-- -->%</span>')
assert module.parse_scorebase_widget(football)[0]['values']=={'home':42.0,'away':28.0,'draw':30.0}, 'Include football draw probability'
print('Published probabilities: full-match parsing, home/away mapping, sum checks and rejected unrelated picks passed.')
