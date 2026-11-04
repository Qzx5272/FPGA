"""Enumerate clock arithmetic, not vendor or physical timing acceptance.

UG306-1.0.7E section 5.1: internal feedback and 1/8 MDIV steps.
DS1239-1.0.3E table 3-18: PFD 19..81.25 MHz.
Keep the 138K VCO bound 650..1300 MHz. Only integer output division
is explored here; other electrical restrictions still require vendor checks.
"""
from fractions import Fraction as F
from pathlib import Path
import json


def candidates():
    for idiv in range(1, 65):
        pfd = F(50, idiv)
        if not F(19) <= pfd <= F(325, 4):
            continue
        for fbdiv in range(1, 65):
            for m8 in range(16, 1025):
                vco = pfd * fbdiv * F(m8, 8)
                if not 650 <= vco <= 1300:
                    continue
                for odiv in range(1, 129):
                    serial = vco / odiv
                    if abs(serial - 126) > 2:
                        continue
                    yield dict(idiv=idiv, fbdiv=fbdiv, mdiv=m8 // 8,
                               mdiv_fraction=m8 % 8, odiv=odiv,
                               pfd_mhz=float(pfd), vco_mhz=float(vco),
                               serial_mhz=float(serial), pixel_mhz=float(serial / 5),
                               error_ppm=float((serial / 126 - 1) * 1000000),
                               exact_126=serial == 126)


if __name__ == '__main__':
    rows = sorted(candidates(), key=lambda x: (abs(x['error_ppm']), x['fbdiv'], x['idiv']))
    result = dict(status='arithmetic_review_only', exact_126_count=sum(x['exact_126'] for x in rows),
                  candidates_within_2mhz=len(rows), closest=rows[:12],
                  scope='Integer output division only; no RTL changed, no synthesis, no board proof. Frequency changes require explicit matching constraints and validation.')
    out = Path(__file__).resolve().parents[1] / 'evidence/pulse_width_review/integer_output_candidates.json'
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
