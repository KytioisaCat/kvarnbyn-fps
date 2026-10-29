#!/usr/bin/env python3
"""Servera webbexporten över HTTPS på hemnätet, så att telefonen kan köra den.

Godot-spel i webbläsaren kräver en säker sida (HTTPS); localhost räknas som säker men inte
http://<laptopens IP>. Certifikatet är självsignerat (v2/.tools/lan-cert/, gitignorerat):
telefonen varnar första gången — välj "Visa detaljer" → "Besök webbplatsen" (Safari) eller
"Avancerat" → "Fortsätt" (Chrome).

    python3 v2/poc/torget/serve_https.py            # port 8791, katalogen web-mobil/
"""
import http.server, ssl, sys, pathlib, functools
ROOT = pathlib.Path(__file__).resolve().parents[3]
DIR = ROOT / 'v2/poc/torget/web-mobil'
CERT = ROOT / 'v2/.tools/lan-cert'
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8791
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIR))
httpd = http.server.ThreadingHTTPServer(('0.0.0.0', port), handler)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(CERT / 'cert.pem', CERT / 'key.pem')
httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
print(f'HTTPS på port {port}, katalog {DIR}', flush=True)
httpd.serve_forever()
