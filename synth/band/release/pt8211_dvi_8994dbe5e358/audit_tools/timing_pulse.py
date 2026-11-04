"""Read vendor minimum-pulse-width results; setup/hold alone are insufficient."""
import html
import math
import re


def pulse_rows(text):
    if 'Minimum_Pulse_Width_Report' not in text:
        raise ValueError('Missing minimum pulse-width report')
    rows = []
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', text, re.S):
        cells = [html.unescape(re.sub('<[^>]+>', '', x)).strip()
                 for x in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.S)]
        kinds = ('High Pulse Width', 'Low Pulse Width')
        if cells and cells[0].isdigit() and any(kind in cells for kind in kinds):
            if len(cells) != 7 or cells[4] not in kinds:
                raise ValueError('Malformed pulse-width path; cannot safely ignore it')
            slack, actual, required = map(float, cells[1:4])
            if not all(math.isfinite(x) for x in (slack, actual, required)):
                raise ValueError('Nonfinite pulse-width result')
            if required < 0 or not cells[5] or not cells[6]:
                raise ValueError('Invalid pulse-width requirement or missing clock/endpoint')
            rows.append(dict(slack_ns=slack, actual_ns=actual, required_ns=required,
                             kind=cells[4], clock=cells[5], endpoint=cells[6]))
    if not rows:
        raise ValueError('No parsed pulse-width paths; review report format before release')
    return rows


def require_clean_pulse(text):
    rows = pulse_rows(text)
    failures = [r for r in rows if r['slack_ns'] < 0 or r['actual_ns'] < r['required_ns']]
    if failures:
        raise ValueError(f'Minimum pulse-width violations: {len(failures)} reported paths; release blocked')
    return rows
