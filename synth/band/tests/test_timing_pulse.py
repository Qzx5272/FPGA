import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from timing_pulse import require_clean_pulse


def report(slack='1.0', actual='1.2', required='0.2'):
    return ('Minimum_Pulse_Width_Report<table><tr class="path">' +
            ''.join('<td>' + x + '</td>' for x in
                    ['1', slack, actual, required, 'High Pulse Width', 'serial_clk', 'ff/CLK']) +
            '</tr></table>')


class PulseGateTests(unittest.TestCase):
    def test_positive_and_zero_margin(self):
        self.assertEqual(len(require_clean_pulse(report())), 1)
        self.assertEqual(len(require_clean_pulse(report('0', '.2', '.2'))), 1)

    def test_negative_or_inconsistent_width(self):
        for values in [('-0.01', '.19', '.2'), ('1', '.19', '.2')]:
            with self.assertRaises(ValueError): require_clean_pulse(report(*values))

    def test_missing_or_empty(self):
        for text in ['', 'Minimum_Pulse_Width_Report<table></table>']:
            with self.assertRaises(ValueError): require_clean_pulse(text)

    def test_nonfinite_and_invalid_requirement(self):
        for values in [('nan', '1.2', '.2'), ('1', 'inf', '.2'), ('1', '1.2', '-.2')]:
            with self.assertRaises(ValueError): require_clean_pulse(report(*values))

    def test_malformed_negative_not_hidden_by_positive(self):
        malformed = report('-.8', '-.6', '.2').replace('<td>ff/CLK</td>', '')
        with self.assertRaises(ValueError): require_clean_pulse(report() + malformed)


if __name__ == '__main__': unittest.main()
