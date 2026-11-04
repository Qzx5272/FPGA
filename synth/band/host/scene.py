"""Validate a scene completely before applying any state to the running desk."""
def validate_performance(performance):
    from score import validate
    from pathlib import Path
    import json
    if not isinstance(performance,dict):raise ValueError('场景参数必须为对象')
    score=json.loads((Path(__file__).resolve().parents[1]/'assets/confluence.json').read_text(encoding='utf-8'))
    score['performance']=performance
    validate(score)
    return performance
