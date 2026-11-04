"""Export a saved singer-v1 score into a standalone full-stage source project."""
from pathlib import Path
import sys,argparse
b=Path(__file__).resolve().parents[1];sys.path.insert(0,str(b/'host'))
from score import load
from offline_stage import export_stage_project
ap=argparse.ArgumentParser();ap.add_argument('score',type=Path);ap.add_argument('destination',type=Path);ap.add_argument('--manual-start',action='store_true');a=ap.parse_args()
print(export_stage_project(load(a.score),a.destination,autoplay=not a.manual_start))
