import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'host'))
from singer_render_contract import check_render_score


class SingerRenderContractTests(unittest.TestCase):
    def setUp(self):
        self.score = json.loads((Path(__file__).resolve().parents[1] /
                                 'assets/confluence_singer.json').read_text(encoding='utf-8'))

    def test_actual_acceptance_song(self):
        result = check_render_score(self.score, 96)
        self.assertTrue(result['full_song'])
        self.assertEqual(result['singer_note_ons'], 96)
        self.assertEqual(result['first_singer_sample'], 48 * 48000)

    def test_missing_singer_fails_before_long_render(self):
        score = copy.deepcopy(self.score)
        score['events'] = [e for e in score['events'] if e['part'] != 15]
        with self.assertRaisesRegex(ValueError, 'part15'):
            check_render_score(score, 96)

    def test_short_instrumental_intro_is_allowed(self):
        result = check_render_score(self.score, 1)
        self.assertFalse(result['full_song'])
        self.assertEqual(result['singer_note_ons'], 0)
