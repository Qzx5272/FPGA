"""Export score/presets into combined I2S+spectrum workstation sources."""
from pathlib import Path
import sys,argparse
b=Path(__file__).resolve().parents[1];sys.path.insert(0,str(b/'host'))
from score import load
from offline_workstation import export_workstation_project
ap=argparse.ArgumentParser();ap.add_argument('score',type=Path);ap.add_argument('destination',type=Path);ap.add_argument('--manual-start',action='store_true');a=ap.parse_args()
print(export_workstation_project(load(a.score),a.destination,autoplay=not a.manual_start))
