import json
import struct
import unittest
from camera_monitor.discovery import parse_onvif, parse_dahua, merge_device, Device, dahua_probe, quiet_enough

ONVIF = b'''<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery" xmlns:a="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:dn="http://www.onvif.org/ver10/network/wsdl"><s:Body><d:ProbeMatches><d:ProbeMatch><a:EndpointReference><a:Address>urn:uuid:camera1</a:Address></a:EndpointReference><d:Types>dn:NetworkVideoTransmitter</d:Types><d:Scopes>onvif://www.onvif.org/name/Front%20door onvif://www.onvif.org/hardware/IPC</d:Scopes><d:XAddrs>http://192.168.1.20/onvif/device_service</d:XAddrs></d:ProbeMatch></d:ProbeMatches></s:Body></s:Envelope>'''

class ProtocolTests(unittest.TestCase):
    def test_onvif_extracts_device(self):
        found = parse_onvif(ONVIF, '192.168.1.20')
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].name, 'Front door')
        self.assertEqual(found[0].model, 'IPC')
        self.assertEqual(found[0].ip, '192.168.1.20')

    def test_non_video_device_not_listed_as_camera(self):
        self.assertEqual(parse_onvif(ONVIF.replace(b'dn:NetworkVideoTransmitter', b'dn:Printer').replace(b'onvif://www.onvif.org', b'printer://example.org'), '192.168.1.3'), [])

    def test_malformed_and_entity_payloads_are_ignored(self):
        for data in (b'garbage', b'<!DOCTYPE x [<!ENTITY a "bad">]><x>&a;</x>'):
            self.assertEqual(parse_onvif(data, '192.168.1.2'), [])
            self.assertEqual(parse_dahua(data, '192.168.1.2'), [])

    def test_dahua_notification_and_header(self):
        body = json.dumps({'method':'client.notifyDevInfo','params':{'deviceInfo':{'DeviceType':'IPC-HDW','MachineName':'Entry','IPv4Address':{'IPAddress':'192.168.1.20'}}}}).encode()
        packet = struct.pack('<I4s6I',32,b'DHIP',0,0,len(body),0,len(body),0) + body
        device = parse_dahua(packet, '192.168.1.20')[0]
        self.assertEqual(device.model, 'IPC-HDW')
        self.assertEqual(device.ip, '192.168.1.20')
        self.assertEqual(parse_dahua(packet[:-5], '192.168.1.20'), [])
        self.assertEqual(parse_dahua(dahua_probe(), '192.168.1.20'), [])

    def test_unexpected_json_shapes_are_ignored(self):
        for obj in ([], {'params':None}, {'params': {'deviceInfo': []}}, {'method':'other','params':{'foo':'bar'}}):
            self.assertEqual(parse_dahua(json.dumps(obj).encode(), '192.168.1.1'), [])

    def test_two_protocols_merge_without_losing_details(self):
        records = {}
        merge_device(records, Device('192.168.1.20', name='Door', protocols=['ONVIF'], urls=['http://192.168.1.20/onvif/device_service']))
        merge_device(records, Device('192.168.1.20', model='IPC', protocols=['大华 DHIP']))
        self.assertEqual(len(records), 1)
        self.assertEqual(records['192.168.1.20'].name, 'Door')
        self.assertEqual(records['192.168.1.20'].model, 'IPC')
        self.assertEqual(records['192.168.1.20'].protocols, ['ONVIF', '大华 DHIP'])

class SearchDurationTests(unittest.TestCase):
    def test_search_ends_early_only_after_something_answered(self):
        # 一台都没回话时不提前结束，否则网络只是慢一点就会被当成"没有设备"
        self.assertFalse(quiet_enough(None, 100.0, 2.5))
        self.assertFalse(quiet_enough(100.0, 101.0, 2.5))
        self.assertTrue(quiet_enough(100.0, 102.5, 2.5))
        self.assertTrue(quiet_enough(100.0, 160.0, 2.5))

if __name__ == '__main__': unittest.main()
