"""Probe Motion via its STA IPv4; send HTTP/WS handshake only, never MOVE/ARM.

Run on the router LAN. Do not use the AP address or change laptop Wi-Fi.
"""
import argparse
import base64
import http.client
import ipaddress
import json
import os


def probe(address, port=80):
    checks = []
    for path, spoof in [('/', False), ('/', True), ('/ws', False), ('/ws', True)]:
        connection = http.client.HTTPConnection(address, port, timeout=4)
        headers = {'Host': '192.168.4.1' if spoof else address}
        if path == '/ws':
            headers.update({'Origin': 'http://192.168.4.1' if spoof else 'http://' + address,
                            'Upgrade': 'websocket', 'Connection': 'Upgrade',
                            'Sec-WebSocket-Version': '13',
                            'Sec-WebSocket-Key': base64.b64encode(os.urandom(16)).decode()})
        try:
            connection.request('GET', path, headers=headers)
            response = connection.getresponse()
            code = response.status
            # Only a server HTTP rejection or explicit EOF counts; a timeout/network
            # error cannot establish the control boundary.
            rejected = code == 403 if path == '/' else code >= 400
            checks.append({'path': path, 'spoof_ap_headers': spoof,
                           'http_status': code, 'rejected': rejected})
        except http.client.RemoteDisconnected:
            checks.append({'path': path, 'spoof_ap_headers': spoof,
                           'http_status': None, 'rejected': path == '/ws', 'eof': True})
        except (OSError, http.client.HTTPException) as error:
            checks.append({'path': path, 'spoof_ap_headers': spoof,
                           'rejected': False, 'error': type(error).__name__})
        finally:
            connection.close()
    return {'scope': 'STA only; GET/handshake, no control frames',
            'checks': checks, 'pass': all(item['rejected'] for item in checks)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ip', required=True, type=ipaddress.IPv4Address)
    args = parser.parse_args()
    if args.ip == ipaddress.ip_address('192.168.4.1') or args.ip.is_loopback or args.ip.is_unspecified or args.ip.is_multicast:
        parser.error('Use the Motion STA address shown on the dashboard, not its AP address')
    report = probe(str(args.ip))
    print(json.dumps(report, indent=2))
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
