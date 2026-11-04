"""Export the clocked video-only DVI workstation candidate; does not program hardware."""
import sys,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from score import load
from offline_dvi import export_dvi_project
parser=argparse.ArgumentParser()
parser.add_argument('score',type=Path);parser.add_argument('destination',type=Path)
parser.add_argument('--manual-start',action='store_true')
args=parser.parse_args()
print(export_dvi_project(load(args.score),args.destination,autoplay=not args.manual_start))
