"""整机配置的导出与导入：相机清单、名称、顺序、连接方式、画面标注（不含密码）。

用途：给多台电脑批量部署。先在样板机上配好，导出成 json；
其它电脑导入后重启一次，墙和名称就跟样板机一样了。

密码只存在系统钥匙串里，**不写进配置文件**——换台电脑要重新填一次，
这是有意的：配置文件会被拷来拷去，不该带着摄像头账号走。
"""
import json
from datetime import datetime

FORMAT = 'camera-monitor-config'
VERSION = 1


class ConfigError(Exception):
    """配置文件格式不对，或内容不可用。"""


def _camera_entry(device, names, options):
    entry = {
        'ip': device.ip,
        'name': names.get(device.ip),
        'model': device.model or '',
        'manufacturer': device.manufacturer or '',
        'protocols': list(device.protocols),
        'urls': list(device.urls),
        'transport': options.transport(device.ip),
    }
    color, corner = names.appearance(device.ip)
    entry['appearance'] = {'color': color, 'corner': corner}
    return entry


def export_config(path, names, options, devices, capacity=0, slots=()):
    """把当前配置写成 json，返回路径（自动补 .json）。"""
    path = str(path)
    if not path.lower().endswith('.json'):
        path += '.json'
    document = {
        'format': FORMAT,
        'version': VERSION,
        'exported_at': datetime.now().isoformat(timespec='seconds'),
        'layout': {'capacity': int(capacity), 'slots': [str(ip or '') for ip in slots]},
        'cameras': [_camera_entry(device, names, options) for device in devices],
    }
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
    return path


def load_config(path):
    """读入并校验配置文件；格式不对抛 ConfigError。"""
    try:
        with open(path, encoding='utf-8') as handle:
            document = json.load(handle)
    except (OSError, ValueError) as exc:
        raise ConfigError('配置文件读不出来，请确认是本软件导出的 json。') from exc
    if not isinstance(document, dict) or document.get('format') != FORMAT:
        raise ConfigError('这不是 Camera Monitor 的配置文件。')
    cameras = document.get('cameras')
    if not isinstance(cameras, list):
        raise ConfigError('配置文件里没有摄像头清单。')
    valid = [camera for camera in cameras if isinstance(camera, dict) and str(camera.get('ip') or '').strip()]
    if not valid:
        raise ConfigError('配置文件里没有可用的摄像头。')
    document['cameras'] = valid
    return document


def apply_config(document, names, options):
    """把名称、标注、连接方式、排列顺序写进本机设置；返回写入的相机台数。

    不动监控墙本身：界面重建容易把正在播的画面打断，
    导入后提示用户重启一次更稳。
    """
    count = 0
    for camera in document.get('cameras', []):
        ip = str(camera.get('ip') or '').strip()
        if not ip:
            continue
        count += 1
        name = camera.get('name')
        if isinstance(name, str) and name.strip():
            names.save(ip, name)
        transport = camera.get('transport')
        if transport in ('tcp', 'udp'):
            options.save_transport(ip, transport)
        appearance = camera.get('appearance')
        if isinstance(appearance, dict):
            color, corner = appearance.get('color'), appearance.get('corner')
            if color in names.COLORS and corner in names.CORNERS:
                names.save_appearance(ip, color, corner)
    slots = document.get('layout', {}).get('slots')
    if isinstance(slots, list):
        names.save_slot_order([str(ip or '') for ip in slots])
    return count
