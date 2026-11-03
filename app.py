import sys, os, sqlite3, json, uuid, secrets
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation
sys.path.insert(0, str(Path(__file__).parent / 'vendor'))
from flask import Flask, request, session, jsonify, send_from_directory, abort
from werkzeug.security import generate_password_hash, check_password_hash
ROOT = Path(__file__).parent
app = Flask(__name__, static_folder='static')
keyfile = ROOT / '.secret'
if not keyfile.exists(): keyfile.write_text(secrets.token_hex(32))
app.secret_key = os.environ.get('SECRET_KEY') or keyfile.read_text()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.environ.get('HTTPS') == '1', MAX_CONTENT_LENGTH=1024*1024)
def db():
    c = sqlite3.connect(ROOT / 'tracker.sqlite3'); c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON'); return c
with db() as c:
    c.executescript('''CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,role TEXT);
    CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,kind TEXT,owner TEXT REFERENCES users(id),profile TEXT,data TEXT);
    CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY,user TEXT,payload TEXT,response TEXT);''')
def uid(): return str(uuid.uuid4())
def user():
    with db() as c: r=c.execute('SELECT id,name,email,role FROM users WHERE id=?',(session.get('uid'),)).fetchone()
    if not r: abort(401)
    return dict(r)
def get(c, id):
    r=c.execute('SELECT * FROM records WHERE id=?',(id,)).fetchone()
    if not r: abort(404)
    return dict(r)|{'data':json.loads(r['data'])}
def allowed(c,p,u):
    r=get(c,p)
    if r['kind']!='clients' or (r['owner']!=u['id'] and r['data'].get('client_user_id')!=u['id']): abort(403)
    return r
def save(c,r):
    c.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?,?)',(r['id'],r['kind'],r['owner'],r.get('profile'),json.dumps(r['data'])))
def validate_exercises(es, completed=False):
    if not isinstance(es,list) or not es: abort(400, 'Add at least one exercise.')
    results=0
    for e in es:
        if not str(e.get('name','')).strip(): abort(400,'Exercise name is required.')
        for k in ('target_sets','target_reps'):
            v=e.get(k,1)
            if type(v)!=int or v<1: abort(400,'Targets must be positive integers.')
        for s in e.get('sets',[]):
            if type(s.get('actual_reps'))!=int or s['actual_reps']<1: abort(400,'Reps must be positive integers.')
            weight(s.get('weight_lb'),False); results+=1
    if completed and not results: abort(400,'Record at least one set.')
def weight(v,positive=True):
    try: n=Decimal(str(v))
    except InvalidOperation: abort(400,'Invalid weight.')
    if not n.is_finite() or n<0 or (positive and n==0): abort(400,'Invalid weight.')
def datecheck(v):
    import time
    from zoneinfo import ZoneInfo
    try:
        d=datetime.strptime(v,'%Y-%m-%d').date()
        try: today=datetime.now(ZoneInfo('America/New_York')).date()
        except Exception: today=datetime.now().date()
        if d>today: abort(400,'Date cannot be in the future.')
    except (ValueError,TypeError): abort(400,'Invalid date.')
@app.before_request
def csrf():
    if request.path.startswith('/api/') and request.method not in ('GET','HEAD','OPTIONS'):
        if request.headers.get('X-CSRF-Token')!=session.get('csrf') or not session.get('csrf'): abort(400,'Refresh the page and try again.')
@app.errorhandler(Exception)
def error(e):
    code=getattr(e,'code',500)
    return jsonify(error={'code':code,'message':getattr(e,'description','An unexpected error occurred.')}),code
@app.get('/')
def index(): return app.send_static_file('index.html')
@app.get('/sw.js')
def sw(): return app.send_static_file('sw.js'),200,{'Service-Worker-Allowed':'/','Cache-Control':'no-cache'}
@app.get('/api/context')
def context():
    session.setdefault('csrf',secrets.token_hex(24))
    try: u=user()
    except Exception: u=None
    return jsonify(data={'user':u,'csrf_token':session['csrf']})
@app.post('/api/<action>')
def auth(action):
    if action not in ('register','login','logout'): abort(404)
    if action=='logout': session.clear(); return jsonify(data=True)
    d=request.get_json() or {}
    email=str(d.get('email','')).strip().lower(); password=d.get('password','')
    with db() as c:
        if action=='register':
            if '@' not in email or len(password)<8 or not d.get('name','').strip() or d.get('role') not in ('trainer','client'): abort(400,'Enter a name, valid email and password of at least 8 characters.')
            try: c.execute('INSERT INTO users VALUES(?,?,?,?,?)',(uid(),d['name'].strip(),email,generate_password_hash(password),d['role']))
            except sqlite3.IntegrityError: abort(409,'Email is already registered.')
        r=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        if not r or not check_password_hash(r['password'],password): abort(401,'Email or password is incorrect.')
        session['uid']=r['id']
    return jsonify(data=user())
