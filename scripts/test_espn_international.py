"""National-team matches need a real kickoff and two published starting elevens."""
from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import patch

spec = spec_from_file_location('international_source', Path(__file__).with_name('update-projections.py'))
source = module_from_spec(spec)
spec.loader.exec_module(source)


def team(side, name, code):
    return {'homeAway': side, 'team': {'displayName': name, 'abbreviation': code,
                                       'logo': f'https://example.com/{code}.png'}}


def roster(side):
    return {'homeAway': side, 'roster': [
        {'starter': True, 'athlete': {'displayName': f'{side} player {i}'},
         'position': {'abbreviation': 'G' if i == 0 else 'M'}} for i in range(11)
    ] + [{'starter': False, 'athlete': {'displayName': 'substitute'}}]}


event = {'id': '123', 'date': '2026-11-12T19:45Z',
         'competitions': [{'competitors': [team('home', 'Türkiye', 'TUR'),
                                           team('away', 'Belgium', 'BEL')]}]}
summary = {'rosters': [roster('away'), roster('home')]}
item = source.international_item(event, summary, 'uefa_nl')
assert item['kickoff'] == '2026-11-12T19:45Z'
assert item['names'] == {'home': '튀르키예', 'away': '벨기에'}
assert item['statuses'] == {'home': 'confirmed', 'away': 'confirmed'}
assert all(len(item['lineups'][side]) == 11 for side in ('home', 'away'))
assert source.international_item(event, {'rosters': [roster('home')]}, 'uefa_nl') is None


def fetch(url):
    if '/summary?' in url:
        return summary
    return {'events': [event] if 'dates=20261112' in url else []}


with patch.object(source, 'fetch_json', side_effect=fetch) as mocked:
    found = source.scrape_espn_international('uefa_nl', 'soccer/uefa.nations', {date(2026, 11, 13)})
assert len(found) == 1
assert sum('/summary?' in call.args[0] for call in mocked.call_args_list) == 1


def partial(url):
    if 'dates=20261113' in url:
        raise OSError('temporary failure')
    return fetch(url)


with patch.object(source, 'fetch_json', side_effect=partial):
    assert len(source.scrape_espn_international('uefa_nl', 'soccer/uefa.nations', {date(2026, 11, 13)})) == 1
print('PASS international fixtures: exact KST date, home/away, 11 starters, missing lineup rejection')
