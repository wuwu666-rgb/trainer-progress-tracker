"""Explicit, repeat-safe demo data creation. Never runs automatically in production."""
from app import create_app, uid, today
from datetime import date, timedelta
import sqlite3

def seed(app=None):
    app=app or create_app()
    with sqlite3.connect(app.config['DATABASE']) as db:
        if db.execute("SELECT 1 FROM users WHERE email='trainer@repbook.demo'").fetchone():
            print('Demo already exists; no data changed.')
            return
    browser=app.test_client()
    def call(path, payload):
        csrf=browser.get('/api/context').json['data']['csrf_token']
        r=browser.post('/api'+path,json=payload,headers={'X-CSRFToken':csrf})
        if r.status_code>=400: raise RuntimeError(r.json)
        return r.json['data']
    call('/register',dict(name='Alex Chen',email='client@repbook.demo',password='Demo2026!',role='client'))
    call('/logout',{})
    call('/register',dict(name='Jordan Lee',email='trainer@repbook.demo',password='Demo2026!',role='trainer'))
    profiles=[]
    for name,goals in [('Alex Chen','Build foundational strength · Train 3 times a week'),('Emma Wilson','Improve core stability · Build a consistent routine'),('Ryan Park','Develop full-body strength · Progress gradually')]:
        profiles.append(call('/clients',dict(name=name,goals=goals)))
    templates=[]
    for name,moves in [('Full body strength · Fundamentals',[('Squat',3,10),('Dumbbell bench press',3,12),('Bent-over row',3,10)]),('Upper body strength · Push & pull',[('Barbell bench press',4,8),('Seated row',3,12),('Dumbbell shoulder press',3,10)]),('Lower body training · Stability',[('Goblet squat',3,12),('Romanian deadlift',3,10),('Reverse lunge',3,10)])]:
        templates.append(call('/templates',dict(name=name,exercises=[dict(id=uid(),name=n,target_sets=s,target_reps=r) for n,s,r in moves])))
    for p,t in zip(profiles,templates):
        call('/plans',dict(profile_id=p['id'],source_template_id=t['id'],name=t['name'],exercises=t['exercises']))
    for index,p in enumerate(profiles):
        d=(date.fromisoformat(today())-timedelta(days=index+1)).isoformat()
        call('/sessions/past',dict(operation_id=uid(),device_id='demo-seed-device',profile_id=p['id'],name='Foundation strength · Completed',workout_date=d,exercises=[dict(id=uid(),name='Goblet squat',target_sets=3,target_reps=10,sets=[dict(actual_reps=10,weight_lb='35') for _ in range(3)])]))
        call('/clients/'+p['id']+'/body-weights',dict(operation_id=uid(),measurement_date=d,weight_lb=str(155+index*12)))
    invitation=call('/invitations',dict(profile_id=profiles[0]['id'],client_email='client@repbook.demo'))
    call('/logout',{})
    call('/login',dict(email='client@repbook.demo',password='Demo2026!'))
    call('/invitations/'+invitation['id']+'/respond',dict(decision='accept'))
    print('Demo ready. trainer@repbook.demo / client@repbook.demo | Password: Demo2026!')

if __name__=='__main__': seed()