@app.route('/api/records/<kind>',methods=['GET','POST'])
@app.route('/api/records/<kind>/<id>',methods=['PUT'])
def records(kind,id=None):
    if kind not in ('clients','invitations','templates','plans','sessions','weights'): abort(404)
    u=user()
    with db() as c:
        if request.method=='GET':
            out=[]
            for row in c.execute('SELECT * FROM records WHERE kind=? ORDER BY rowid DESC',(kind,)):
                r=dict(row); r['data']=json.loads(r['data'])
                permitted=r['owner']==u['id']
                if kind=='invitations': permitted=permitted or r['data']['client_user_id']==u['id']
                if r['profile']:
                    p=get(c,r['profile']); permitted=p['owner']==u['id'] or p['data'].get('client_user_id')==u['id']
                if kind=='clients': permitted=permitted or r['data'].get('client_user_id')==u['id']
                if permitted: out.append(r)
            return jsonify(data=out)
        d=request.get_json() or {}; op=d.pop('operation_id',None)
        payload=json.dumps([kind,id,d],sort_keys=True)
        if op:
            receipt=c.execute('SELECT * FROM receipts WHERE id=?',(op,)).fetchone()
            if receipt:
                if receipt['user']!=u['id'] or receipt['payload']!=payload: abort(409,'Operation conflict.')
                return jsonify(data=json.loads(receipt['response']))
        old=get(c,id) if id else None
        if old and old['kind']!=kind: abort(404)
        r=old or {'id':uid(),'kind':kind,'owner':u['id'],'profile':d.get('profile'),'data':{}}
        if kind=='invitations' and old:
            if old['data']['client_user_id']!=u['id'] or old['data']['status']!='pending': abort(403)
            if d.get('decision') not in ('accept','decline'): abort(400)
            if d['decision']=='accept':
                p=get(c,r['profile'])
                if p['data'].get('client_user_id'): abort(409,'Profile already connected.')
                for x in c.execute("SELECT data FROM records WHERE kind='clients'"):
                    if json.loads(x['data']).get('client_user_id')==u['id']: abort(409,'You already have a trainer.')
                p['data']['client_user_id']=u['id']; save(c,p)
            r['data']['status']='accepted' if d['decision']=='accept' else 'declined'
        else:
            if kind in ('clients','templates','plans','invitations','weights') and u['role']!='trainer': abort(403)
            if old and old['owner']!=u['id']: abort(403)
            if r['profile']: allowed(c,r['profile'],u)
            if kind in ('clients','templates','plans','sessions') and not d.get('name','').strip(): abort(400,'Name is required.')
            if kind in ('templates','plans'): validate_exercises(d.get('exercises'))
            if kind=='clients': d.pop('client_user_id',None)
            if kind=='invitations':
                p=allowed(c,r['profile'],u)
                target=c.execute("SELECT id FROM users WHERE email=? AND role='client'",(d.get('email','').lower().strip(),)).fetchone()
                if not target: abort(400,'Ask the client to register first.')
                if p['data'].get('client_user_id'): abort(409,'Client already connected.')
                d={'client_user_id':target['id'],'status':'pending','name':p['data']['name'],'trainer_name':u['name']}
            if kind in ('plans','weights','sessions') and not r['profile']: abort(400,'Choose a client.')
            if kind=='weights':
                weight(d.get('weight_lb')); datecheck(d.get('measurement_date'))
                for x in c.execute("SELECT id,data FROM records WHERE kind='weights' AND profile=?",(r['profile'],)):
                    if x['id']!=r['id'] and json.loads(x['data'])['measurement_date']==d['measurement_date']: abort(409,'A measurement already exists for this date.')
            if kind=='sessions':
                if old:
                    if d.get('base_version')!=old['data']['version'] or d.get('device_id')!=old['data']['device_id']: abort(409,'Version or recording device conflict.')
                elif d.get('plan_id'):
                    p=get(c,d['plan_id']); allowed(c,p['profile'],u)
                    if p['kind']!='plans' or p['profile']!=r['profile']: abort(403)
                    if any(json.loads(x['data']).get('plan_id')==d['plan_id'] for x in c.execute("SELECT data FROM records WHERE kind='sessions'")): abort(409,'This plan already has a session.')
                    d['exercises']=p['data']['exercises']
                elif u['role']!='trainer': abort(403)
                if d.get('status') not in ('in_progress','completed'): abort(400)
                if old and old['data']['status']=='completed' and not request.headers.get('X-Online-Correction'): abort(400,'Corrections require an online save.')
                validate_exercises(d.get('exercises'),d['status']=='completed'); datecheck(d.get('workout_date'))
                d['version']=(old['data']['version'] if old else 0)+1
            r['data'].update(d)
        save(c,r)
        if op: c.execute('INSERT INTO receipts VALUES(?,?,?,?)',(op,u['id'],payload,json.dumps(r)))
    return jsonify(data=r)
if __name__=='__main__': app.run(host='127.0.0.1',port=int(os.environ.get('PORT', '8080')),debug=False)

