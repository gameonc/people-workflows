#!/usr/bin/env python3
"""Loopback-only demo server with fictional data. No third-party credentials required."""
import argparse
import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from core import Store, Rejected
from knowledge import answer, POLICIES

ROOT = Path(__file__).parent

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(20)

    def log_message(self, fmt, *args):
        pass

    def respond(self, data, status=200, mime='application/json'):
        raw = json.dumps(data).encode() if mime == 'application/json' else data
        self.send_response(status)
        self.send_header('Content-Type', mime + '; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(raw)

    def check_host(self):
        port = self.server.server_address[1]
        if self.headers.get('Host') not in (f'127.0.0.1:{port}', f'localhost:{port}'):
            raise Rejected('Use the local demo address.', 403)

    def do_GET(self):
        try:
            self.check_host()
            path = urlparse(self.path).path
            if path == '/api/bootstrap':
                return self.respond({'token': self.server.token, 'policies': POLICIES,
                    'model_configured': bool(os.environ.get('PEOPLE_OLLAMA_MODEL'))})
            if path == '/api/state':
                return self.respond(self.server.store.snapshot(self.headers.get('X-Demo-Actor', 'ops')))
            if path == '/api/health':
                return self.respond({'status': 'ok', 'mode': 'local synthetic demonstration', 'external_connectors': 'simulated'})
            files = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
            if path not in files: raise Rejected('Not found.', 404)
            name, mime = files[path]
            self.respond((ROOT / 'static' / name).read_bytes(), mime=mime)
        except Rejected as e: self.respond({'error': str(e)}, e.status)
        except Exception:
            self.respond({'error': 'The demo could not load this request. Try again.'}, 500)

    def do_POST(self):
        try:
            self.check_host()
            port = self.server.server_address[1]
            origin = self.headers.get('Origin')
            if origin not in (None, f'http://127.0.0.1:{port}', f'http://localhost:{port}'):
                raise Rejected('Cross-origin commands are disabled.', 403)
            supplied_token = self.headers.get('X-Demo-Token', '')
            if not supplied_token.isascii() or not secrets.compare_digest(supplied_token, self.server.token):
                raise Rejected('Reload the demo before sending a command.', 403)
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise Rejected('JSON content is required.', 400)
            try: length = int(self.headers.get('Content-Length', '0'))
            except ValueError: raise Rejected('Invalid request length.', 400)
            if not 0 < length <= 32768: raise Rejected('Request is empty or too large.', 400)
            try: payload = json.loads(self.rfile.read(length))
            except (ValueError, UnicodeError): raise Rejected('Invalid JSON.', 400)
            if not isinstance(payload, dict): raise Rejected('Expected a JSON object.', 400)
            actor = self.headers.get('X-Demo-Actor', '')
            self.server.store.actor(actor)
            if self.path == '/api/command': result = self.server.store.execute(actor, payload)
            elif self.path == '/api/ask': result = answer(payload.get('question'))
            else: raise Rejected('Not found.', 404)
            self.respond(result)
        except Rejected as e: self.respond({'error': str(e)}, e.status)
        except Exception:
            self.respond({'error': 'The request did not finish. Refresh to check the case before retrying.'}, 500)


def make_server(port=8766, database=None):
    database = database or ROOT / '.data' / 'demo.sqlite3'
    Path(database).parent.mkdir(parents=True, exist_ok=True)
    store = Store(database)
    store.seed()
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.store, server.token = store, secrets.token_urlsafe(32)
    return server

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--db', default=None)
    args = parser.parse_args()
    server = make_server(args.port, args.db)
    print(f'CLD People Workflows: http://127.0.0.1:{server.server_address[1]}', flush=True)
    print('Fictional data. Demo actor switching is not authentication. Connectors are simulated.', flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()
