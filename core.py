"""Local portfolio workflow engine. Demo actor selection is NOT authentication."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, date
from pathlib import Path

ROOT = Path(__file__).parent

class Rejected(Exception):
    def __init__(self, message, status=409):
        self.status = status
        super().__init__(message)

def require(ok, message, status=409):
    if not ok:
        raise Rejected(message, status)

def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')

class Store:
    def __init__(self, path, config=None):
        self.path = str(path)
        self.config = config or json.loads((ROOT / 'config.json').read_text())
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL, at TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS requests(actor TEXT, key TEXT, payload TEXT, result TEXT,
                PRIMARY KEY(actor,key));
            CREATE TABLE IF NOT EXISTS receipts(case_id TEXT PRIMARY KEY, receipt TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS protect_events_delete BEFORE DELETE ON events
                BEGIN SELECT RAISE(ABORT,'Audit events are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS protect_events_update BEFORE UPDATE ON events
                BEGIN SELECT RAISE(ABORT,'Audit events are append-only'); END;
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL')
        try:
            with db:
                yield db
        finally:
            db.close()

    def actors(self):
        result = [dict(x) for x in self.config['actors']]
        with self.connect() as db:
            for row in db.execute('SELECT body FROM cases ORDER BY rowid'):
                c = json.loads(row['body'])
                result.append({'id': c['employee_id'], 'role': 'employee', 'name': c['name']})
        return result

    def actor(self, actor_id):
        actor = next((x for x in self.actors() if x['id'] == actor_id), None)
        require(actor is not None, 'Choose a valid demo actor.', 403)
        return actor

    def readable(self, c, actor):
        return (actor['role'] in ('operator', 'agent') or
                (actor['role'] == 'manager' and c['manager_id'] == actor['id']) or
                (actor['role'] == 'employee' and c['employee_id'] == actor['id']))

    def event(self, db, c, actor, action, detail):
        db.execute('INSERT INTO events(case_id,at,actor,action,detail) VALUES(?,?,?,?,?)',
                   (c['id'], now(), actor['id'], action, detail))

    def save(self, db, c):
        c['updated_at'] = now()
        db.execute('INSERT INTO cases(id,body) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',
                   (c['id'], json.dumps(c)))

    def summary(self, c):
        if c['approval'] == 'denied': return 'Needs revision'
        if c['delivery'] == 'failed': return 'Delivery failed'
        if c['approval'] == 'pending': return 'Needs approval'
        if c['delivery'] != 'delivered': return 'Ready to provision'
        if not c['acknowledged']: return 'Waiting on employee'
        return 'Complete'

    def actions(self, c, actor):
        result = []
        if actor['role'] == 'employee' and c['employee_id'] == actor['id'] and not c['acknowledged']:
            result.append('acknowledge')
        if actor['role'] == 'manager' and c['manager_id'] == actor['id'] and c['approval'] == 'pending':
            result += ['approve', 'deny']
        if actor['role'] == 'operator' and c['approval'] == 'approved' and c['delivery'] in ('pending', 'failed'):
            result.append('retry' if c['delivery'] == 'failed' else 'deliver')
        if actor['role'] in ('employee', 'manager', 'operator', 'agent') and not c['escalated']:
            result.append('escalate')
        if actor['role'] == 'operator' and c['escalated']:
            result.append('resolve')
        return result

    def snapshot(self, actor_id):
        actor = self.actor(actor_id)
        cases = []
        with self.connect() as db:
            for row in db.execute('SELECT body FROM cases ORDER BY rowid DESC'):
                c = json.loads(row['body'])
                if not self.readable(c, actor): continue
                c['status'] = self.summary(c)
                c['actions'] = self.actions(c, actor)
                c['events'] = [dict(e) for e in db.execute('SELECT * FROM events WHERE case_id=? ORDER BY seq DESC', (c['id'],))]
                cases.append(c)
        return {'cases': cases, 'actor': actor, 'actors': self.actors(), 'config': self.config}

    def execute(self, actor_id, payload):
        require(isinstance(payload, dict), 'Expected a JSON object.', 400)
        actor = self.actor(actor_id)
        key = payload.get('key')
        require(isinstance(key, str) and 8 <= len(key) <= 100, 'A request key is required.', 400)
        action = payload.get('action')
        require(action in ('create', 'approve', 'deny', 'acknowledge', 'deliver', 'retry', 'escalate', 'resolve'), 'Unknown action.', 400)
        allowed_fields = {'key', 'action', 'name', 'department', 'starts_on'} if action == 'create' else {'key', 'action', 'id', 'version', 'reason'}
        require(not (set(payload) - allowed_fields), 'Unexpected command fields.', 400)
        canonical = json.dumps(payload, sort_keys=True)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            c = None
            if action == 'create':
                require(actor['role'] == 'operator', 'Only People Ops can start onboarding.', 403)
            else:
                require(isinstance(payload.get('id'), str), 'A case ID is required.', 400)
                row = db.execute('SELECT body FROM cases WHERE id=?', (payload.get('id'),)).fetchone()
                require(row is not None, 'Case not found.', 404)
                c = json.loads(row['body'])
                require(self.readable(c, actor), 'Case not found for this actor.', 404)
                roles = {'approve': {'manager'}, 'deny': {'manager'}, 'acknowledge': {'employee'},
                         'deliver': {'operator'}, 'retry': {'operator'}, 'resolve': {'operator'},
                         'escalate': {'employee', 'manager', 'operator', 'agent'}}
                require(actor['role'] in roles[action], 'This actor cannot perform that action.', 403)
            prior = db.execute('SELECT payload,result FROM requests WHERE actor=? AND key=?', (actor_id, key)).fetchone()
            if prior:
                require(prior['payload'] == canonical, 'Request key reused with different content.')
                return json.loads(prior['result']) | {'replayed': True}
            if action == 'create':
                name = payload.get('name', '')
                require(isinstance(name, str) and 2 <= len(name.strip()) <= 80, 'Use a fictional name of 2–80 characters.', 400)
                dept = payload.get('department')
                require(isinstance(dept, str) and dept in self.config['departments'], 'Choose a configured department.', 400)
                starts = payload.get('starts_on', '')
                try: date.fromisoformat(starts)
                except (ValueError, TypeError): raise Rejected('Use a valid start date.', 400)
                case_id = str(uuid.uuid4())
                c = {'id': case_id, 'employee_id': 'employee-' + case_id, 'name': name.strip(),
                     'department': dept, 'manager_id': self.config['departments'][dept]['manager'],
                     'starts_on': starts, 'version': 1, 'approval': 'pending', 'acknowledged': False,
                     'delivery': 'blocked', 'attempts': 0, 'escalated': False, 'receipt': None, 'created_at': now()}
                self.event(db, c, actor, 'Onboarding started', 'Checklist created. Access is blocked until the assigned manager approves.')
                self.event(db, c, actor, 'Welcome queued in demo', 'A simulated welcome task was created. No email was sent.')
            else:
                require(type(payload.get('version')) is int and payload['version'] == c['version'], 'This case changed. Refresh before acting.')
                require(action in self.actions(c, actor), 'This action is unavailable in the current state.')
                if action in ('approve', 'deny'):
                    c['approval'] = 'approved' if action == 'approve' else 'denied'
                    c['delivery'] = 'pending' if action == 'approve' else 'blocked'
                    self.event(db, c, actor, 'Access approved' if action == 'approve' else 'Access declined',
                               'Assigned manager decision recorded. ' + ('A delivery task is now ready.' if action == 'approve' else 'No access will be provisioned.'))
                elif action == 'acknowledge':
                    c['acknowledged'] = True
                    self.event(db, c, actor, 'Handbook acknowledged', 'Employee acknowledged the fictional onboarding handbook v1.')
                elif action in ('deliver', 'retry'):
                    c['attempts'] += 1
                    # Controlled connector simulator: first attempt fails, next succeeds.
                    # One SQLite transaction is appropriate ONLY because no remote call occurs.
                    if c['attempts'] == 1:
                        c['delivery'] = 'failed'
                        self.event(db, c, actor, 'Connector unavailable', 'Simulated HTTP 503. Task retained for an operator-triggered retry; no receipt created.')
                    else:
                        receipt = 'DEMO-' + c['id'][:8].upper()
                        db.execute('INSERT OR IGNORE INTO receipts(case_id,receipt) VALUES(?,?)', (c['id'], receipt))
                        c['receipt'], c['delivery'] = receipt, 'delivered'
                        self.event(db, c, actor, 'Access provisioned in simulator', 'Connector simulator accepted one delivery. Receipt: ' + receipt)
                elif action == 'escalate':
                    reason = payload.get('reason', 'Employee requested help.')
                    require(isinstance(reason, str) and 1 <= len(reason.strip()) <= 500, 'Provide a short escalation reason.', 400)
                    require(not c['escalated'], 'An escalation is already open.')
                    c['escalated'] = True
                    self.event(db, c, actor, 'People Ops review requested', reason.strip())
                elif action == 'resolve':
                    c['escalated'] = False
                    self.event(db, c, actor, 'People Ops review resolved', 'Operator closed the review; onboarding state was not bypassed.')
                c['version'] += 1
            self.save(db, c)
            result = {'id': c['id'], 'version': c['version'], 'status': self.summary(c), 'replayed': False}
            db.execute('INSERT INTO requests VALUES(?,?,?,?)', (actor_id, key, canonical, json.dumps(result)))
            return result

    def seed(self):
        with self.connect() as db:
            if db.execute('SELECT count(*) FROM cases').fetchone()[0]: return
        specs = [('Avery Morgan', 'Engineering', 0), ('Mina Patel', 'Operations', 2), ('Theo Brooks', 'Engineering', 3)]
        for name, dept, steps in specs:
            r = self.execute('ops', {'action': 'create', 'key': 'seed-' + name, 'name': name, 'department': dept, 'starts_on': '2026-10-05'})
            if steps:
                manager = self.config['departments'][dept]['manager']
                r = self.execute(manager, {'action': 'approve', 'key': 'seed-approve-' + name, 'id': r['id'], 'version': r['version']})
                r = self.execute('ops', {'action': 'deliver', 'key': 'seed-deliver-' + name, 'id': r['id'], 'version': r['version']})
            if steps == 3:
                r = self.execute('ops', {'action': 'retry', 'key': 'seed-retry-' + name, 'id': r['id'], 'version': r['version']})
                self.execute('employee-' + r['id'], {'action': 'acknowledge', 'key': 'seed-ack-' + name, 'id': r['id'], 'version': r['version']})
