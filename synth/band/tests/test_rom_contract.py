from pathlib import Path
import sys,unittest,tempfile
band=Path(__file__).resolve().parents[1];sys.path.insert(0,str(band/'host'))
from rom_contract import check_vocoder_rom,check_coefficient_width

class ROMContractTests(unittest.TestCase):
    def test_actual_upstream_2d_table_is_blocked(self):
        with self.assertRaisesRegex(ValueError,'one-dimensional'):
            check_vocoder_rom(band/'experimental/vocoder/upstream/filterbank.sv')

    def test_corrected_ported_table_is_exportable(self):
        check_vocoder_rom(band/'experimental/vocoder/ported/filterbank.sv')

    def test_coefficient_width_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'coeffs.mem'
            path.write_text('ffe00000\n001fffff\n')
            check_coefficient_width(path,22)
            for value in ('00200000','ffdfffff'):
                path.write_text(value)
                with self.assertRaisesRegex(ValueError,'refusing lossy truncation'):
                    check_coefficient_width(path,22)

if __name__=='__main__':unittest.main()
