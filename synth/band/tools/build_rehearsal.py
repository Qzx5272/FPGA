"""Build the standalone browser rehearsal room from the project's event scores."""
import json
import sys
from pathlib import Path

BAND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BAND / "host"))
from score import load

FILES = ["twinkle", "ode_to_joy", "confluence", "four_families_demo", "scale_chord_practice"]

def export(name):
    score = load(BAND / "assets" / (name + ".json"))
    pending, notes = {}, []
    for event in score["events"]:
        key = event["part"], event["note"], event["serial"]
        if event["kind"] == 0:
            pending[key] = event
        elif event["kind"] == 1:
            start = pending.pop(key)
            notes.append([start["sample"], key[0], key[1], event["sample"] - start["sample"], start["velocity"]])
    return dict(title=score["title"], bpm=score.get("performance", {}).get("tempo",120),
                length=score["duration_samples"], notes=sorted(notes))

if __name__ == "__main__":
    library = [export(name) for name in FILES]
    template = (BAND / "host" / "rehearsal.html").read_text(encoding="utf8")
    destination = BAND.parents[1] / "output" / "星群合奏室.html"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(template.replace("/* SCORE_LIBRARY */[]",json.dumps(library,ensure_ascii=False,separators=(",",":"))),encoding="utf8")
    print([len(s["notes"]) for s in library])
