"""命名布局方案：同一批摄像头的不同摆法（例如「大门组」「夜班」）。"""
from __future__ import annotations

import json

KEY = 'monitor/layout_profiles'


def _clean(document):
    if not isinstance(document, dict):
        return None
    slots = document.get('slots')
    if not isinstance(slots, list):
        return None
    try:
        capacity = int(document.get('capacity', 4))
    except (TypeError, ValueError):
        capacity = 4
    columns = document.get('columns') if isinstance(document.get('columns'), dict) else {}
    return {
        'capacity': capacity,
        'slots': [str(ip or '') for ip in slots][:25],
        'columns': {str(k): int(v) for k, v in columns.items()
                    if str(k).isdigit() and str(v).isdigit()},
        'fill_width': bool(document.get('fill_width', False)),
        'organization': str(document.get('organization', '') or '')[:80],
    }


def load_all(settings):
    raw = settings.value(KEY, '')
    if not raw:
        return {}
    try:
        data = json.loads(str(raw))
    except ValueError:
        return {}
    if not isinstance(data, dict):
        return {}
    result = {}
    for name, document in data.items():
        cleaned = _clean(document)
        if isinstance(name, str) and name and cleaned is not None:
            result[name] = cleaned
    return result


def save_all(settings, profiles):
    settings.setValue(KEY, json.dumps(profiles, ensure_ascii=False))
    settings.sync()
    if settings.status() != settings.Status.NoError:
        raise OSError('Could not save layout profiles')


def save_profile(settings, name, document):
    name = name.strip()
    if not name:
        raise ValueError('方案名称不能为空')
    cleaned = _clean(document)
    if cleaned is None:
        raise ValueError('布局方案内容不完整')
    profiles = load_all(settings)
    profiles[name] = cleaned
    save_all(settings, profiles)
    return cleaned


def delete_profile(settings, name):
    profiles = load_all(settings)
    profiles.pop(name, None)
    save_all(settings, profiles)
