import unittest
from lexicon import ROOT, lookup, normalize

class LexiconTests(unittest.TestCase):
    def test_tones_and_umlaut(self):
        for text, expected in [('lǜ','lü4'), ('nǚ','nü3'), ('mā','ma1'), ('ma','ma5'), ('ń','n2'), ('ê','ê5')]:
            self.assertEqual(normalize(text)['numbered'], expected)

    def test_context_and_ambiguity(self):
        result = lookup('重庆银行音乐')
        flattened = [p['numbered'] for t in result['tokens'] for p in t['readings'][0]]
        self.assertEqual(flattened, ['chong2','qing4','yin2','hang2','yin1','yue4'])
        char = lookup('行')['tokens'][0]
        self.assertTrue(char['needs_review'])
        self.assertGreater(len(char['readings']), 1)

    def test_unknown_and_punctuation(self):
        tokens = lookup('你，🙂')['tokens']
        self.assertEqual([t['source'] for t in tokens], ['character','pause','unknown'])
        self.assertTrue(tokens[-1]['needs_review'])

    def test_no_audio_files(self):
        for path in (ROOT/'sources').rglob('*'):
            if path.is_file():
                with path.open('rb') as stream:
                    header = stream.read(12)
                self.assertFalse(header[:4] == b'RIFF' and header[8:12] == b'WAVE', str(path))

if __name__ == '__main__':
    unittest.main()
