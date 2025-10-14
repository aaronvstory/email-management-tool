#!/usr/bin/env python3
import json, socket, time
import requests

BASE = 'http://127.0.0.1:5000'

def tcp_check(host, port, timeout=0.5):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        try: s.close()
        except: pass

def main():
    out = {'ts': int(time.time())}
    # Healthz
    try:
        r = requests.get(f'{BASE}/healthz', timeout=3)
        out['healthz_status'] = r.status_code
        out['healthz'] = r.json() if r.ok else None
    except Exception as e:
        out['healthz_error'] = str(e)
    # Redirect (no auth)
    try:
        r2 = requests.get(f'{BASE}/dashboard', allow_redirects=False, timeout=3)
        out['dashboard_noauth_status'] = r2.status_code
    except Exception as e:
        out['dashboard_noauth_error'] = str(e)
    # SMTP reachability
    out['smtp_tcp_listening'] = tcp_check('127.0.0.1', 8587)
    # Save
    fname = f'baseline_{out["ts"]}.json'
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)
    print(fname)

if __name__ == '__main__':
    main()
