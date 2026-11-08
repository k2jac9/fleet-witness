#!/usr/bin/env python3
"""Check the owner's dashboard; never print credentials or follow redirects."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from urllib.error import HTTPError
from urllib.parse import urlsplit

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def check(base, password):
    target = urlsplit(base)
    if (target.username or target.password or target.query or target.fragment or target.path not in ('','/')
            or not target.hostname or (target.scheme != 'https' and
                not (target.scheme == 'http' and target.hostname in ('127.0.0.1','::1')))):
        raise ValueError('HTTPS required except numeric loopback; no embedded credentials or URL suffix')
    opener=build_opener(ProxyHandler({}), NoRedirect())
    auth='Basic '+base64.b64encode(('owner:'+password).encode()).decode()
    results=[]
    def request(path, expected, method='GET', authorization=None):
        headers={} if authorization is None else {'Authorization':authorization}
        req=Request(base+path,headers=headers,method=method)
        try: response=opener.open(req,timeout=15)
        except HTTPError as error: response=error
        with response:
            body=response.read(2*1024*1024+1)
            status=response.status
            csp=response.headers.get('Content-Security-Policy','')
            challenge=response.headers.get('WWW-Authenticate','')
        assert status == expected, (path,method,status,expected)
        assert len(body)<=2*1024*1024, 'response too large'
        if status == 401: assert challenge.startswith('Basic '), 'missing challenge'
        if status == 200: assert "default-src 'none'" in csp and "frame-ancestors 'none'" in csp
        results.append(dict(path=path,method=method,status=status,bytes=len(body),sha256=hashlib.sha256(body).hexdigest()))
        return body
    for path in ('/','/index.html','/styles.css','/app.js','/replay.json'):
        request(path,401)
        request(path,401,authorization='Basic b3duZXI6d3Jvbmc=')
        body=request(path,200,authorization=auth)
        if path=='/replay.json': assert json.loads(body)['mode']=='scripted-demo'
    for path in ('/witness.sqlite3','/.env','/Caddyfile','/summary.json','/../witness.sqlite3','/%2e%2e/witness.sqlite3','/seed-0/','/foo','//witness.sqlite3'):
        request(path,404,authorization=auth)
    for method in ('POST','PUT','PATCH','DELETE','OPTIONS'):
        request('/',405,method,auth)
        request('/',401,method)
    request('/',200,'HEAD',auth)
    return results

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',required=True)
    p.add_argument('--password-file',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(check(a.url.rstrip('/'),a.password_file.read_text().strip()),indent=2))
