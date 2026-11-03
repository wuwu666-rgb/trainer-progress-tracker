import os
import json
import uuid
import hashlib
import sqlite3
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from functools import wraps
from flask import Flask, request, session, jsonify, g, send_from_directory
from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException

ROOT = Path(__file__).parent
def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc).isoformat()
def today(): return datetime.now(ZoneInfo('America/New_York')).date().isoformat()

class Problem(Exception):
    def __init__(self, message, status=400): self.message, self.status = message, status

def create_app(config=None):
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    instance = Path(os.environ.get('TRACKER_DATA_DIR', str(ROOT / 'instance')))
    instance.mkdir(parents=True, exist_ok=True)
    secret_file = instance / '.secret'
    if not secret_file.exists(): secret_file.write_text(os.urandom(32).hex())
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY', secret_file.read_text()), DATABASE=str(instance/'tracker.sqlite3'), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE')=='1', MAX_CONTENT_LENGTH=1024*1024, WTF_CSRF_TIME_LIMIT=None)
    if config: app.config.update(config)
    CSRFProtect(app)

    def db():
        if 'db' not in g:
            g.db = sqlite3.connect(app.config['DATABASE'], timeout=15)
            g.db.row_factory = sqlite3.Row
            g.db.execute('PRAGMA foreign_keys=ON')
        return g.db

    @app.teardown_appcontext
    def close(error):
        if 'db' in g: g.db.close()

    def one(sql, args=()):
        r = db().execute(sql, args).fetchone()
        return dict(r) if r else None
    def many(sql, args=()): return [dict(r) for r in db().execute(sql, args)]
    def insert(table, data):
        db().execute(f"INSERT INTO {table} ({','.join(data)}) VALUES ({','.join('?' for _ in data)})", tuple(data.values()))
        return data
    def body():
        x = request.get_json(silent=True)
        if not isinstance(x, dict): raise Problem('The request must contain a JSON object.')
        return x
    def text(x, key, limit=200):
        v = x.get(key)
        if not isinstance(v, str) or not v.strip() or len(v.strip())>limit: raise Problem(f'{key} is required and must be {limit} characters or fewer.')
        return v.strip()
    def integer(v, maximum=1000):
        if isinstance(v, bool) or not isinstance(v, int) or not 1<=v<=maximum: raise Problem('Sets and reps must be valid positive whole numbers.')
        return v
    def weight(v, positive=False):
        try: d = Decimal(str(v))
        except (InvalidOperation, ValueError): raise Problem('Enter a valid weight.')
        if not d.is_finite() or d<0 or (positive and d<=0) or d>10000: raise Problem('The weight is outside the allowed range.')
        return str(d)
    def date(v):
        try:
            if not isinstance(v, str) or datetime.strptime(v,'%Y-%m-%d').strftime('%Y-%m-%d') != v or v>today(): raise ValueError()
        except ValueError: raise Problem('Enter a valid date that is today or earlier in New York time.')
        return v
    def exercises(rows, results=False, completed=False):
        if not isinstance(rows, list) or len(rows)>100: raise Problem('The exercise list is invalid.')
        out=[]
        count=0
        for n,e in enumerate(rows):
            if not isinstance(e, dict): raise Problem('The exercise is invalid.')
            item=dict(id=e.get('id') or uid(), position=n+1, name=text(e,'name'), target_sets=integer(e.get('target_sets',1),100), target_reps=integer(e.get('target_reps',1)))
            if results:
                sets=e.get('sets',[])
                if not isinstance(sets,list) or len(sets)>100: raise Problem('The workout sets are invalid.')
                item['sets']=[dict(id=s.get('id') or uid(),set_number=i+1,actual_reps=integer(s.get('actual_reps')),weight_lb=weight(s.get('weight_lb'))) for i,s in enumerate(sets) if isinstance(s,dict)]
                if len(item['sets'])!=len(sets): raise Problem('The workout sets are invalid.')
                count+=len(sets)
            out.append(item)
        if completed and not count: raise Problem('Add at least one exercise with one recorded set to complete the workout.')
        if not results and not out: raise Problem('Add at least one exercise.')
        return out
    def user():
        u=one('SELECT id,name,email,role FROM users WHERE id=?',(session.get('user_id'),))
        if not u: raise Problem('Please sign in first.',401)
        return u
    def trainer():
        u=user()
        if u['role']!='trainer': raise Problem('Only trainers can perform this action.',403)
        return u
    def profile(pid):
        p=one('SELECT * FROM client_profiles WHERE id=?',(pid,)); u=user()
        if not p or u['id'] not in (p['trainer_id'],p['client_user_id']): raise Problem('You do not have access to this client.',403)
        return p
    def decode(r):
        if r and 'exercises' in r: r['exercises']=json.loads(r['exercises'])
        return r
    def session_record(sid):
        r=decode(one('SELECT * FROM sessions WHERE id=?',(sid,)))
        if not r: raise Problem('Workout not found.',404)
        profile(r['profile_id'])
        return r
    def mutation(fn):
        @wraps(fn)
        def run(*a,**kw):
            db().execute('BEGIN IMMEDIATE')
            result=fn(*a,**kw)
            db().commit()
            return jsonify(data=result)
        return run
    def idempotent(fn):
        @wraps(fn)
        def run(*a,**kw):
            x=body(); op=text(x,'operation_id',100); u=user()
            digest=hashlib.sha256((request.path+json.dumps(x,sort_keys=True,separators=(',',':'))).encode()).hexdigest()
            old=one('SELECT * FROM operation_receipts WHERE operation_id=?',(op,))
            if old:
                if old['user_id']!=u['id'] or old['request_hash']!=digest: raise Problem('This operation ID has already been used for a different request.',409)
                return json.loads(old['response_json'])
            result=fn(*a,**kw)
            insert('operation_receipts',dict(operation_id=op,user_id=u['id'],request_hash=digest,response_json=json.dumps(result),created_at=now()))
            return result
        return run

    @app.errorhandler(Problem)
    def problem(e): return jsonify(error=dict(code=str(e.status),message=e.message)),e.status
    @app.errorhandler(CSRFError)
    def csrf_error(e): return jsonify(error=dict(code='csrf',message='Your session has expired. Refresh the page and try again. Your offline records are still saved.')),400
    @app.errorhandler(sqlite3.IntegrityError)
    def integrity(e): return jsonify(error=dict(code='conflict',message='This record already exists or conflicts with a linked record.')),409
    @app.errorhandler(HTTPException)
    def http_error(e): return jsonify(error=dict(code=str(e.code),message=e.description)),e.code
    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.path.startswith('/api/'): response.headers['Cache-Control']='no-store'
        return response

    @app.get('/')
    def index(): return send_from_directory(app.static_folder,'index.html')
    @app.get('/sw.js')
    def sw(): return send_from_directory(app.static_folder,'sw.js',max_age=0)
    @app.get('/api/context')
    def context():
        u=one('SELECT id,name,email,role FROM users WHERE id=?',(session.get('user_id'),))
        return jsonify(data=dict(user=u,csrf_token=generate_csrf(),today=today()))
    @app.post('/api/register')
    @mutation
    def register():
        x=body(); name=text(x,'name'); email=text(x,'email').lower(); password=text(x,'password',256); role=x.get('role')
        if '@' not in email or len(password)<8 or role not in ('trainer','client'): raise Problem('Enter a valid email address, select a valid role, and use a password with at least 8 characters.')
        u=dict(id=uid(),name=name,email=email,role=role,password_hash=generate_password_hash(password),created_at=now())
        insert('users',u); session.clear(); session['user_id']=u['id']
        return {k:u[k] for k in ('id','name','email','role')}
    @app.post('/api/login')
    def login():
        x=body(); u=one('SELECT * FROM users WHERE email=?',(text(x,'email').lower(),))
        if not u or not check_password_hash(u['password_hash'],text(x,'password',256)): raise Problem('Incorrect email or password.',401)
        session.clear(); session['user_id']=u['id']
        return jsonify(data={k:u[k] for k in ('id','name','email','role')})
    @app.post('/api/logout')
    def logout(): session.clear(); return jsonify(data=dict(signed_out=True))
    @app.get('/api/clients')
    def clients():
        u=user()
        return jsonify(data=many('SELECT * FROM client_profiles WHERE trainer_id=? OR client_user_id=? ORDER BY created_at',(u['id'],u['id'])))
    @app.post('/api/clients')
    @mutation
    def add_client():
        u=trainer(); x=body()
        return insert('client_profiles',dict(id=uid(),trainer_id=u['id'],client_user_id=None,name=text(x,'name'),goals=str(x.get('goals',''))[:1000],created_at=now()))
    @app.patch('/api/clients/<pid>')
    @mutation
    def edit_client(pid):
        trainer(); profile(pid); x=body()
        db().execute('UPDATE client_profiles SET name=?,goals=? WHERE id=?',(text(x,'name'),str(x.get('goals',''))[:1000],pid))
        return profile(pid)
    @app.get('/api/invitations')
    def invitations():
        u=user()
        return jsonify(data=many('SELECT i.*,p.name AS profile_name,u.name AS trainer_name FROM invitations i JOIN client_profiles p ON p.id=i.profile_id JOIN users u ON u.id=i.trainer_id WHERE i.trainer_id=? OR i.client_user_id=? ORDER BY i.created_at DESC',(u['id'],u['id'])))
    @app.post('/api/invitations')
    @mutation
    def invite():
        u=trainer(); x=body(); p=profile(x.get('profile_id'))
        c=one("SELECT id FROM users WHERE email=? AND role='client'",(text(x,'client_email').lower(),))
        if not c: raise Problem('Ask the client to register a client account with this email address first.')
        if p['client_user_id'] or one('SELECT id FROM client_profiles WHERE client_user_id=?',(c['id'],)): raise Problem('This client is already linked to a trainer.',409)
        return insert('invitations',dict(id=uid(),profile_id=p['id'],trainer_id=u['id'],client_user_id=c['id'],status='pending',created_at=now()))
    @app.post('/api/invitations/<iid>/respond')
    @mutation
    def respond(iid):
        u=user(); x=body(); i=one('SELECT * FROM invitations WHERE id=?',(iid,))
        if not i or i['client_user_id']!=u['id']: raise Problem('You cannot respond to this invitation.',403)
        if i['status']!='pending': raise Problem('This invitation has already been answered.',409)
        decision=x.get('decision')
        if decision not in ('accept','decline'): raise Problem('Choose a valid response.')
        if decision=='accept':
            p=one('SELECT * FROM client_profiles WHERE id=?',(i['profile_id'],))
            if p['client_user_id'] or one('SELECT id FROM client_profiles WHERE client_user_id=?',(u['id'],)): raise Problem('An account is already linked to this profile, or your account is linked to another profile.',409)
            db().execute('UPDATE client_profiles SET client_user_id=? WHERE id=?',(u['id'],p['id']))
            db().execute("UPDATE invitations SET status='declined' WHERE client_user_id=? AND status='pending' AND id<>?",(u['id'],iid))
        status='accepted' if decision=='accept' else 'declined'
        db().execute('UPDATE invitations SET status=? WHERE id=?',(status,iid))
        return dict(id=iid,status=status)
    @app.get('/api/templates')
    def templates(): return jsonify(data=[decode(r) for r in many('SELECT * FROM templates WHERE trainer_id=? ORDER BY created_at DESC',(trainer()['id'],))])
    @app.post('/api/templates')
    @mutation
    def add_template():
        u=trainer(); x=body()
        r=insert('templates',dict(id=uid(),trainer_id=u['id'],name=text(x,'name'),exercises=json.dumps(exercises(x.get('exercises'))),created_at=now()))
        return decode(r)
    @app.put('/api/templates/<tid>')
    @mutation
    def edit_template(tid):
        u=trainer(); x=body()
        if not one('SELECT id FROM templates WHERE id=? AND trainer_id=?',(tid,u['id'])): raise Problem('You do not have access to this template.',403)
        db().execute('UPDATE templates SET name=?,exercises=? WHERE id=?',(text(x,'name'),json.dumps(exercises(x.get('exercises'))),tid))
        return decode(one('SELECT * FROM templates WHERE id=?',(tid,)))
    @app.get('/api/plans')
    def plans():
        u=user()
        return jsonify(data=[decode(r) for r in many('SELECT p.* FROM plans p JOIN client_profiles c ON c.id=p.profile_id WHERE c.trainer_id=? OR c.client_user_id=? ORDER BY p.created_at DESC',(u['id'],u['id']))])
    @app.post('/api/plans')
    @mutation
    def add_plan():
        u=trainer(); x=body(); p=profile(x.get('profile_id')); tid=x.get('source_template_id')
        if tid and not one('SELECT id FROM templates WHERE id=? AND trainer_id=?',(tid,u['id'])): raise Problem('You do not have access to this template.',403)
        return decode(insert('plans',dict(id=uid(),profile_id=p['id'],trainer_id=u['id'],source_template_id=tid,name=text(x,'name'),exercises=json.dumps(exercises(x.get('exercises'))),created_at=now())))
    @app.get('/api/sessions')
    def sessions():
        u=user()
        return jsonify(data=[decode(r) for r in many('SELECT s.* FROM sessions s JOIN client_profiles c ON c.id=s.profile_id WHERE c.trainer_id=? OR c.client_user_id=? ORDER BY s.workout_date DESC,s.created_at DESC',(u['id'],u['id']))])
    @app.post('/api/sessions/prepare')
    @mutation
    @idempotent
    def prepare():
        u=user(); x=body(); p=profile(x.get('profile_id')); device=text(x,'device_id',100); plan_id=x.get('plan_id'); rows=[]; name=text(x,'name')
        if plan_id:
            plan=decode(one('SELECT * FROM plans WHERE id=? AND profile_id=?',(plan_id,p['id'])))
            if not plan: raise Problem('Workout plan not found.',404)
            old=decode(one('SELECT * FROM sessions WHERE plan_id=?',(plan_id,)))
            if old:
                if old['recorder_user_id']!=u['id'] or old['recorder_device_id']!=device: raise Problem('This workout is already assigned to another recorder or device.',409)
                return old
            rows=[dict(e,sets=[]) for e in plan['exercises']]; name=plan['name']
        else: trainer()
        r=dict(id=uid(),profile_id=p['id'],plan_id=plan_id,recorder_user_id=u['id'],recorder_device_id=device,name=name,source='planned' if plan_id else 'blank',status='ready',workout_date=today(),version=0,exercises=json.dumps(rows),created_at=now(),updated_at=now())
        return decode(insert('sessions',r))
    @app.get('/api/sessions/<sid>')
    def get_session(sid):
        r=session_record(sid); r['can_record']=r['recorder_user_id']==user()['id'] and r['recorder_device_id']==request.args.get('device_id')
        return jsonify(data=r)
    @app.put('/api/sessions/<sid>')
    @mutation
    @idempotent
    def update_session(sid):
        u=user(); x=body(); r=session_record(sid)
        if r['recorder_user_id']!=u['id']: raise Problem('Only the original recorder can edit this workout.',403)
        if r['recorder_device_id']!=x.get('device_id'): raise Problem('This workout is linked to another device.',409)
        if x.get('base_version')!=r['version']: raise Problem('This record has been updated. Keep your local data and refresh the sync status.',409)
        status=x.get('status')
        if status not in ('in_progress','completed') or (r['status']=='completed' and status!='completed'): raise Problem('The workout status is invalid.')
        rows=exercises(x.get('exercises'),True,status=='completed')
        if u['role']=='client':
            old=r['exercises']
            if [(e['id'],e['name'],e['target_sets'],e['target_reps']) for e in rows] != [(e['id'],e['name'],e['target_sets'],e['target_reps']) for e in old]: raise Problem('Clients can only record results for the exercises in their plan.',403)
        version=r['version']+1
        db().execute('UPDATE sessions SET name=?,status=?,workout_date=?,exercises=?,version=?,updated_at=? WHERE id=?',(text(x,'name'),status,date(x.get('workout_date')),json.dumps(rows),version,now(),sid))
        return dict(session_id=sid,version=version,operation_id=x['operation_id'])
    @app.post('/api/sessions/past')
    @mutation
    @idempotent
    def past_session():
        u=trainer(); x=body(); p=profile(x.get('profile_id'))
        r=dict(id=uid(),profile_id=p['id'],plan_id=None,recorder_user_id=u['id'],recorder_device_id=text(x,'device_id',100),name=text(x,'name'),source='past',status='completed',workout_date=date(x.get('workout_date')),version=1,exercises=json.dumps(exercises(x.get('exercises'),True,True)),created_at=now(),updated_at=now())
        return decode(insert('sessions',r))
    @app.get('/api/clients/<pid>/history')
    def history(pid):
        profile(pid)
        return jsonify(data=[decode(r) for r in many("SELECT * FROM sessions WHERE profile_id=? AND status='completed' ORDER BY workout_date DESC,created_at DESC",(pid,))])
    @app.get('/api/clients/<pid>/body-weights')
    def weights(pid):
        profile(pid)
        return jsonify(data=many('SELECT * FROM body_weights WHERE profile_id=? ORDER BY measurement_date DESC',(pid,)))
    @app.post('/api/clients/<pid>/body-weights')
    @mutation
    @idempotent
    def add_weight(pid):
        u=trainer(); profile(pid); x=body()
        return insert('body_weights',dict(id=uid(),profile_id=pid,recorded_by=u['id'],measurement_date=date(x.get('measurement_date')),weight_lb=weight(x.get('weight_lb'),True),created_at=now(),updated_at=now()))
    @app.patch('/api/body-weights/<wid>')
    @mutation
    @idempotent
    def edit_weight(wid):
        trainer(); x=body(); r=one('SELECT * FROM body_weights WHERE id=?',(wid,))
        if not r: raise Problem('Record not found.',404)
        profile(r['profile_id'])
        db().execute('UPDATE body_weights SET measurement_date=?,weight_lb=?,updated_at=? WHERE id=?',(date(x.get('measurement_date',r['measurement_date'])),weight(x.get('weight_lb',r['weight_lb']),True),now(),wid))
        return one('SELECT * FROM body_weights WHERE id=?',(wid,))

    with app.app_context():
        db().executescript((ROOT/'schema.sql').read_text(encoding='utf-8'))
        db().commit()
    return app

if __name__=='__main__':
    create_app().run(host='127.0.0.1',port=int(os.environ.get('PORT','5055')),debug=False)
