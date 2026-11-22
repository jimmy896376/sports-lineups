import importlib.util
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('projections_injury', Path(__file__).with_name('update-projections.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class InjuryReports(TestCase):
    def test_game_specific_questionable_update_overrides_generic_out(self):
        report = {'injuries': [{'displayName': 'Atlanta Hawks', 'abbreviation': 'ATL', 'injuries': [{
            'date': '2026-11-21T22:16Z', 'status': 'Out',
            'shortComment': 'Flemings (back) is questionable to play Sunday against the Pistons.',
            'athlete': {'displayName': 'Kingston Flemings'},
        }]}]}
        with patch.object(module, 'fetch_json', return_value=report):
            result = module.fetch_espn_injury_reports('basketball/nba')
        self.assertEqual(result['ATL']['records'][0]['status'], 'Questionable')

    def test_team_nested_under_athlete_is_indexed(self):
        response = {'injuries': [{'id': '1', 'displayName': 'Atlanta Hawks', 'injuries': [{
            'date': '2026-10-24T12:00Z', 'status': 'Out',
            'athlete': {'displayName': 'Mouhamed Gueye', 'team': {'abbreviation': 'ATL', 'displayName': 'Atlanta Hawks'}},
            'details': {'type': 'Foot', 'location': 'Left'},
        }]}]}
        with patch.object(module, 'fetch_json', return_value=response):
            report = module.fetch_espn_injury_reports('basketball/nba')
        self.assertEqual(report['ATL']['records'][0]['name'], 'Mouhamed Gueye')
        self.assertEqual(report['ATL']['records'][0]['part'], 'Foot')


if __name__ == '__main__':
    main()
