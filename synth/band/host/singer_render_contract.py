"""Fail before compilation when a full-song singer render has the wrong score."""
import math
from score import validate


def check_render_score(score, seconds):
    validate(score)
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('Render duration must be finite and positive')
    if score.get('engine_profile') != 'singer-v1':
        raise ValueError('Singer rendering requires singer-v1')
    frames = round(seconds * 48000)
    notes = [e for e in score['events']
             if e['part'] == 15 and e['kind'] == 0 and e['sample'] < frames]
    full_song = frames >= score['duration_samples']
    if full_song and not notes:
        raise ValueError('Full singer render requires part15 note-on events; this score has none')
    return dict(frames=frames, duration_samples=score['duration_samples'],
                full_song=full_song, singer_note_ons=len(notes),
                first_singer_sample=notes[0]['sample'] if notes else None)
