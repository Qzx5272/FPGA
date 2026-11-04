"""Export the onboard-audio workstation; does not program hardware."""
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from score import load
from offline_pt8211_dvi import export_pt8211_dvi_project
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('score',type=Path);ap.add_argument('destination',type=Path)
ap.add_argument('--manual-start',action='store_true')
args=ap.parse_args()
print(export_pt8211_dvi_project(load(args.score),args.destination,autoplay=not args.manual_start))
