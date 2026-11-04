"""Export a saved singer-v1 score as shared256 PT8211/DVI sources; never program."""
from pathlib import Path
import argparse
import sys

band = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(band / 'host'))
from score import load
from offline_shared import export_shared_project

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('score', type=Path)
ap.add_argument('destination', type=Path)
ap.add_argument('--manual-start', action='store_true')
args = ap.parse_args()
print(export_shared_project(load(args.score), args.destination, autoplay=not args.manual_start))
